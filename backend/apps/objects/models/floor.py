"""Floor (этаж). FK → Section, contains many Apartments.

`price_per_sqm` is the base price-per-square-metre for apartments on this
floor. Changes here cascade to every apartment's `total_price` and every
calculation — **but** the cascade is triggered **explicitly** via
`apps.objects.services.pricing.recalc_floor(floor)`, never via signals.
(Signal-based cascade was a bug source in the legacy code; see CLAUDE.md.)

`PriceHistory` (phase 3.3) will log every `price_per_sqm` change.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Floor(BaseModel):
    section = models.ForeignKey(
        "objects.Section",
        on_delete=models.PROTECT,
        related_name="floors",
        verbose_name=_("Подъезд"),
    )
    number = models.SmallIntegerField(
        _("Номер этажа"),
        help_text=_("Может быть отрицательным для подземных уровней."),
    )
    price_per_sqm = models.DecimalField(
        _("Цена за м²"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("Этаж")
        verbose_name_plural = _("Этажи")
        ordering = ["section_id", "number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "number"],
                name="objects_floor_unique_number_per_section",
            ),
        ]

    def __str__(self) -> str:
        return f"Floor {self.number}"
