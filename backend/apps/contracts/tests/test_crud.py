"""Tests for Contracts CRUD (Phase 5.1).

Scope is deliberately narrow — data shape, FK wiring, denormalisation,
permission gating, and a couple of business constraints (unique per-project
number, `down_payment <= total_amount`, cross-project apartment rejection).

Workflow transitions (action state machine), schedule recomputation from
Calculation, and docgen all belong to 5.2/5.3 — not tested here.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status

from apps.clients.tests.factories import ClientContactFactory
from apps.contracts.models import (
    Contract,
    ContractTemplate,
    Payment,
    PaymentSchedule,
)
from apps.contracts.tests.factories import (
    ContractFactory,
    ContractTemplateFactory,
    PaymentFactory,
    PaymentScheduleFactory,
)
from apps.core.permission_tree import default_permissions
from apps.objects.tests.factories import ApartmentFactory, ProjectFactory
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped(*keys: str) -> dict[str, bool]:
    perms = default_permissions(False)
    for k in keys:
        parts = k.split(".")
        for i in range(1, len(parts) + 1):
            perms[".".join(parts[:i])] = True
    return perms


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)
    return admin


# --- Contract -------------------------------------------------------------


@pytest.mark.django_db
class TestContractCRUD:
    url_list = reverse("contract-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        assert api_client.get(self.url_list).status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_list(self, api_client):
        _superuser(api_client)
        ContractFactory.create_batch(3)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 3

    def test_scoped_role_can_view(self, api_client):
        role = RoleFactory(
            code="ct-v", permissions=_scoped("contracts.unsigned.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        assert api_client.get(self.url_list).status_code == status.HTTP_200_OK

    def test_create_minimal(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        # apartment must live under the same project
        apt = ApartmentFactory(
            floor__section__building__project=project,
        )
        signer = ClientContactFactory()
        payload = {
            "project": project.id,
            "apartment": apt.id,
            "signer": signer.id,
            "contract_number": "ЯМ-00001",
            "date": date.today().isoformat(),
            "total_amount": "750000000.00",
            "down_payment": "225000000.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        c = Contract.objects.get(id=resp.data["id"])
        assert c.action == "request"  # default
        assert c.is_signed is False
        assert c.signer_id == signer.id

    def test_denormalised_fields_on_retrieve(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        resp = api_client.get(reverse("contract-detail", args=[contract.id]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["signer_name"] == contract.signer.full_name
        assert resp.data["client_id"] == contract.signer.client_id
        assert resp.data["apartment_number"] == contract.apartment.number

    def test_unique_contract_number_per_project(self, api_client):
        project = ProjectFactory()
        ContractFactory(project=project, contract_number="A-1")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ContractFactory(project=project, contract_number="A-1")

    def test_same_number_allowed_across_projects(self):
        """Different project, same number — legal."""
        a = ProjectFactory()
        b = ProjectFactory()
        ContractFactory(project=a, contract_number="A-1")
        ContractFactory(project=b, contract_number="A-1")
        assert Contract.objects.filter(contract_number="A-1").count() == 2

    def test_empty_number_not_unique_constrained(self):
        """Drafts can share a blank contract_number."""
        project = ProjectFactory()
        ContractFactory(project=project, contract_number="")
        # Should not raise even though another has the same empty string.
        ContractFactory(project=project, contract_number="")

    def test_down_payment_exceeding_total_rejected(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        apt = ApartmentFactory(floor__section__building__project=project)
        signer = ClientContactFactory()
        payload = {
            "project": project.id,
            "apartment": apt.id,
            "signer": signer.id,
            "total_amount": "100.00",
            "down_payment": "200.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "down_payment" in resp.data

    def test_apartment_from_other_project_rejected(self, api_client):
        _superuser(api_client)
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        apt_in_b = ApartmentFactory(
            floor__section__building__project=project_b,
        )
        signer = ClientContactFactory()
        payload = {
            "project": project_a.id,
            "apartment": apt_in_b.id,
            "signer": signer.id,
            "total_amount": "1000.00",
            "down_payment": "0.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "apartment" in resp.data

    def test_action_is_read_only_in_51(self, api_client):
        """In 5.1 workflow transitions happen only via dedicated endpoints
        (which land in 5.2). Direct PATCH on `action` must be ignored."""
        _superuser(api_client)
        contract = ContractFactory()
        resp = api_client.patch(
            reverse("contract-detail", args=[contract.id]),
            {"action": "sign_in", "is_signed": True, "is_paid": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        contract.refresh_from_db()
        assert contract.action == "request"
        assert contract.is_signed is False
        assert contract.is_paid is False

    def test_filter_by_project(self, api_client):
        _superuser(api_client)
        a = ProjectFactory()
        b = ProjectFactory()
        ContractFactory.create_batch(
            2,
            project=a,
            apartment=factory_build_apt_in(a),
        )
        ContractFactory(
            project=b,
            apartment=factory_build_apt_in(b),
        )
        resp = api_client.get(f"{self.url_list}?project={a.id}")
        assert len(resp.data["results"]) == 2

    def test_search_by_signer_name(self, api_client):
        _superuser(api_client)
        signer = ClientContactFactory(full_name="Директор Искандерович")
        ContractFactory(signer=signer)
        ContractFactory()
        resp = api_client.get(f"{self.url_list}?search=Искандер")
        assert len(resp.data["results"]) == 1

    def test_payment_methods_m2m(self, api_client):
        from apps.references.models import PaymentMethod

        _superuser(api_client)
        pm_cash = PaymentMethod.objects.create(name={"ru": "Наличные", "uz": "Naqd", "oz": "Нақд"})
        pm_bank = PaymentMethod.objects.create(name={"ru": "Банк", "uz": "Bank", "oz": "Банк"})
        project = ProjectFactory()
        apt = ApartmentFactory(floor__section__building__project=project)
        signer = ClientContactFactory()
        payload = {
            "project": project.id,
            "apartment": apt.id,
            "signer": signer.id,
            "total_amount": "1000.00",
            "down_payment": "0.00",
            "payment_methods": [pm_cash.id, pm_bank.id],
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        c = Contract.objects.get(id=resp.data["id"])
        assert set(c.payment_methods.values_list("id", flat=True)) == {pm_cash.id, pm_bank.id}


def factory_build_apt_in(project):
    """Create an apartment belonging to the given project."""
    return ApartmentFactory(floor__section__building__project=project)


# --- ContractTemplate -----------------------------------------------------


@pytest.mark.django_db
class TestContractTemplateCRUD:
    url_list = reverse("contract-template-list")

    def test_scoped_permission(self, api_client):
        role = RoleFactory(
            code="tpl-v", permissions=_scoped("references.templates.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        ContractTemplateFactory.create_batch(2)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_list(self, api_client):
        _superuser(api_client)
        ContractTemplateFactory.create_batch(2)
        resp = api_client.get(self.url_list)
        assert len(resp.data["results"]) == 2

    def test_placeholders_roundtrip(self, api_client):
        _superuser(api_client)
        tpl = ContractTemplateFactory(
            placeholders=[
                {"key": "contract_number", "path": "contract.contract_number", "label": "№"},
                {"key": "client_name", "path": "client.full_name", "label": "ФИО"},
            ],
        )
        resp = api_client.get(reverse("contract-template-detail", args=[tpl.id]))
        assert len(resp.data["placeholders"]) == 2
        assert resp.data["placeholders"][0]["key"] == "contract_number"


# --- PaymentSchedule ------------------------------------------------------


@pytest.mark.django_db
class TestPaymentScheduleCRUD:
    url_list = reverse("payment-schedule-list")

    def test_create(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        payload = {
            "contract": contract.id,
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "amount": "50000000.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        ps = PaymentSchedule.objects.get(id=resp.data["id"])
        assert ps.status == "pending"
        assert ps.paid_amount == Decimal("0.00")

    def test_debt_property(self):
        ps = PaymentScheduleFactory(
            amount=Decimal("100.00"), paid_amount=Decimal("30.00"),
        )
        assert ps.debt == Decimal("70.00")

    def test_debt_clamped_at_zero(self):
        """Overpayments shouldn't make debt go negative."""
        ps = PaymentScheduleFactory(
            amount=Decimal("100.00"), paid_amount=Decimal("150.00"),
        )
        assert ps.debt == Decimal("0.00")

    def test_debt_exposed_in_serializer(self, api_client):
        _superuser(api_client)
        ps = PaymentScheduleFactory(
            amount=Decimal("100.00"), paid_amount=Decimal("40.00"),
        )
        resp = api_client.get(reverse("payment-schedule-detail", args=[ps.id]))
        assert resp.data["debt"] == "60.00"

    def test_filter_by_contract(self, api_client):
        _superuser(api_client)
        c1 = ContractFactory()
        c2 = ContractFactory()
        PaymentScheduleFactory.create_batch(3, contract=c1)
        PaymentScheduleFactory(contract=c2)
        resp = api_client.get(f"{self.url_list}?contract={c1.id}")
        assert len(resp.data["results"]) == 3

    def test_cascade_delete_on_contract(self):
        """Deleting a Contract should cascade to its schedule rows."""
        contract = ContractFactory()
        PaymentScheduleFactory.create_batch(3, contract=contract)
        assert PaymentSchedule.objects.filter(contract=contract).count() == 3
        contract.delete()
        assert PaymentSchedule.objects.filter(contract_id=contract.id).count() == 0


