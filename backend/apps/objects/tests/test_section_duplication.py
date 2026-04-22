"""Tests for section duplication — service + HTTP action."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import Apartment, Floor, Section
from apps.objects.services.section_duplication import duplicate_section
from apps.objects.tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    FloorFactory,
    SectionFactory,
)
from apps.references.tests.factories import DeveloperFactory
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped(*keys: str) -> dict[str, bool]:
    perms = default_permissions(False)
    for k in keys:
        parts = k.split(".")
        for i in range(1, len(parts) + 1):
            perms[".".join(parts[:i])] = True
    return perms


# --- Service -------------------------------------------------------------


@pytest.mark.django_db
class TestDuplicateSectionService:
    def test_clones_full_subtree(self):
        src_section = SectionFactory(number=1)
        f1 = FloorFactory(section=src_section, number=1, price_per_sqm=Decimal("10000000.00"))
        f2 = FloorFactory(section=src_section, number=2, price_per_sqm=Decimal("10500000.00"))
        ApartmentFactory(floor=f1, number="1", area=Decimal("45.00"))
        ApartmentFactory(floor=f1, number="2", area=Decimal("62.00"))
        ApartmentFactory(floor=f2, number="1", area=Decimal("45.00"))

        # Different project/building: simulate "copy across projects".
        target_building = BuildingFactory()
        result = duplicate_section(src_section, target_building)

        assert result.floors_created == 2
        assert result.apartments_created == 3

        new_section = Section.objects.get(pk=result.new_section_id)
        assert new_section.building == target_building
        assert new_section.title == src_section.title
        # Number preserved when free.
        assert new_section.number == 1
        # Floor numbers preserved; total floors match.
        assert Floor.objects.filter(section=new_section).count() == 2
        numbers = set(Floor.objects.filter(section=new_section).values_list("number", flat=True))
        assert numbers == {1, 2}

    def test_section_number_collision_bumps(self):
        """If target_building already has a section with the same number,
        the clone picks max+1 instead of raising an IntegrityError."""
        target_building = BuildingFactory()
        SectionFactory(building=target_building, number=1)
        SectionFactory(building=target_building, number=3)

        src_section = SectionFactory(number=1)  # collides
        result = duplicate_section(src_section, target_building)

        new_section = Section.objects.get(pk=result.new_section_id)
        assert new_section.number == 4  # max(1, 3) + 1

    def test_booking_state_reset_on_clone(self):
        """Cloned apartments always land as `free` with no expiry, even if
        the source was booked / sold."""
        from django.utils import timezone

        src_section = SectionFactory()
        src_floor = FloorFactory(section=src_section)
        ApartmentFactory(
            floor=src_floor,
            number="1",
            status="booked",
            booking_expires_at=timezone.now(),
        )
        ApartmentFactory(floor=src_floor, number="2", status="sold")

        target_building = BuildingFactory()
        result = duplicate_section(src_section, target_building)

        new_section = Section.objects.get(pk=result.new_section_id)
        cloned = Apartment.objects.filter(floor__section=new_section)
        assert cloned.count() == 2
        for apt in cloned:
            assert apt.status == "free"
            assert apt.booking_expires_at is None

    def test_original_untouched(self):
        """Cloning must not mutate the source in any way."""
        src_section = SectionFactory()
        src_floor = FloorFactory(section=src_section)
        original_apt = ApartmentFactory(floor=src_floor, area=Decimal("50.00"))

        target_building = BuildingFactory()
        duplicate_section(src_section, target_building)

        original_apt.refresh_from_db()
        src_section.refresh_from_db()
        assert src_section.building != target_building
        assert original_apt.area == Decimal("50.00")
        # Source floor count unchanged.
        assert src_section.floors.count() == 1


# --- HTTP action ---------------------------------------------------------


@pytest.mark.django_db
class TestDuplicateSectionAction:
    @staticmethod
    def _url(section_id):
        return reverse("section-duplicate", args=[section_id])

    def test_requires_create_permission(self, api_client):
        """View-only role is rejected — duplication creates new rows."""
        role = RoleFactory(
            code="viewer",
            permissions=_scoped("objects.sections.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        src = SectionFactory()
        target = BuildingFactory()
        resp = api_client.post(
            self._url(src.id),
            {"target_building_id": target.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_scoped_role_can_duplicate(self, api_client):
        role = RoleFactory(
            code="cloner",
            permissions=_scoped(
                "objects.sections.view",
                "objects.sections.create",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))

        src = SectionFactory()
        FloorFactory(section=src, number=1)
        FloorFactory(section=src, number=2)
        target = BuildingFactory()

        resp = api_client.post(
            self._url(src.id),
            {"target_building_id": target.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["floors_created"] == 2
        assert resp.data["apartments_created"] == 0
        new_id = resp.data["section"]["id"]
        assert Section.objects.get(pk=new_id).building == target

    def test_missing_target_returns_404(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        src = SectionFactory()
        resp = api_client.post(
            self._url(src.id),
            {"target_building_id": 9999999},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "target_building_id" in resp.data

    def test_target_must_be_positive(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        src = SectionFactory()
        resp = api_client.post(
            self._url(src.id),
            {"target_building_id": 0},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_clone_across_developers(self, api_client):
        """The copy must work cross-project / cross-developer; nothing in
        the service references the current project's developer."""
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)

        dev_a = DeveloperFactory()
        dev_b = DeveloperFactory()
        from apps.objects.tests.factories import ProjectFactory
        p_a = ProjectFactory(developer=dev_a)
        p_b = ProjectFactory(developer=dev_b)
        b_a = BuildingFactory(project=p_a)
        b_b = BuildingFactory(project=p_b)
        src = SectionFactory(building=b_a, number=1)
        src_floor = FloorFactory(section=src, number=3)
        ApartmentFactory(floor=src_floor, number="1", area=Decimal("40.00"))

        resp = api_client.post(
            self._url(src.id),
            {"target_building_id": b_b.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        new_section = Section.objects.get(pk=resp.data["section"]["id"])
        assert new_section.building == b_b
        assert new_section.building.project == p_b
        assert Apartment.objects.filter(floor__section=new_section).count() == 1
