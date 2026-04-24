"""Section duplication — clone a full Section subtree into another Building.

Copies the Section itself plus every Floor and every Apartment underneath.
Calculations are intentionally NOT cloned: they're derived data and will be
re-materialised lazily (or via pricing.recalc_apartment when the user
changes prices on the new floors).

Booking state is reset on the copy — every Apartment arrives as `free` with
no `booking_expires_at`. Otherwise we'd import zombie reservations tied to
the source section.

Number collision: Section.number is unique per Building. If the source
section's number is already taken in the target Building, we bump to
max(existing)+1 so the clone always inserts cleanly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.objects.models import Building, Section


@dataclass(frozen=True)
class DuplicationResult:
    new_section_id: int
    floors_created: int
    apartments_created: int


def duplicate_section(
    source: "Section",
    target_building: "Building",
) -> DuplicationResult:
    """Clone `source` into `target_building`, returning the new Section's id
    plus counts of children created. Runs in one transaction — either the
    whole subtree lands or none of it does.
    """
    from apps.objects.models import Apartment, Floor, Section

    with transaction.atomic():
        # Pick a safe section number: keep source's if free, else bump.
        taken = set(
            Section.objects
            .filter(building=target_building)
            .values_list("number", flat=True),
        )
        new_number = source.number
        if new_number in taken:
            new_number = (max(taken) if taken else 0) + 1

        new_section = Section.objects.create(
            building=target_building,
            title=source.title,
            number=new_number,
            planning_file=None,  # files aren't copied; re-upload if needed
            sort=source.sort,
            is_active=True,
        )

        floors_created = 0
        apartments_created = 0

        src_floors = source.floors.order_by("number", "id")
        for src_floor in src_floors:
            new_floor = Floor.objects.create(
                section=new_section,
                number=src_floor.number,
                price_per_sqm=src_floor.price_per_sqm,
                sort=src_floor.sort,
                is_active=True,
            )
            floors_created += 1

            src_apts = src_floor.apartments.order_by("number", "id")
            for a in src_apts:
                new_apt = Apartment.objects.create(
                    floor=new_floor,
                    number=a.number,
                    rooms_count=a.rooms_count,
                    area=a.area,
                    total_bti_area=a.total_bti_area,
                    total_price=a.total_price,
                    surcharge=a.surcharge,
                    is_duplex=a.is_duplex,
                    is_studio=a.is_studio,
                    is_euro_planning=a.is_euro_planning,
                    # `planning` intentionally not copied — if target_building
                    # lives in a different ЖК, the reference would be
                    # cross-project (rejected by ApartmentSerializer). Even
                    # within the same ЖК, the manager re-picks the layout
                    # after cloning so the catalog stays the source of truth.
                    decoration=a.decoration,
                    output_window=a.output_window,
                    occupied_by=a.occupied_by,
                    # Always reset booking state on the clone.
                    status="free",
                    booking_expires_at=None,
                    sort=a.sort,
                    is_active=True,
                )
                # M2M has to be set after the instance exists.
                new_apt.characteristics.set(a.characteristics.all())
                apartments_created += 1

    return DuplicationResult(
        new_section_id=new_section.pk,
        floors_created=floors_created,
        apartments_created=apartments_created,
    )
