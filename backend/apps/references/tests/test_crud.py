"""Tests for References CRUD and permission enforcement.

Mirrors the approach in `apps.users.tests.test_crud` — each resource gets a
minimal trio: list-without-perm → 403, superuser → 200, scoped-role → 200.
"""
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.references.models import Currency, Developer, SalesOffice
from apps.references.tests.factories import (
    CurrencyFactory,
    DeveloperFactory,
    SalesOfficeFactory,
)
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped_role(base: str, action: str = "view") -> dict[str, bool]:
    """Build a permissions dict that grants exactly `base.action` (with ancestors)."""
    perms = default_permissions(False)
    parts = f"{base}.{action}".split(".")
    for i in range(1, len(parts) + 1):
        perms[".".join(parts[:i])] = True
    return perms


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)


# --- Developer -----------------------------------------------------------


@pytest.mark.django_db
class TestDeveloperCRUD:
    url_list = reverse("developer-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_list(self, api_client):
        _superuser(api_client)
        DeveloperFactory.create_batch(3)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 3

    def test_scoped_role_can_view(self, api_client):
        role = RoleFactory(code="dev-viewer", permissions=_scoped_role("references.developers"))
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create(self, api_client):
        role = RoleFactory(code="dev-viewer", permissions=_scoped_role("references.developers"))
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        payload = {"name": {"ru": "A", "uz": "A", "oz": "А"}, "inn": "000000000"}
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_create(self, api_client):
        _superuser(api_client)
        payload = {
            "name": {"ru": "Ташкент-Строй", "uz": "Toshkent-Stroy", "oz": "Тошкент-Строй"},
            "director": "Иванов И.И.",
            "phone": "+998901112233",
            "inn": "301234567",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert Developer.objects.get(id=resp.data["id"]).director == "Иванов И.И."


# --- SalesOffice ----------------------------------------------------------


@pytest.mark.django_db
class TestSalesOfficeCRUD:
    url_list = reverse("sales-office-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_create_with_coords(self, api_client):
        _superuser(api_client)
        payload = {
            "name": {"ru": "Главный офис", "uz": "Bosh ofis", "oz": "Бош офис"},
            "address": "г. Ташкент, ул. Шота Руставели, 1",
            "latitude": "41.3111",
            "longitude": "69.2797",
            "phone": "+998712345678",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        obj = SalesOffice.objects.get(id=resp.data["id"])
        assert obj.latitude == Decimal("41.3111")
        assert obj.longitude == Decimal("69.2797")

    def test_coords_validated(self, api_client):
        _superuser(api_client)
        payload = {
            "name": {"ru": "X", "uz": "X", "oz": "Х"},
            "latitude": "200",  # > 90 -> invalid
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --- Currency -------------------------------------------------------------


@pytest.mark.django_db
class TestCurrencyCRUD:
    url_list = reverse("currency-list")

    def test_code_is_normalized_to_upper(self, api_client):
        _superuser(api_client)
        payload = {
            "code": "usd",
            "symbol": "$",
            "name": {"ru": "Доллар США", "uz": "AQSh dollari", "oz": "АҚШ доллари"},
            "rate": "12500.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["code"] == "USD"
        assert Currency.objects.filter(code="USD").exists()

    def test_invalid_code_rejected(self, api_client):
        _superuser(api_client)
        payload = {
            "code": "US",  # too short
            "name": {"ru": "X", "uz": "X", "oz": "Х"},
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_code_unique(self, api_client):
        _superuser(api_client)
        CurrencyFactory(code="USD")
        payload = {"code": "USD", "name": {"ru": "A", "uz": "A", "oz": "А"}}
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