# --- Payment --------------------------------------------------------------


@pytest.mark.django_db
class TestPaymentCRUD:
    url_list = reverse("payment-list")

    def test_create(self, api_client):
        _superuser(api_client)
        ps = PaymentScheduleFactory()
        payload = {
            "schedule": ps.id,
            "amount": "10000000.00",
            "payment_type": "bank",
            "paid_at": date.today().isoformat(),
            "receipt_number": "ПКО-42",
            "comment": "первый взнос, перечислено",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        p = Payment.objects.get(id=resp.data["id"])
        assert p.payment_type == "bank"

    def test_contract_id_denormalised(self, api_client):
        _superuser(api_client)
        p = PaymentFactory()
        resp = api_client.get(reverse("payment-detail", args=[p.id]))
        assert resp.data["contract_id"] == p.schedule.contract_id

    def test_cascade_delete_on_schedule(self):
        ps = PaymentScheduleFactory()
        PaymentFactory.create_batch(2, schedule=ps)
        assert Payment.objects.filter(schedule=ps).count() == 2
        ps.delete()
        assert Payment.objects.filter(schedule_id=ps.id).count() == 0


# --- Protected delete -----------------------------------------------------


@pytest.mark.django_db
class TestProtectedDelete:
    def test_deleting_apartment_under_contract_blocked(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        apt = contract.apartment
        resp = api_client.delete(reverse("apartment-detail", args=[apt.id]))
        # The Apartment FK is PROTECT → ProtectedDestroyMixin → 409.
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert "contracts.Contract" in resp.data["blocked_by"]

    def test_deleting_signer_under_contract_blocked(self):
        contract = ContractFactory()
        with pytest.raises(Exception) as exc_info:
            with transaction.atomic():
                contract.signer.delete()
        # Django's ProtectedError is a subclass of IntegrityError in spirit;
        # either surfaces here — we accept both.
        from django.db.models import ProtectedError

        assert isinstance(exc_info.value, (ProtectedError, IntegrityError))
