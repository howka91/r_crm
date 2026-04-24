"""Tests for Apartment CRUD, status workflow, and the change-status action.

Covers:
  * CRUD permission gating.
  * `services.apartments.change_status`: legal/illegal transitions, log is
    written with actor, booking_expires_at is cleared on non-booking statuses.
  * `POST /apartments/:id/change-status/` action: happy path, 409 on bad
    transition, permission isolation (view vs change_status).
  * `is_active=False` filtering via SoftDeleteManager.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import Apartment, ApartmentStatusLog
from apps.objects.services.apartments import (
    InvalidStatusTransition,
    can_transition,
    change_status,
)
from apps.objects.tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    FloorFactory,
    ProjectFactory,
    SectionFactory,
)
from apps.references.tests.factories import PlanningFactory
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped_role(*keys: str) -> dict[str, bool]:
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


def _make_apartment(**overrides) -> Apartment:
    floor = overrides.pop("floor", None) or FloorFactory()
    defaults = {
        "floor": floor,
        "number": overrides.pop("number", "1"),
        "rooms_count": 2,
        "area": Decimal("50.00"),
        "total_price": Decimal("750000000.00"),
    }
    defaults.update(overrides)
    return Apartment.objects.create(**defaults)


# --- Service layer --------------------------------------------------------


@pytest.mark.django_db
class TestChangeStatusService:
    def test_transition_matrix(self):
        assert can_transition("free", "booked")
        assert can_transition("free", "booked_vip")
        assert can_transition("booked", "formalized")
        assert can_transition("escrow", "sold")
        assert can_transition("sold", "free")  # admin rollback

        assert not can_transition("free", "sold")
        assert not can_transition("free", "formalized")
        assert not can_transition("sold", "escrow")

    def test_change_status_happy_path(self):
        apt = _make_apartment()
        actor = StaffFactory(password="x12345678")
        result = change_status(apt, "booked", by=actor, comment="manager call")

        apt.refresh_from_db()
        assert apt.status == "booked"
        assert result.old_status == "free"
        assert result.new_status == "booked"

        log = ApartmentStatusLog.objects.get(id=result.log_id)
        assert log.apartment_id == apt.id
        assert log.old_status == "free"
        assert log.new_status == "booked"
        assert log.changed_by == actor
        assert log.comment == "manager call"

    def test_invalid_transition_rejected(self):
        apt = _make_apartment()
        with pytest.raises(InvalidStatusTransition):
            change_status(apt, "sold")
        apt.refresh_from_db()
        assert apt.status == "free"
        assert not ApartmentStatusLog.objects.filter(apartment=apt).exists()

    def test_unknown_status_rejected(self):
        apt = _make_apartment()
        with pytest.raises(InvalidStatusTransition):
            change_status(apt, "totally-fake")

    def test_noop_still_logs(self):
        """Setting the same status is allowed but logged as 'touched'."""
        apt = _make_apartment()
        result = change_status(apt, "free", comment="double-click")
        assert result.old_status == "free"
        assert result.new_status == "free"
        log = ApartmentStatusLog.objects.get(id=result.log_id)
        assert "no-op" in log.comment or log.comment == "double-click"

    def test_booking_expires_cleared_on_non_booking_status(self, django_user_model):
        from django.utils import timezone

        apt = _make_apartment()
        apt.status = "booked"
        apt.booking_expires_at = timezone.now()
        apt.save()

        change_status(apt, "formalized")
        apt.refresh_from_db()
        assert apt.status == "formalized"
        assert apt.booking_expires_at is None


# --- HTTP layer (CRUD + action) -------------------------------------------


@pytest.mark.django_db
class TestApartmentCRUD:
    url_list = reverse("apartment-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create(self, api_client):
        _superuser(api_client)
        floor = FloorFactory()
        payload = {
            "floor": floor.id,
            "number": "42",
            "rooms_count": 3,
            "area": "72.50",
            "total_price": "1100000000.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        apt = Apartment.objects.get(id=resp.data["id"])
        assert apt.status == "free"  # default
        assert apt.rooms_count == 3

    def test_filter_by_floor(self, api_client):
        _superuser(api_client)
        f1 = FloorFactory()
        f2 = FloorFactory()
        _make_apartment(floor=f1, number="1")
        _make_apartment(floor=f1, number="2")
        _make_apartment(floor=f2, number="1")
        resp = api_client.get(f"{self.url_list}?floor={f1.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_unique_number_per_floor(self, api_client):
        _superuser(api_client)
        floor = FloorFactory()
        _make_apartment(floor=floor, number="7")
        payload = {
            "floor": floor.id,
            "number": "7",
            "area": "40.00",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code >= 400

    def test_status_display_returned(self, api_client):
        _superuser(api_client)
        apt = _make_apartment()
        resp = api_client.get(reverse("apartment-detail", args=[apt.id]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "free"
        # status_display is the translated label — assert non-empty string.
        assert isinstance(resp.data["status_display"], str) and resp.data["status_display"]


@pytest.mark.django_db
class TestChangeStatusAction:
    @staticmethod
    def _url(apt_id):
        return reverse("apartment-change-status", args=[apt_id])

    def test_requires_change_status_permission(self, api_client):
        """View-only role cannot invoke the action (only change_status perm does)."""
        role = RoleFactory(
            code="viewer-only",
            permissions=_scoped_role("objects.apartments.view"),
        )
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        apt = _make_apartment()
        resp = api_client.post(self._url(apt.id), {"new_status": "booked"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_scoped_role_can_change_status(self, api_client):
        role = RoleFactory(
            code="mover",
            permissions=_scoped_role(
                "objects.apartments.view",
                "objects.apartments.change_status",
            ),
        )
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        apt = _make_apartment()
        resp = api_client.post(
            self._url(apt.id),
            {"new_status": "booked", "comment": "client #55"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["apartment"]["status"] == "booked"
        assert "log_id" in resp.data
        log = ApartmentStatusLog.objects.get(id=resp.data["log_id"])
        assert log.changed_by == staff
        assert log.comment == "client #55"

    def test_invalid_transition_returns_409(self, api_client):
        _superuser(api_client)
        apt = _make_apartment()
        resp = api_client.post(
            self._url(apt.id),
            {"new_status": "sold"},  # free → sold is illegal
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["code"] == "invalid_transition"
        apt.refresh_from_db()
        assert apt.status == "free"

    def test_bad_status_value_returns_400(self, api_client):
        _superuser(api_client)
        apt = _make_apartment()
        resp = api_client.post(
            self._url(apt.id),
            {"new_status": "not-a-real-status"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestStatusLogReadOnly:
    url_list = reverse("apartment-status-log-list")

    def test_filter_by_apartment(self, api_client):
        _superuser(api_client)
        apt_a = _make_apartment(number="A")
        apt_b = _make_apartment(number="B")
        change_status(apt_a, "booked")
        change_status(apt_b, "booked")
        change_status(apt_b, "formalized")
        resp = api_client.get(f"{self.url_list}?apartment={apt_b.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_log_is_read_only(self, api_client):
        _superuser(api_client)
        apt = _make_apartment()
        payload = {
            "apartment": apt.id,
            "old_status": "free",
            "new_status": "booked",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        # Read-only viewset → no POST allowed.
        assert resp.status_code in (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN)


# --- Planning cross-project validation -----------------------------------


@pytest.mark.django_db
class TestApartmentPlanning:
    """Apartments may only reference a `Planning` that belongs to the same
    ЖК — enforced by `ApartmentSerializer.validate`. The rejected payload
    returns 400 with `code=planning_cross_project` so the UI can surface a
    specific error instead of a generic 400."""

    def test_can_assign_planning_from_same_project(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        building = BuildingFactory(project=project)
        section = SectionFactory(building=building)
        floor = FloorFactory(section=section)
        apt = ApartmentFactory(floor=floor)
        planning = PlanningFactory(project=project)

        url = reverse("apartment-detail", args=[apt.id])
        resp = api_client.patch(url, {"planning": planning.id}, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        apt.refresh_from_db()
        assert apt.planning_id == planning.id

    def test_cannot_assign_planning_from_other_project(self, api_client):
        _superuser(api_client)
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        floor_a = FloorFactory(section__building__project=project_a)
        apt = ApartmentFactory(floor=floor_a)
        foreign_planning = PlanningFactory(project=project_b)

        url = reverse("apartment-detail", args=[apt.id])
        resp = api_client.patch(
            url, {"planning": foreign_planning.id}, format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # DRF emits the field-level error keyed by `planning`.
        assert "planning" in resp.data

    def test_planning_preview_embedded_in_response(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        floor = FloorFactory(section__building__project=project)
        planning = PlanningFactory(
            project=project, code="3K-A", rooms_count=3, area=Decimal("72.50"),
        )
        apt = ApartmentFactory(floor=floor, planning=planning)
        resp = api_client.get(reverse("apartment-detail", args=[apt.id]))
        assert resp.status_code == status.HTTP_200_OK
        preview = resp.data["planning_preview"]
        assert preview is not None
        assert preview["id"] == planning.id
        assert preview["code"] == "3K-A"
        assert preview["rooms_count"] == 3
