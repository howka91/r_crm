"""PriceHistory — append-only ledger of Floor.price_per_sqm changes.

Written by `apps.objects.services.pricing` (phase 3.4) inside the same
transaction that updates the Floor price and re-runs the downstream cascade
(Apartment.total_price, Calculation rows). Never mutate after insert.

Not a BaseModel — no `is_active`/soft-delete semantics. Logs are immutable
records of what happened.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PriceHistory(models.Model):
    floor = models.ForeignKey(
        "objects.Floor",
        on_delete=models.CASCADE,
        related_name="price_history",
        verbose_name=_("Этаж"),
    )
    old_price = models.DecimalField(
        _("Старая цена за м²"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    new_price = models.DecimalField(
        _("Новая цена за м²"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="floor_price_changes",
        verbose_name=_("Кто изменил"),
    )
    comment = models.CharField(_("Комментарий"), max_length=512, blank=True)
    created_at = models.DateTimeField(_("Когда"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Запись истории цен")
        verbose_name_plural = _("История цен")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["floor", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Floor #{self.floor_id}: {self.old_price} → {self.new_price}"
