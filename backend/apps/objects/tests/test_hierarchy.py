"""Tests for Objects hierarchy CRUD + permission enforcement.

Mirrors `apps.references.tests.test_crud` shape. Focus:

- Permission gating on each of the 4 ViewSets (superuser / scoped role / no-perm).
- Hierarchy integrity: unique constraints, PROTECT-on-delete.
- `*_count` read-only fields on parent serializers reflect DB state.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import Building, Floor, Project, Section
from apps.objects.tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    FloorFactory,
    ProjectFactory,
    SectionFactory,
)
from apps.references.tests.factories import DeveloperFactory
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped_role(base: str, action: str = "view") -> dict[str, bool]:
    perms = default_permissions(False)
    parts = f"{base}.{action}".split(".")
    for i in range(1, len(parts) + 1):
        perms[".".join(parts[:i])] = True
    return perms


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)


# --- Project --------------------------------------------------------------


@pytest.mark.django_db
class TestProjectCRUD:
    url_list = reverse("project-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_list(self, api_client):
        _superuser(api_client)
        ProjectFactory.create_batch(3)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 3

    def test_scoped_role_can_view(self, api_client):
        role = RoleFactory(code="proj-viewer", permissions=_scoped_role("objects.projects"))
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create(self, api_client):
        role = RoleFactory(code="proj-viewer", permissions=_scoped_role("objects.projects"))
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        dev = DeveloperFactory()
        payload = {
            "developer": dev.id,
            "title": {"ru": "ЖК", "uz": "JK", "oz": "ЖК"},
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_create(self, api_client):
        _superuser(api_client)
        dev = DeveloperFactory()
        payload = {
            "developer": dev.id,
            "title": {"ru": "Янги Маҳалла", "uz": "Yangi Mahalla", "oz": "Янги Маҳалла"},
            "address": "г. Ташкент, Яшнабадский район",
            "description": {"ru": "", "uz": "", "oz": ""},
            "banks": [{"name": "Uzbek Bank", "account": "2020..."}],
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        obj = Project.objects.get(id=resp.data["id"])
        assert obj.developer == dev
        assert obj.contract_number_index == 0  # default

    def test_buildings_count_reflects_children(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        BuildingFactory.create_batch(4, project=project)
        resp = api_client.get(reverse("project-detail", args=[project.id]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["buildings_count"] == 4


# --- Building -------------------------------------------------------------


@pytest.mark.django_db
class TestBuildingCRUD:
    url_list = reverse("building-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        payload = {
            "project": project.id,
            "title": {"ru": "Блок А", "uz": "Blok A", "oz": "Блок А"},
            "number": "A",
            "cadastral_number": "10:01:01:001",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert Building.objects.get(id=resp.data["id"]).number == "A"

    def test_filter_by_project(self, api_client):
        _superuser(api_client)
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        BuildingFactory.create_batch(2, project=p1)
        BuildingFactory.create_batch(3, project=p2)
        resp = api_client.get(f"{self.url_list}?project={p1.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_delete_protected_when_has_children(self, api_client):
        """Deleting a Project that has Buildings returns 409 (ProtectedError)."""
        _superuser(api_client)
        project = ProjectFactory()
        BuildingFactory(project=project)
        resp = api_client.delete(reverse("project-detail", args=[project.id]))
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert Project.objects.filter(id=project.id).exists()
        assert resp.data["blocked_by"] == {"objects.Building": 1}


# --- Section --------------------------------------------------------------


@pytest.mark.django_db
class TestSectionCRUD:
    url_list = reverse("section-list")

    def test_create(self, api_client):
        _superuser(api_client)
        building = BuildingFactory()
        payload = {
            "building": building.id,
            "title": {"ru": "Подъезд 1", "uz": "Podyezd 1", "oz": "Подъезд 1"},
            "number": 1,
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_unique_number_per_building(self, api_client):
        """`objects_section_unique_number_per_building` — DB-level constraint."""
        building = BuildingFactory()
        SectionFactory(building=building, number=1)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                SectionFactory(building=building, number=1)

    def test_same_number_different_building_ok(self, api_client):
        b1 = BuildingFactory()
        b2 = BuildingFactory()
        SectionFactory(building=b1, number=1)
        SectionFactory(building=b2, number=1)
        assert Section.objects.filter(number=1).count() == 2


# --- Floor ----------------------------------------------------------------


@pytest.mark.django_db
class TestFloorCRUD:
    url_list = reverse("floor-list")

    def test_create_with_price(self, api_client):
        _superuser(api_client)
        section = SectionFactory()
        payload = {
            "section": section.id,
            "number": 5,
            "price_per_sqm": "18000000.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert Floor.objects.get(id=resp.data["id"]).price_per_sqm == Decimal("18000000.00")

    def test_negative_price_rejected(self, api_client):
        _superuser(api_client)
        section = SectionFactory()
        payload = {
            "section": section.id,
            "number": 5,
            "price_per_sqm": "-1.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unique_number_per_section(self, api_client):
        section = SectionFactory()
        FloorFactory(section=section, number=3)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                FloorFactory(section=section, number=3)

    def test_negative_floor_number_allowed(self, api_client):
        """Floors with negative numbers (parking levels) are valid."""
        _superuser(api_client)
        section = SectionFactory()
        payload = {
            "section": section.id,
            "number": -1,
            "price_per_sqm": "0.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data


# --- Inventory aggregated endpoint ---------------------------------------


@pytest.mark.django_db
class TestProjectInventory:
    """`GET /projects/:id/inventory/` — single-shot tree for the contract
    wizard's apartment picker and the inventory grid. Replaces the 4-call
    fan-out that previously pulled all buildings/sections/floors/apartments
    in the DB and filtered in-memory on the frontend.
    """

    def test_unauthenticated_rejected(self, api_client):
        project = ProjectFactory()
        url = reverse("project-inventory", args=[project.id])
        resp = api_client.get(url)
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_requires_apartments_view_permission(self, api_client):
        """Gate is `objects.apartments.view` — someone who can see projects
        but not apartments shouldn't be able to enumerate the whole tree."""
        project = ProjectFactory()
        role = RoleFactory(
            code="proj-only",
            permissions=_scoped_role("objects.projects"),  # no apartments.view
        )
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        url = reverse("project-inventory", args=[project.id])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_only_this_projects_subtree(self, api_client):
        _superuser(api_client)
        target = ProjectFactory()
        other = ProjectFactory()
        # Target tree: 2 buildings × 1 section × 1 floor × 2 apartments = 4 apts
        for b_num in range(2):
            b = BuildingFactory(project=target, number=f"T{b_num}")
            s = SectionFactory(building=b, number=b_num + 1)
            f = FloorFactory(section=s, number=1)
            ApartmentFactory.create_batch(2, floor=f)
        # Noise — another project's subtree must not appear.
        other_b = BuildingFactory(project=other, number="OTHER")
        other_s = SectionFactory(building=other_b, number=9)
        other_f = FloorFactory(section=other_s, number=1)
        ApartmentFactory.create_batch(3, floor=other_f)

        url = reverse("project-inventory", args=[target.id])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert set(data.keys()) == {"buildings", "sections", "floors", "apartments"}
        assert len(data["buildings"]) == 2
        assert len(data["sections"]) == 2
        assert len(data["floors"]) == 2
        assert len(data["apartments"]) == 4
        assert all(b["project"] == target.id for b in data["buildings"])

    def test_empty_project_returns_empty_collections(self, api_client):
        """A project with no buildings still returns a 200 with four
        empty arrays — the client uses `.length` checks, not try/catch."""
        _superuser(api_client)
        project = ProjectFactory()
        url = reverse("project-inventory", args=[project.id])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == {
            "buildings": [],
            "sections": [],
            "floors": [],
            "apartments": [],
        }

    def test_apartments_carry_nested_status_and_chars(self, api_client):
        """Payload uses the same ApartmentSerializer as /apartments/, so the
        frontend does not need a reshape when swapping from the 4-call
        fan-out to this endpoint."""
        _superuser(api_client)
        project = ProjectFactory()
        b = BuildingFactory(project=project, number="A")
        s = SectionFactory(building=b, number=1)
        f = FloorFactory(section=s, number=3)
        apt = ApartmentFactory(floor=f, number="12")
        url = reverse("project-inventory", args=[project.id])
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        (payload,) = resp.data["apartments"]
        assert payload["id"] == apt.id
        assert payload["floor"] == f.id
        # status_display must be rendered — wizard uses it verbatim.
        assert "status_display" in payload
