"""Currency — ISO 4217 code + rate to UZS. UZS itself has rate=1."""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel


class Currency(BaseModel):
    """Rates are manually updated in Phase 2. Later phases may add a scheduled
    task to pull rates from cbu.uz."""

    code = models.CharField(
        _("Код"),
        max_length=3,
        unique=True,
        help_text=_("ISO 4217: UZS, USD, EUR, RUB, …"),
    )
    symbol = models.CharField(_("Символ"), max_length=4, blank=True)
    name = I18nField(verbose_name=_("Название"))
    rate = models.DecimalField(
        _("Курс к UZS"),
        max_digits=14,
        decimal_places=4,
        default=Decimal("1.0000"),
        help_text=_("1 единица валюты = N UZS"),
    )

    class Meta:
        verbose_name = _("Валюта")
        verbose_name_plural = _("Валюты")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        # Normalize code to uppercase so 'usd' == 'USD'.
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)
