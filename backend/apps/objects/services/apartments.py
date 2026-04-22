"""Apartment status workflow.

Single source of truth for *which* transitions are legal and *how* they are
recorded. Every state change goes through `change_status` — never mutate
`Apartment.status` directly. ViewSets call this service in the
`change-status` custom action; background jobs (booking expiry in phase 8)
will call it too.

Reasoning:
  * Legal transitions are data (a dict), not nested `if/else`.
  * Transaction wraps both the status update and the log insert — no
    half-logged transitions.
  * Booking expiry metadata (`booking_expires_at`) is cleared by this
    service on transitions OUT OF booked states; the booking service in
    phase 3.4 will set it on transitions INTO booked states.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from apps.objects.models import Apartment
    from apps.users.models import Staff


# All legal transitions, keyed by source status. Value is the set of statuses
# the source can move to. "free" accepts `booked`, `booked_vip` as the normal
# start; rollbacks "* → free" are included so mis-bookings can be undone.
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "free": frozenset({"booked", "booked_vip"}),
    "booked": frozenset({"free", "formalized"}),
    "booked_vip": frozenset({"free", "formalized"}),
    "formalized": frozenset({"free", "escrow"}),
    "escrow": frozenset({"formalized", "sold"}),
    "sold": frozenset({"free"}),  # rare admin rollback path
}

# Statuses that imply "no booking in effect" — `booking_expires_at` is
# cleared on transition to any of these.
_NON_BOOKING_STATUSES: frozenset[str] = frozenset({
    "free", "formalized", "escrow", "sold",
})


class InvalidStatusTransition(ValueError):
    """Raised when a status transition is not in `_ALLOWED_TRANSITIONS`."""


@dataclass(frozen=True)
class TransitionResult:
    apartment_id: int
    old_status: str
    new_status: str
    log_id: int


def can_transition(old: str, new: str) -> bool:
    """Pure predicate — useful in serializers/templates/tests."""
    return new in _ALLOWED_TRANSITIONS.get(old, frozenset())


def change_status(
    apartment: "Apartment",
    new_status: str,
    *,
    by: "Staff | None" = None,
    comment: str = "",
) -> TransitionResult:
    """Transition an Apartment and write an ApartmentStatusLog row.

    Raises `InvalidStatusTransition` if the transition is not allowed.

    The Apartment instance is re-fetched inside the transaction using
    `select_for_update` to avoid the read-before-write race when two users
    try to change status concurrently. Pass a fresh instance — attributes
    may have drifted from the row that the caller holds.
    """
    # Local import: this module is loaded at startup and the models package
    # imports references, which would otherwise form a reverse dep.
    from apps.objects.models import Apartment, ApartmentStatusLog

    if new_status not in Apartment.Status.values:
        raise InvalidStatusTransition(
            _("Неизвестный статус: %(s)s") % {"s": new_status},
        )

    with transaction.atomic():
        apt = Apartment.objects.select_for_update().get(pk=apartment.pk)

        if apt.status == new_status:
            # No-op — but still log as an explicit "touched" action so the
            # audit trail reflects the intent.
            log = ApartmentStatusLog.objects.create(
                apartment=apt,
                old_status=apt.status,
                new_status=new_status,
                changed_by=by,
                comment=comment or "no-op",
            )
            return TransitionResult(apt.pk, apt.status, new_status, log.pk)

        if not can_transition(apt.status, new_status):
            raise InvalidStatusTransition(
                _("Недопустимый переход: %(old)s → %(new)s") %
                {"old": apt.status, "new": new_status},
            )

        old = apt.status
        apt.status = new_status
        if new_status in _NON_BOOKING_STATUSES:
            apt.booking_expires_at = None
        apt.save(update_fields=["status", "booking_expires_at", "modified_at"])

        log = ApartmentStatusLog.objects.create(
            apartment=apt,
            old_status=old,
            new_status=new_status,
            changed_by=by,
            comment=comment,
        )

    return TransitionResult(apt.pk, old, new_status, log.pk)
