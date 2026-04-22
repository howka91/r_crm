"""Developer (застройщик) — юрлицо-строитель. One Developer owns many Projects."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel
from apps.references.models._validators import phone_validator


class Developer(BaseModel):
    name = I18nField(verbose_name=_("Название"))
    director = models.CharField(_("Директор"), max_length=255, blank=True)
    address = models.CharField(_("Адрес"), max_length=512, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    phone = models.CharField(
        _("Телефон"),
        max_length=13,
        blank=True,
        validators=[phone_validator],
    )

    # --- Bank requisites ---
    bank_name = models.CharField(_("Название банка"), max_length=255, blank=True)
    bank_account = models.CharField(_("Расчётный счёт"), max_length=32, blank=True)
    inn = models.CharField(_("ИНН"), max_length=16, blank=True, db_index=True)
    nds = models.CharField(_("Регистрация НДС"), max_length=32, blank=True)
    oked = models.CharField(_("ОКЭД"), max_length=16, blank=True)

    # --- Extension point ---
    # Stash rarely-used fields (mfo, branch_code, legal_form, etc.) without
    # schema churn. Keep the structured fields above for anything we actually
    # query or display in UI.
    extra = models.JSONField(_("Доп. данные"), default=dict, blank=True)

    class Meta:
        verbose_name = _("Застройщик")
        verbose_name_plural = _("Застройщики")
        ordering = ["id"]
