"""Tests for `apps.objects.services.booking`.

Focus:
  * book_apartment: `free → booked` happy path, `free → booked_vip`, sets
    `booking_expires_at`, rejects non-free source statuses.
  * release_booking: `booked → free`, clears expiry, rejects non-booking
    source statuses.
  * Both write ApartmentStatusLog rows.
  * HTTP actions: permission gating (`book` vs `book_vip` vs
    `change_status`), 409 on illegal transitions, 200 on success.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import ApartmentStatusLog
from apps.objects.services.apartments import change_status
from apps.objects.services.booking import (
    ApartmentNotBookable,
    ApartmentNotReleasable,
    book_apartment,
    release_booking,
)
from apps.objects.tests.factories import ApartmentFactory
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped(*keys: str) -> dict[str, bool]:
    perms = default_permissions(False)
    for k in keys:
        parts = k.split(".")
        for i in range(1, len(parts) + 1):
            perms[".".join(parts[:i])] = True
    return perms


# --- Service-level --------------------------------------------------------


@pytest.mark.django_db
class TestBookApartmentService:
    def test_happy_path(self):
        apt = ApartmentFactory()
        actor = StaffFactory(password="x12345678")
        result = book_apartment(apt, 7, by=actor, comment="client call")

        apt.refresh_from_db()
        assert apt.status == "booked"
        assert apt.booking_expires_at is not None
        # Expiry ~ now + 7 days (allow 5-sec slack)
        delta = apt.booking_expires_at - timezone.now()
        assert 6 * 86400 < delta.total_seconds() < 8 * 86400

        log = ApartmentStatusLog.objects.get(id=result.log_id)
        assert log.old_status == "free"
        assert log.new_status == "booked"
        assert log.changed_by == actor

    def test_vip_sets_booked_vip(self):
        apt = ApartmentFactory()
        book_apartment(apt, 3, vip=True)
        apt.refresh_from_db()
        assert apt.status == "booked_vip"
        assert apt.booking_expires_at is not None

    def test_cannot_book_non_free(self):
        apt = ApartmentFactory()
        book_apartment(apt, 7)
        apt.refresh_from_db()
        with pytest.raises(ApartmentNotBookable):
            book_apartment(apt, 7)

    def test_positive_duration_required(self):
        apt = ApartmentFactory()
        with pytest.raises(ValueError):
            book_apartment(apt, 0)
        with pytest.raises(ValueError):
            book_apartment(apt, -5)


@pytest.mark.django_db
class TestReleaseBookingService:
    def test_happy_path(self):
        apt = ApartmentFactory()
        book_apartment(apt, 7)
        apt.refresh_from_db()
        assert apt.status == "booked"
        assert apt.booking_expires_at is not None

        result = release_booking(apt, comment="client declined")
        apt.refresh_from_db()
        assert apt.status == "free"
        assert apt.booking_expires_at is None

        log = ApartmentStatusLog.objects.get(id=result.log_id)
        assert log.new_status == "free"

    def test_cannot_release_non_booked(self):
        apt = ApartmentFactory()
        # status = free by default
        with pytest.raises(ApartmentNotReleasable):
            release_booking(apt)

    def test_cannot_release_formalized(self):
        """Releasing a formalized apartment should go through change_status,
        not release_booking — enforce that here."""
        apt = ApartmentFactory()
        book_apartment(apt, 3)
        change_status(
            __import__("apps.objects.models", fromlist=["Apartment"]).Apartment.objects.get(pk=apt.pk),
            "formalized",
        )
        apt.refresh_from_db()
        with pytest.raises(ApartmentNotReleasable):
            release_booking(apt)


# --- HTTP actions --------------------------------------------------------


@pytest.mark.django_db
class TestBookAction:
    @staticmethod
    def _url(apt_id):
        return reverse("apartment-book", args=[apt_id])

    def test_requires_book_permission(self, api_client):
        role = RoleFactory(
            code="viewer",
            permissions=_scoped("objects.apartments.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        apt = ApartmentFactory()
        resp = api_client.post(self._url(apt.id), {"duration_days": 7}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_scoped_role_can_book(self, api_client):
        role = RoleFactory(
            code="booker",
            permissions=_scoped(
                "objects.apartments.view",
                "objects.apartments.book",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        apt = ApartmentFactory()
        resp = api_client.post(
            self._url(apt.id),
            {"duration_days": 7, "comment": "client #42"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["apartment"]["status"] == "booked"
        assert resp.data["booking_expires_at"] is not None

    def test_vip_requires_book_vip(self, api_client):
        """book + vip=True → needs book_vip permission on top of book."""
        role = RoleFactory(
            code="booker-no-vip",
            permissions=_scoped(
                "objects.apartments.view",
                "objects.apartments.book",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        apt = ApartmentFactory()
        resp = api_client.post(
            self._url(apt.id),
            {"duration_days": 3, "vip": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_vip_success_with_both_perms(self, api_client):
        role = RoleFactory(
            code="vip-booker",
            permissions=_scoped(
                "objects.apartments.view",
                "objects.apartments.book",
                "objects.apartments.book_vip",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        apt = ApartmentFactory()
        resp = api_client.post(
            self._url(apt.id),
            {"duration_days": 3, "vip": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["apartment"]["status"] == "booked_vip"

    def test_bad_duration_rejected(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        apt = ApartmentFactory()
        resp = api_client.post(
            self._url(apt.id),
            {"duration_days": 0},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_free_returns_409(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        apt = ApartmentFactory()
        book_apartment(apt, 7)  # Now booked
        resp = api_client.post(
            self._url(apt.id),
            {"duration_days": 7},
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["code"] == "not_bookable"


@pytest.mark.django_db
class TestReleaseAction:
    @staticmethod
    def _url(apt_id):
        return reverse("apartment-release", args=[apt_id])

    def test_requires_change_status_permission(self, api_client):
        role = RoleFactory(
            code="viewer",
            permissions=_scoped("objects.apartments.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        apt = ApartmentFactory()
        resp = api_client.post(self._url(apt.id), {}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_scoped_role_can_release(self, api_client):
        role = RoleFactory(
            code="mover",
            permissions=_scoped(
                "objects.apartments.view",
                "objects.apartments.change_status",
            ),
        )
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        apt = ApartmentFactory()
        book_apartment(apt, 7)

        resp = api_client.post(self._url(apt.id), {"comment": "cancel"}, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["apartment"]["status"] == "free"
        assert resp.data["apartment"]["booking_expires_at"] is None

    def test_free_apt_returns_409(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        apt = ApartmentFactory()
        resp = api_client.post(self._url(apt.id), {}, format="json")
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["code"] == "not_releasable"
