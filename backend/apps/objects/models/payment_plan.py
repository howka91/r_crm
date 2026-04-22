"""PaymentPlan (план оплаты) — per-project configuration of installment terms.

Each project has several named plans (e.g. "100% upfront", "30/70 over 12
months", "0% down, 24 months"). A Contract references exactly one PaymentPlan
when minted; Calculation rows use PaymentInPercent (a 0/10/30/50/100 pct
bucket) independently.

PROTECT on Project so deleting a ЖК with payment plans requires an explicit
cleanup step.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel


class PaymentPlan(BaseModel):
    project = models.ForeignKey(
        "objects.Project",
        on_delete=models.PROTECT,
        related_name="payment_plans",
        verbose_name=_("ЖК"),
    )
    name = I18nField(verbose_name=_("Название"))

    down_payment_percent = models.DecimalField(
        _("Первый взнос, %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    installment_months = models.PositiveSmallIntegerField(
        _("Срок рассрочки, мес."), default=0,
    )

    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("План оплаты")
        verbose_name_plural = _("Планы оплаты")
        ordering = ["project_id", "sort", "id"]

    def __str__(self) -> str:
        if isinstance(self.name, dict):
            return self.name.get("ru") or self.name.get("uz") or f"#{self.pk}"
        return str(self.name)
