"""PaymentSchedule — single line of a contract's payment calendar.

Legacy `clients_installmentplan` (4074 rows) is the 1:1 source. One schedule
row per due date; `paid_amount` accumulates as `Payment`s arrive against it
(recalculated by the payments service — *not* via signals).

`status` is kept as a real column (not derived) so listings can filter/index
on it cheaply. Its transitions are driven by the payments service:

    paid_amount == 0,                  due_date >= today → pending
    0 < paid_amount < amount,          due_date >= today → partial
    paid_amount >= amount                                → paid
    paid_amount <  amount,             due_date <  today → overdue

`debt` is an arithmetic property (no need to store).
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import BaseModel


class PaymentSchedule(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Ожидает оплаты")
        PARTIAL = "partial", _("Частично оплачен")
        PAID = "paid", _("Оплачен")
        OVERDUE = "overdue", _("Просрочен")

    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name=_("Договор"),
    )
    due_date = models.DateField(_("Срок оплаты"), db_index=True)
    amount = MoneyField(
        _("Сумма к оплате"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    paid_amount = MoneyField(
        _("Оплачено"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        _("Статус"),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    class Meta:
        verbose_name = _("Пункт графика")
        verbose_name_plural = _("График платежей")
        ordering = ["contract_id", "due_date", "id"]
        indexes = [
            models.Index(fields=["contract", "due_date"]),
            models.Index(fields=["status", "due_date"]),
        ]

    @property
    def debt(self) -> Decimal:
        """Unpaid remainder. Clipped at zero (overpayments don't go negative)."""
        remaining = (self.amount or Decimal("0.00")) - (self.paid_amount or Decimal("0.00"))
        return remaining if remaining > 0 else Decimal("0.00")

    def __str__(self) -> str:
        return f"C{self.contract_id} · {self.due_date.isoformat()} · {self.amount}"
