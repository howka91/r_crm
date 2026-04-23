"""End-to-end tests for the workflow custom actions on ContractViewSet.

Each endpoint is exercised through the DRF test client so the permission
wiring, URL routing and response shape are all validated together with the
underlying service.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.contracts.models import Contract, PaymentSchedule
from apps.contracts.tests.factories import ContractFactory
from apps.core.permission_tree import default_permissions
from apps.objects.tests.factories import (
    CalculationFactory,
    PaymentInPercentFactory,
)
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


def _attach_calc(contract, **overrides):
    defaults = dict(
        apartment=contract.apartment,
        payment_percent=PaymentInPercentFactory(),
        installment_months=6,
        monthly_payment=Decimal("50000000.00"),
        initial_fee=Decimal("150000000.00"),
    )
    defaults.update(overrides)
    calc = CalculationFactory(**defaults)
    contract.calculation = calc
    contract.save(update_fields=["calculation"])
    return calc


# --- send-to-wait --------------------------------------------------------


@pytest.mark.django_db
class TestSendToWaitEndpoint:
    def test_mints_number_and_flips_action(self, api_client):
        _superuser(api_client)
        contract = ContractFactory(contract_number="")
        contract.project.contract_number_prefix = "ЯМ"
        contract.project.save(update_fields=["contract_number_prefix"])

        resp = api_client.post(
            reverse("contract-send-to-wait", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["action"] == "wait"
        assert resp.data["contract_number"] == "ЯМ-00001"
        assert resp.data["__minted_contract_number"] == "ЯМ-00001"

    def test_scoped_permission_allows(self, api_client):
        role = RoleFactory(
            code="contract-sender",
            permissions=_scoped(
                "contracts.unsigned.view",
                "contracts.unsigned.send_to_wait",
            ),
        )
        api_client.force_authenticate(
            StaffFactory(role=role, password="x12345678"),
        )
        contract = ContractFactory()
        resp = api_client.post(
            reverse("contract-send-to-wait", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data

    def test_illegal_transition_returns_409(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        contract.action = Contract.Action.APPROVE
        contract.save(update_fields=["action"])
        resp = api_client.post(
            reverse("contract-send-to-wait", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["current_action"] == "approve"


# --- approve -------------------------------------------------------------


@pytest.mark.django_db
class TestApproveEndpoint:
    def test_wait_to_approve(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        contract.action = Contract.Action.WAIT
        contract.save(update_fields=["action"])
        resp = api_client.post(reverse("contract-approve", args=[contract.id]))
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["action"] == "approve"


# --- sign ----------------------------------------------------------------


@pytest.mark.django_db
class TestSignEndpoint:
    def test_approve_to_sign(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        contract.action = Contract.Action.APPROVE
        contract.save(update_fields=["action"])
        resp = api_client.post(reverse("contract-sign", args=[contract.id]))
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["action"] == "sign_in"
        assert resp.data["is_signed"] is True


# --- request-edit --------------------------------------------------------


@pytest.mark.django_db
class TestRequestEditEndpoint:
    def test_wait_to_edit_with_reason(self, api_client):
        _superuser(api_client)
        contract = ContractFactory(document={"a": 1})
        contract.action = Contract.Action.WAIT
        contract.save(update_fields=["action"])
        resp = api_client.post(
            reverse("contract-request-edit", args=[contract.id]),
            {"reason": "Fix signer PIN"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["action"] == "edit"
        contract.refresh_from_db()
        assert len(contract.old) == 1
        assert contract.old[0]["reason"] == "Fix signer PIN"


# --- generate-schedule ---------------------------------------------------


@pytest.mark.django_db
class TestGenerateScheduleEndpoint:
    def test_happy_path(self, api_client):
        _superuser(api_client)
        contract = ContractFactory(date=date(2026, 5, 1))
        _attach_calc(contract, installment_months=3)

        resp = api_client.post(
            reverse("contract-generate-schedule", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["count"] == 4  # 1 initial + 3 monthly
        assert PaymentSchedule.objects.filter(contract=contract).count() == 4

    def test_blocked_on_signed_contract(self, api_client):
        _superuser(api_client)
        contract = ContractFactory(is_signed=True)
        _attach_calc(contract)
        resp = api_client.post(
            reverse("contract-generate-schedule", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_rejects_contract_without_calculation(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        contract.calculation = None
        contract.save(update_fields=["calculation"])
        resp = api_client.post(
            reverse("contract-generate-schedule", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
