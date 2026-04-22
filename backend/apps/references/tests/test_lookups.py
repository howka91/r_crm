"""Tests for the 13 LookupModel-based references.

All 13 share `references.lookups.*` permissions and a generic serializer
(`make_lookup_serializer`) + viewset (`make_lookup_viewset`). These tests:

  - parametrize over the list of models: each gets the standard permission gate
    + superuser CRUD smoke.
  - also pin down the 3 models that have extra fields (Badge.color,
    Location.region, PaymentInPercent.percent).
"""
from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.references.models import (
    LOOKUP_MODELS,
    Badge,
    Location,
    PaymentInPercent,
    Region,
)
from apps.users.tests.factories import RoleFactory, StaffFactory


def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _list_url(model_cls: type) -> str:
    return reverse(f"{_kebab(model_cls.__name__)}-list")


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)


@pytest.mark.django_db
@pytest.mark.parametrize("model_cls", LOOKUP_MODELS, ids=lambda m: m.__name__)
class TestLookupPermissions:
    def test_list_requires_permission(self, api_client, model_cls):
        role = RoleFactory(code=f"no-perms-{model_cls.__name__.lower()}")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(_list_url(model_cls))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_list(self, api_client, model_cls):
        _superuser(api_client)
        resp = api_client.get(_list_url(model_cls))
        assert resp.status_code == status.HTTP_200_OK

    def test_scoped_lookups_role_can_view(self, api_client, model_cls):
        perms = default_permissions(False)
        for key in ("references", "references.lookups", "references.lookups.view"):
            perms[key] = True
        role = RoleFactory(code=f"lu-view-{model_cls.__name__.lower()}", permissions=perms)
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(_list_url(model_cls))
        assert resp.status_code == status.HTTP_200_OK


# --- Extra-field sanity checks ---------------------------------------------


@pytest.mark.django_db
class TestLookupExtras:
    def test_badge_accepts_hex_color(self, api_client):
        _superuser(api_client)
        payload = {
            "name": {"ru": "Новинка", "uz": "Yangi", "oz": "Янги"},
            "color": "#22C55E",
        }
        resp = api_client.post(_list_url(Badge), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert Badge.objects.get(id=resp.data["id"]).color == "#22C55E"

    def test_badge_rejects_invalid_color(self, api_client):
        _superuser(api_client)
        payload = {
            "name": {"ru": "X", "uz": "X", "oz": "Х"},
            "color": "green",  # not hex
        }
        resp = api_client.post(_list_url(Badge), payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_payment_in_percent_stores_decimal(self, api_client):
        _superuser(api_client)
        payload = {
            "name": {"ru": "30%", "uz": "30%", "oz": "30%"},
            "percent": "30.00",
        }
        resp = api_client.post(_list_url(PaymentInPercent), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert PaymentInPercent.objects.get(id=resp.data["id"]).percent == Decimal("30.00")

    def test_location_links_to_region(self, api_client):
        _superuser(api_client)
        region = Region.objects.create(name={"ru": "Ташкентская область", "uz": "Toshkent viloyati", "oz": "Тошкент вилояти"})
        payload = {
            "name": {"ru": "Янгиюль", "uz": "Yangiyo'l", "oz": "Янгийўл"},
            "region": region.pk,
        }
        resp = api_client.post(_list_url(Location), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        obj = Location.objects.get(id=resp.data["id"])
        assert obj.region_id == region.pk

    def test_lookup_create_ordering_by_sort(self, api_client):
        _superuser(api_client)
        Region.objects.create(name={"ru": "Первый", "uz": "Birinchi", "oz": "Биринчи"}, sort=10)
        Region.objects.create(name={"ru": "Нулевой", "uz": "Nol", "oz": "Нол"}, sort=5)
        resp = api_client.get(_list_url(Region))
        assert resp.status_code == status.HTTP_200_OK
        # Smaller sort comes first.
        names_ru = [r["name"]["ru"] for r in resp.data["results"]]
        assert names_ru.index("Нулевой") < names_ru.index("Первый")
