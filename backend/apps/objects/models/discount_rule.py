"""DiscountRule — per-project discount matrix row.

Matches legacy `rc_objects_discountpercent`. A rule says: "for apartments in
area range [area_start, area_end] paying `payment_percent` up-front, apply
`discount_percent`." Duplex rules are kept separate via the `is_duplex` flag
(history from legacy: duplex apartments had their own rate card).

Matching logic lives in `apps.objects.services.pricing` (phase 3.4).
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class DiscountRule(BaseModel):
    project = models.ForeignKey(
        "objects.Project",
        on_delete=models.PROTECT,
        related_name="discount_rules",
        verbose_name=_("ЖК"),
    )

    area_start = models.DecimalField(
        _("Площадь от, м²"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    area_end = models.DecimalField(
        _("Площадь до, м²"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    payment_percent = models.ForeignKey(
        "references.PaymentInPercent",
        on_delete=models.PROTECT,
        related_name="discount_rules",
        verbose_name=_("Процент оплаты"),
    )
    discount_percent = models.DecimalField(
        _("Скидка, %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )

    is_duplex = models.BooleanField(
        _("Для дуплексов"), default=False,
        help_text=_("Правило применяется только к квартирам-дуплексам."),
    )

    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("Правило скидок")
        verbose_name_plural = _("Правила скидок")
        ordering = ["project_id", "sort", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(area_end__gte=models.F("area_start")),
                name="objects_discountrule_area_end_gte_start",
            ),
        ]

    def __str__(self) -> str:
        kind = " (duplex)" if self.is_duplex else ""
        return (
            f"[{self.project_id}] {self.area_start}-{self.area_end} м²"
            f" @ {self.discount_percent}%{kind}"
        )
