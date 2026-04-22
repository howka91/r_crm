"""Tests for ?force=true cascade delete on SectionViewSet and FloorViewSet.

Default destroy is protected (409 via ProtectedDestroyMixin). With
`?force=true` the viewset explicitly walks children bottom-up so
ApartmentStatusLogs, Calculations, PriceHistory all cascade cleanly via
their on_delete=CASCADE FKs.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.objects.models import (
    Apartment,
    ApartmentStatusLog,
    Calculation,
    Floor,
    PriceHistory,
    Section,
)
from apps.objects.services.apartments import change_status
from apps.objects.services.pricing import change_floor_price
from apps.objects.tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    FloorFactory,
    PaymentInPercentFactory,
    SectionFactory,
)
from apps.users.tests.factories import StaffFactory


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)
    return admin


# --- SectionViewSet.destroy?force=true -----------------------------------


@pytest.mark.django_db
class TestSectionForceDelete:
    def test_without_force_returns_409_when_has_floors(self, api_client):
        _superuser(api_client)
        section = SectionFactory()
        FloorFactory(section=section)
        resp = api_client.delete(reverse("section-detail", args=[section.id]))
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert Section.objects.filter(id=section.id).exists()

    def test_with_force_cascades_everything(self, api_client):
        _superuser(api_client)
        building = BuildingFactory()
        section = SectionFactory(building=building)
        f1 = FloorFactory(section=section)
        f2 = FloorFactory(section=section)
        a1 = ApartmentFactory(floor=f1, area=Decimal("50.00"))
        a2 = ApartmentFactory(floor=f1, area=Decimal("60.00"))
        a3 = ApartmentFactory(floor=f2, area=Decimal("45.00"))
        # Create derived rows that should cascade-delete via CASCADE FKs.
        change_status(a1, "booked")
        change_status(a2, "booked")
        PaymentInPercentFactory(percent=Decimal("100.00"))
        change_floor_price(f1, Decimal("12000000.00"))  # creates Calculation + PriceHistory

        assert Apartment.objects.filter(floor__section=section).count() == 3
        assert ApartmentStatusLog.objects.filter(apartment__floor__section=section).count() >= 2
        assert Calculation.objects.filter(apartment__floor__section=section).count() >= 1
        assert PriceHistory.objects.filter(floor__section=section).count() >= 1

        resp = api_client.delete(
            reverse("section-detail", args=[section.id]) + "?force=true",
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        # Section, floors, apartments, logs, calcs, price-history all gone.
        assert not Section.objects.filter(id=section.id).exists()
        assert not Floor.objects.filter(section_id=section.id).exists()
        assert not Apartment.objects.filter(floor__section_id=section.id).exists()
        assert ApartmentStatusLog.objects.filter(apartment_id__in=[a1.id, a2.id, a3.id]).count() == 0
        assert PriceHistory.objects.filter(floor__section_id=section.id).count() == 0
        # Building itself is untouched.
        assert building.id == section.building_id
        from apps.objects.models import Building
        assert Building.objects.filter(id=building.id).exists()

    def test_force_on_empty_section_still_works(self, api_client):
        _superuser(api_client)
        section = SectionFactory()
        resp = api_client.delete(
            reverse("section-detail", args=[section.id]) + "?force=true",
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Section.objects.filter(id=section.id).exists()


# --- FloorViewSet.destroy?force=true -------------------------------------


@pytest.mark.django_db
class TestFloorForceDelete:
    def test_without_force_returns_409_when_has_apartments(self, api_client):
        _superuser(api_client)
        floor = FloorFactory()
        ApartmentFactory(floor=floor)
        resp = api_client.delete(reverse("floor-detail", args=[floor.id]))
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert Floor.objects.filter(id=floor.id).exists()

    def test_with_force_cascades_apartments(self, api_client):
        _superuser(api_client)
        floor = FloorFactory()
        apts = ApartmentFactory.create_batch(3, floor=floor)
        for a in apts[:2]:
            change_status(a, "booked")

        resp = api_client.delete(
            reverse("floor-detail", args=[floor.id]) + "?force=true",
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Floor.objects.filter(id=floor.id).exists()
        assert not Apartment.objects.filter(floor_id=floor.id).exists()
        assert ApartmentStatusLog.objects.filter(apartment_id__in=[a.id for a in apts]).count() == 0

    def test_force_keeps_sibling_floors_intact(self, api_client):
        """Force-deleting one floor must NOT touch other floors in the section."""
        _superuser(api_client)
        section = SectionFactory()
        f_delete = FloorFactory(section=section, number=1)
        f_keep = FloorFactory(section=section, number=2)
        ApartmentFactory(floor=f_delete)
        ApartmentFactory(floor=f_keep)

        resp = api_client.delete(
            reverse("floor-detail", args=[f_delete.id]) + "?force=true",
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert Floor.objects.filter(id=f_keep.id).exists()
        assert Apartment.objects.filter(floor_id=f_keep.id).count() == 1
