"""Apartment (квартира) — the sellable unit.

Sits at the bottom of the Objects hierarchy: Project → Building → Section →
Floor → **Apartment**. Status is a CharField with a fixed choice set; legal
transitions are enforced by `apps.objects.services.apartments.change_status`
(not via signals — cf. CLAUDE.md).

`total_price` is a stored Decimal that gets recomputed by the pricing service
when Floor.price_per_sqm changes. Phase 3.3 introduces the explicit recalc
function (`services/pricing.recalc_floor`). Until then, `total_price` is set
by the caller on create/update.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Apartment(BaseModel):
    class Status(models.TextChoices):
        FREE = "free", _("Свободно")
        BOOKED = "booked", _("Забронировано")
        BOOKED_VIP = "booked_vip", _("Бронь руководства")
        FORMALIZED = "formalized", _("Оформлено")
        ESCROW = "escrow", _("Эскроу")
        SOLD = "sold", _("Продано")

    floor = models.ForeignKey(
        "objects.Floor",
        on_delete=models.PROTECT,
        related_name="apartments",
        verbose_name=_("Этаж"),
    )
    number = models.CharField(
        _("Номер квартиры"), max_length=32, db_index=True,
        help_text=_("Строка, т.к. в легаси встречаются буквы (12А)."),
    )
    rooms_count = models.PositiveSmallIntegerField(
        _("Число комнат"), default=1,
    )

    # Площади и цены — всегда Decimal, никогда Float.
    area = models.DecimalField(
        _("Площадь, м²"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_bti_area = models.DecimalField(
        _("БТИ-площадь, м²"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_price = models.DecimalField(
        _("Итоговая цена, UZS"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Обновляется сервисом pricing при изменении цены этажа."),
    )
    surcharge = models.DecimalField(
        _("Наценка, UZS"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Разовая наценка для данной квартиры (не %)."),
    )

    # Планировка / тип.
    is_duplex = models.BooleanField(_("Дуплекс"), default=False)
    is_studio = models.BooleanField(_("Студия"), default=False)
    is_euro_planning = models.BooleanField(_("Европлан"), default=False)

    # Reference to the shared planning catalog (references.Planning).
    # One planning describes many apartments (sharing "вид сверху" +
    # 3D-render). Cross-project mismatch is rejected in the serializer.
    planning = models.ForeignKey(
        "references.Planning",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apartments",
        verbose_name=_("Планировка"),
    )

    # FK на справочники (references). Необязательны — данные могут отсутствовать.
    decoration = models.ForeignKey(
        "references.Decoration",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apartments",
        verbose_name=_("Отделка"),
    )
    output_window = models.ForeignKey(
        "references.OutputWindows",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apartments",
        verbose_name=_("Вид из окон"),
    )
    occupied_by = models.ForeignKey(
        "references.OccupiedBy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apartments",
        verbose_name=_("Категория занятости"),
    )
    characteristics = models.ManyToManyField(
        "references.Badge",
        blank=True,
        related_name="apartments",
        verbose_name=_("Характеристики (теги)"),
    )

    # Статус и бронь.
    status = models.CharField(
        _("Статус"),
        max_length=16,
        choices=Status.choices,
        default=Status.FREE,
        db_index=True,
    )
    booking_expires_at = models.DateTimeField(
        _("Бронь истекает"), null=True, blank=True, db_index=True,
        help_text=_("Заполняется при бронировании; пустая для других статусов."),
    )

    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("Квартира")
        verbose_name_plural = _("Квартиры")
        ordering = ["floor_id", "sort", "number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["floor", "number"],
                name="objects_apartment_unique_number_per_floor",
            ),
        ]

    def __str__(self) -> str:
        return f"Apt {self.number}"
