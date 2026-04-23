"""Payment — a single inflow recorded against a PaymentSchedule line.

One schedule line can receive many Payments (partial payments). The payments
service (Phase 5.2) is responsible for recomputing `PaymentSchedule.paid_amount`
and `PaymentSchedule.status` whenever a Payment is created/modified.

`payment_type` lives here (not on Contract) — it describes the channel of
**this specific inflow**. A contract may combine cash + bank transfer across
its installments, which is why Contract only has a M2M list of declared
`PaymentMethod`s (the *plan*), while Payment has the concrete `payment_type`
(the *fact*).

FinanceRecord (cashbox / accounting) will be created alongside Payment in
Phase 6; for 5.1 we keep the models separate and rely on the future service
to tie them together.
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import BaseModel


class Payment(BaseModel):
    class Type(models.TextChoices):
        CASH = "cash", _("Наличные")
        BANK = "bank", _("Перечисление")
        BARTER = "barter", _("Бартер")

    schedule = models.ForeignKey(
        "contracts.PaymentSchedule",
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("Пункт графика"),
    )
    amount = MoneyField(
        _("Сумма"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payment_type = models.CharField(
        _("Канал оплаты"),
        max_length=16,
        choices=Type.choices,
        default=Type.CASH,
        db_index=True,
    )
    paid_at = models.DateField(
        _("Дата оплаты"), default=date_type.today, db_index=True,
    )
    recorded_by = models.ForeignKey(
        "users.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_payments",
        verbose_name=_("Кто зафиксировал"),
    )
    receipt_number = models.CharField(
        _("Номер ПКО"), max_length=50, blank=True, db_index=True,
    )
    comment = models.TextField(_("Комментарий"), blank=True)

    class Meta:
        verbose_name = _("Платёж")
        verbose_name_plural = _("Платежи")
        ordering = ["-paid_at", "-id"]
        indexes = [
            models.Index(fields=["schedule", "-paid_at"]),
        ]

    def __str__(self) -> str:
        return f"Pay {self.amount} @ {self.paid_at.isoformat()} (sch#{self.schedule_id})"
