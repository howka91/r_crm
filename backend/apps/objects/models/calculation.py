"""Calculation — precomputed price-per-apartment per PaymentInPercent bucket.

Legacy `flats_calculation` stored these rows so the sales UI could show a
price table without recomputing on every page load. We preserve the same
idea: for each apartment × payment_in_percent combination, store the final
numbers (price/sqm after discount, total, initial fee, monthly payment).

These rows are refreshed by `apps.objects.services.pricing` (phase 3.4)
whenever inputs change: Floor.price_per_sqm, apartment attributes, or
DiscountRule definitions. No signals — the service is called explicitly.

CASCADE on Apartment: if an apartment is deleted its calculations go with
it. They're derived data, not independently meaningful.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Calculation(BaseModel):
    apartment = models.ForeignKey(
        "objects.Apartment",
        on_delete=models.CASCADE,
        related_name="calculations",
        verbose_name=_("Квартира"),
    )
    payment_percent = models.ForeignKey(
        "references.PaymentInPercent",
        on_delete=models.PROTECT,
        related_name="calculations",
        verbose_name=_("Процент оплаты"),
    )

    discount_percent = models.DecimalField(
        _("Применённая скидка, %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    installment_months = models.PositiveSmallIntegerField(
        _("Срок рассрочки, мес."), default=0,
    )

    new_price_per_sqm = models.DecimalField(
        _("Цена за м² после скидки"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    new_total_price = models.DecimalField(
        _("Итоговая цена"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    initial_fee = models.DecimalField(
        _("Первый взнос"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    monthly_payment = models.DecimalField(
        _("Ежемесячный платёж"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = _("Расчёт")
        verbose_name_plural = _("Расчёты по квартирам")
        ordering = ["apartment_id", "payment_percent_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["apartment", "payment_percent"],
                name="objects_calculation_unique_apt_payment_percent",
            ),
        ]

    def __str__(self) -> str:
        return f"Calc apt#{self.apartment_id} @ payment#{self.payment_percent_id}"
