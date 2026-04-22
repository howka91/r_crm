"""SalesOffice (отдел продаж) — физическая точка встречи с клиентами."""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel
from apps.references.models._validators import phone_validator


class SalesOffice(BaseModel):
    """Used for: filtering leads/clients by office, map pins in the public
    catalog (Leaflet), routing SMS from a specific office, etc."""

    name = I18nField(verbose_name=_("Название"))
    address = models.CharField(_("Адрес"), max_length=512, blank=True)

    # Geographic coordinates — decimal degrees, WGS84.
    latitude = models.DecimalField(
        _("Широта"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
    )
    longitude = models.DecimalField(
        _("Долгота"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
    )

    work_start = models.TimeField(_("Начало работы"), null=True, blank=True)
    work_end = models.TimeField(_("Конец работы"), null=True, blank=True)

    phone = models.CharField(
        _("Телефон"),
        max_length=13,
        blank=True,
        validators=[phone_validator],
    )
    photo = models.ImageField(
        _("Фото"),
        upload_to="references/sales_offices/",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Отдел продаж")
        verbose_name_plural = _("Отделы продаж")
        ordering = ["id"]
