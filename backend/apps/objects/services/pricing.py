"""Pricing cascade — explicit functions, called from ViewSets and jobs.

This is a deliberate departure from the legacy codebase, where a signal on
`Stage.save` re-ran the entire pricing graph and sometimes recursed on itself.
Here the caller decides when to recompute: change a Floor price, call
`change_floor_price(...)`; the function writes a PriceHistory row, updates
the Floor, and walks every child Apartment invoking `recalc_apartment`.

`recalc_apartment`:
  1. Updates `Apartment.total_price` as `area * floor.price_per_sqm + surcharge`
     (the no-discount baseline).
  2. For every active `references.PaymentInPercent`, upserts a `Calculation`
     row with the discount-adjusted numbers. If a Calculation already exists
     with a non-zero `installment_months`, the `monthly_payment` is
     recomputed; otherwise `installment_months` and `monthly_payment` stay
     as 0 until a user picks a plan.

Discount matching (`find_applicable_discount`):
  filter by project × payment_percent × is_duplex × area in [start, end]
  → first result by sort, then highest discount_percent.
  Returns None if no rule applies → discount_percent = 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.objects.models import Apartment, Floor, Project
    from apps.references.models import PaymentInPercent
    from apps.users.models import Staff


_HUNDRED = Decimal("100.00")
_ONE = Decimal("1.00")


@dataclass(frozen=True)
class CascadeStats:
    """Counts returned by `change_floor_price` so callers (action, cron) can
    report what happened without re-querying."""

    floor_id: int
    old_price: Decimal
    new_price: Decimal
    apartments_updated: int
    calculations_upserted: int
    price_history_id: int


def find_applicable_discount(
    apartment: "Apartment",
    payment_percent: "PaymentInPercent",
):
    """Return the best-matching `DiscountRule` for the given combo, or None.

    Matching rules:
      - rule.project == apartment's project
      - rule.is_active
      - rule.payment_percent == payment_percent
      - rule.is_duplex == apartment.is_duplex
      - rule.area_start <= apartment.area <= rule.area_end

    Among matches, pick lowest `sort` then highest `discount_percent`.
    """
    from apps.objects.models import DiscountRule

    project_id = apartment.floor.section.building.project_id
    return (
        DiscountRule.objects
        .filter(
            project_id=project_id,
            is_active=True,
            payment_percent=payment_percent,
            is_duplex=apartment.is_duplex,
            area_start__lte=apartment.area,
            area_end__gte=apartment.area,
        )
        .order_by("sort", "-discount_percent")
        .first()
    )


def recalc_apartment(apartment: "Apartment") -> int:
    """Recompute `total_price` on the apartment and upsert Calculation rows
    for every active PaymentInPercent lookup. Returns the number of
    Calculation rows touched.
    """
    from apps.objects.models import Calculation
    from apps.references.models import PaymentInPercent

    floor = apartment.floor
    base_price_per_sqm = floor.price_per_sqm

    apartment.total_price = (
        apartment.area * base_price_per_sqm + apartment.surcharge
    ).quantize(Decimal("0.01"))
    apartment.save(update_fields=["total_price", "modified_at"])

    touched = 0
    for pp in PaymentInPercent.objects.filter(is_active=True):
        rule = find_applicable_discount(apartment, pp)
        discount_percent = rule.discount_percent if rule else Decimal("0.00")

        new_price_per_sqm = (
            base_price_per_sqm * (_ONE - discount_percent / _HUNDRED)
        ).quantize(Decimal("0.01"))
        new_total_price = (
            apartment.area * new_price_per_sqm + apartment.surcharge
        ).quantize(Decimal("0.01"))
        initial_fee = (
            new_total_price * pp.percent / _HUNDRED
        ).quantize(Decimal("0.01"))

        calc, _created = Calculation.objects.get_or_create(
            apartment=apartment,
            payment_percent=pp,
            defaults={
                "discount_percent": discount_percent,
                "new_price_per_sqm": new_price_per_sqm,
                "new_total_price": new_total_price,
                "initial_fee": initial_fee,
            },
        )
        # If existing row has installment_months > 0, recompute monthly_payment;
        # otherwise leave monthly fields at zero and let a user pick a plan.
        if calc.installment_months and calc.installment_months > 0:
            monthly = ((new_total_price - initial_fee) / Decimal(calc.installment_months)).quantize(Decimal("0.01"))
        else:
            monthly = Decimal("0.00")

        Calculation.objects.filter(pk=calc.pk).update(
            discount_percent=discount_percent,
            new_price_per_sqm=new_price_per_sqm,
            new_total_price=new_total_price,
            initial_fee=initial_fee,
            monthly_payment=monthly,
        )
        touched += 1

    return touched


def recalc_floor(floor: "Floor") -> tuple[int, int]:
    """Recompute every apartment on this floor.

    Returns (apartments_updated, calculations_upserted).
    """
    apartments_updated = 0
    calcs_total = 0
    for apt in floor.apartments.all():
        calcs_total += recalc_apartment(apt)
        apartments_updated += 1
    return apartments_updated, calcs_total


def recalc_project(project: "Project") -> tuple[int, int]:
    """Recompute every apartment in the whole ЖК. Used by management command
    or migrations — not wired to any HTTP route yet (too expensive for a
    single request)."""
    from apps.objects.models import Floor

    apartments_updated = 0
    calcs_total = 0
    floors = Floor.objects.filter(
        section__building__project=project,
    ).select_related("section", "section__building")
    for floor in floors:
        a, c = recalc_floor(floor)
        apartments_updated += a
        calcs_total += c
    return apartments_updated, calcs_total


def change_floor_price(
    floor: "Floor",
    new_price: Decimal,
    *,
    by: "Staff | None" = None,
    comment: str = "",
) -> CascadeStats:
    """Atomically: write a PriceHistory row, update Floor.price_per_sqm,
    cascade to every apartment on the floor.

    Uses `select_for_update` on the Floor row to prevent two concurrent price
    changes from racing. If `new_price == old_price`, writes a PriceHistory
    row anyway (as an explicit "touched" marker) and skips the cascade.
    """
    from apps.objects.models import Floor, PriceHistory

    new_price = Decimal(new_price).quantize(Decimal("0.01"))

    with transaction.atomic():
        f = Floor.objects.select_for_update().get(pk=floor.pk)
        old_price = f.price_per_sqm

        history = PriceHistory.objects.create(
            floor=f,
            old_price=old_price,
            new_price=new_price,
            changed_by=by,
            comment=comment,
        )

        if old_price == new_price:
            return CascadeStats(
                floor_id=f.pk,
                old_price=old_price,
                new_price=new_price,
                apartments_updated=0,
                calculations_upserted=0,
                price_history_id=history.pk,
            )

        f.price_per_sqm = new_price
        f.save(update_fields=["price_per_sqm", "modified_at"])

        apartments_updated, calcs = recalc_floor(f)

    return CascadeStats(
        floor_id=f.pk,
        old_price=old_price,
        new_price=new_price,
        apartments_updated=apartments_updated,
        calculations_upserted=calcs,
        price_history_id=history.pk,
    )
