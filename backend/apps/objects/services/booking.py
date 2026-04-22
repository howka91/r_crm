"""Booking workflow — explicit reservation of an apartment with an expiry.

Distinct from `services.apartments.change_status` because booking has two
extra concerns that don't fit the generic status-transition service:

  1. `booking_expires_at` — a concrete timestamp that must be set atomically
     with the status change (and cleared on release), otherwise a crash
     between the two writes leaves zombie reservations.
  2. Concurrency — two sales managers clicking "Book" on the same apartment
     must not both succeed. `select_for_update()` on Apartment inside a
     transaction is how we serialize the conflict.

Both `book_apartment` and `release_booking` write an `ApartmentStatusLog`
row inline rather than delegating to the status service — otherwise we'd
have nested transactions and the logging path would diverge by accident.

Expiry is enforced elsewhere: a Celery beat job (`release_expired_bookings`,
phase 8) scans `Apartment.booking_expires_at < now` and calls
`release_booking` on each.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from apps.objects.models import Apartment
    from apps.users.models import Staff


class ApartmentNotBookable(ValueError):
    """Raised when booking is attempted on an apartment that isn't `free`."""


class ApartmentNotReleasable(ValueError):
    """Raised when release is attempted on an apartment that isn't booked."""


@dataclass(frozen=True)
class BookingResult:
    apartment_id: int
    status: str
    booking_expires_at: str | None
    log_id: int


def book_apartment(
    apartment: "Apartment",
    duration_days: int,
    *,
    by: "Staff | None" = None,
    comment: str = "",
    vip: bool = False,
) -> BookingResult:
    """Reserve an apartment until now + duration_days.

    Moves status `free → booked` (or `booked_vip` if `vip=True`). Raises
    `ApartmentNotBookable` if status is anything else. Uses
    `select_for_update` so concurrent booking attempts serialize and the
    second one correctly sees the first's state before trying again.
    """
    from apps.objects.models import Apartment, ApartmentStatusLog

    if duration_days <= 0:
        raise ValueError(_("Срок брони должен быть положительным"))

    target_status = "booked_vip" if vip else "booked"
    expires = timezone.now() + timedelta(days=duration_days)

    with transaction.atomic():
        apt = Apartment.objects.select_for_update().get(pk=apartment.pk)
        if apt.status != "free":
            raise ApartmentNotBookable(
                _("Квартира не может быть забронирована из статуса '%(s)s'")
                % {"s": apt.status},
            )

        old_status = apt.status
        apt.status = target_status
        apt.booking_expires_at = expires
        apt.save(
            update_fields=["status", "booking_expires_at", "modified_at"],
        )

        log = ApartmentStatusLog.objects.create(
            apartment=apt,
            old_status=old_status,
            new_status=target_status,
            changed_by=by,
            comment=comment or f"Бронь на {duration_days} дн. (до {expires:%Y-%m-%d %H:%M})",
        )

    return BookingResult(
        apartment_id=apt.pk,
        status=target_status,
        booking_expires_at=expires.isoformat(),
        log_id=log.pk,
    )


def release_booking(
    apartment: "Apartment",
    *,
    by: "Staff | None" = None,
    comment: str = "",
) -> BookingResult:
    """Undo a booking — status `booked / booked_vip → free`, clear expiry.

    Raises `ApartmentNotReleasable` if the apartment is already free or has
    progressed past the booking stage (e.g. `formalized`). Use
    `services.apartments.change_status` directly for those rollback paths.
    """
    from apps.objects.models import Apartment, ApartmentStatusLog

    with transaction.atomic():
        apt = Apartment.objects.select_for_update().get(pk=apartment.pk)
        if apt.status not in ("booked", "booked_vip"):
            raise ApartmentNotReleasable(
                _("Освободить можно только забронированную квартиру; статус: '%(s)s'")
                % {"s": apt.status},
            )

        old_status = apt.status
        apt.status = "free"
        apt.booking_expires_at = None
        apt.save(
            update_fields=["status", "booking_expires_at", "modified_at"],
        )

        log = ApartmentStatusLog.objects.create(
            apartment=apt,
            old_status=old_status,
            new_status="free",
            changed_by=by,
            comment=comment or "Бронь снята",
        )

    return BookingResult(
        apartment_id=apt.pk,
        status="free",
        booking_expires_at=None,
        log_id=log.pk,
    )
