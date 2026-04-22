"""Tests for pricing models: PaymentPlan, DiscountRule, Calculation,
PriceHistory.

The models carry no cascade/recalc logic themselves — that belongs to
`services.pricing` (phase 3.4). So these tests focus on:

  * CRUD + permission gating on each ViewSet.
  * Model-level constraints (area_end >= area_start on DiscountRule,
    unique(apartment, payment_percent) on Calculation).
  * PriceHistory is read-only via HTTP — writes happen only via the (3.4)
    service using the model manager directly.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import (
    Calculation,
    DiscountRule,
    PaymentPlan,
    PriceHistory,
)
from apps.objects.tests.factories import (
    ApartmentFactory,
    CalculationFactory,
    DiscountRuleFactory,
    FloorFactory,
    PaymentInPercentFactory,
    PaymentPlanFactory,
    ProjectFactory,
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


# --- PaymentPlan ----------------------------------------------------------


@pytest.mark.django_db
class TestPaymentPlanCRUD:
    url_list = reverse("payment-plan-list")

    def test_requires_permission(self, api_client):
        role = RoleFactory(code="none")
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        assert api_client.get(self.url_list).status_code == status.HTTP_403_FORBIDDEN

    def test_create(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        payload = {
            "project": project.id,
            "name": {"ru": "30/70", "uz": "30/70", "oz": "30/70"},
            "down_payment_percent": "30.00",
            "installment_months": 24,
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        pp = PaymentPlan.objects.get(id=resp.data["id"])
        assert pp.installment_months == 24

    def test_filter_by_project(self, api_client):
        _superuser(api_client)
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        PaymentPlanFactory.create_batch(2, project=p1)
        PaymentPlanFactory(project=p2)
        resp = api_client.get(f"{self.url_list}?project={p1.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_scoped_role_can_create(self, api_client):
        role = RoleFactory(
            code="pp-editor",
            permissions=_scoped(
                "objects.payment_plans.view",
                "objects.payment_plans.create",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        project = ProjectFactory()
        payload = {
            "project": project.id,
            "name": {"ru": "X", "uz": "X", "oz": "X"},
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data


# --- DiscountRule ---------------------------------------------------------


@pytest.mark.django_db
class TestDiscountRuleCRUD:
    url_list = reverse("discount-rule-list")

    def test_create(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        pp = PaymentInPercentFactory()
        payload = {
            "project": project.id,
            "area_start": "50.00",
            "area_end": "100.00",
            "payment_percent": pp.id,
            "discount_percent": "7.50",
            "is_duplex": False,
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_area_end_below_start_rejected_at_serializer(self, api_client):
        """Serializer validation — clients get 400, not a DB-level 500."""
        _superuser(api_client)
        project = ProjectFactory()
        pp = PaymentInPercentFactory()
        payload = {
            "project": project.id,
            "area_start": "100.00",
            "area_end": "50.00",
            "payment_percent": pp.id,
            "discount_percent": "5.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "area_end" in resp.data

    def test_area_end_below_start_rejected_at_db(self):
        """Model CheckConstraint — last line of defence if serializer is bypassed."""
        project = ProjectFactory()
        pp = PaymentInPercentFactory()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DiscountRule.objects.create(
                    project=project,
                    area_start=Decimal("100.00"),
                    area_end=Decimal("50.00"),
                    payment_percent=pp,
                    discount_percent=Decimal("5.00"),
                )

    def test_filter_by_project_and_duplex(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        DiscountRuleFactory(project=project, is_duplex=True)
        DiscountRuleFactory(project=project, is_duplex=False)
        DiscountRuleFactory(project=project, is_duplex=False)
        resp = api_client.get(
            f"{self.url_list}?project={project.id}&is_duplex=false",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2


# --- Calculation ----------------------------------------------------------


@pytest.mark.django_db
class TestCalculationCRUD:
    url_list = reverse("calculation-list")

    def test_create(self, api_client):
        _superuser(api_client)
        apt = ApartmentFactory()
        pp = PaymentInPercentFactory()
        payload = {
            "apartment": apt.id,
            "payment_percent": pp.id,
            "discount_percent": "5.00",
            "installment_months": 12,
            "new_price_per_sqm": "14250000.00",
            "new_total_price": "712500000.00",
            "initial_fee": "213750000.00",
            "monthly_payment": "41562500.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_unique_apt_payment_percent(self):
        apt = ApartmentFactory()
        pp = PaymentInPercentFactory()
        CalculationFactory(apartment=apt, payment_percent=pp)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CalculationFactory(apartment=apt, payment_percent=pp)

    def test_filter_by_apartment(self, api_client):
        _superuser(api_client)
        apt = ApartmentFactory()
        other = ApartmentFactory()
        pp1 = PaymentInPercentFactory()
        pp2 = PaymentInPercentFactory()
        CalculationFactory(apartment=apt, payment_percent=pp1)
        CalculationFactory(apartment=apt, payment_percent=pp2)
        CalculationFactory(apartment=other, payment_percent=pp1)
        resp = api_client.get(f"{self.url_list}?apartment={apt.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2


# --- PriceHistory (read-only) --------------------------------------------


@pytest.mark.django_db
class TestPriceHistoryReadOnly:
    url_list = reverse("price-history-list")

    def test_is_read_only(self, api_client):
        _superuser(api_client)
        floor = FloorFactory()
        payload = {
            "floor": floor.id,
            "old_price": "10000000.00",
            "new_price": "12000000.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_filter_by_floor(self, api_client):
        _superuser(api_client)
        f1 = FloorFactory()
        f2 = FloorFactory()
        PriceHistory.objects.create(
            floor=f1, old_price=Decimal("1"), new_price=Decimal("2"),
        )
        PriceHistory.objects.create(
            floor=f1, old_price=Decimal("2"), new_price=Decimal("3"),
        )
        PriceHistory.objects.create(
            floor=f2, old_price=Decimal("1"), new_price=Decimal("4"),
        )
        resp = api_client.get(f"{self.url_list}?floor={f1.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_gated_by_floor_view_permission(self, api_client):
        role = RoleFactory(
            code="floor-view",
            permissions=_scoped("objects.floors.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
