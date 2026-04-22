"""Simple reference lookups — 13 small tables sharing `LookupModel`.

All inherit `apps.core.models.LookupModel` (abstract), which contributes:
  - `name: I18nField`
  - `sort: PositiveSmallIntegerField(default=0, db_index=True)`
  - `is_active: BooleanField` (from BaseModel)
  - `created_at / modified_at` (from TimeStampedModel)

Each concrete subclass just sets Meta verbose names. A few add domain-specific
extra fields (Badge.color, Location.region, PaymentInPercent.percent).

Permission: all 13 share the `references.lookups.*` bundle (see
`apps.core.permission_tree`).
"""
from __future__ import annotations

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import PercentField
from apps.core.models import LookupModel

# --- Building-material / apartment-facing lookups -----------------------------


class ApartmentType(LookupModel):
    """Квартира / апартаменты / нежилое и т.д."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Тип помещения")
        verbose_name_plural = _("Типы помещений")


class RoomType(LookupModel):
    """Студия / 1-комн / 2-комн / ... — shortcut label on apartment cards."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Тип планировки (комнатность)")
        verbose_name_plural = _("Типы планировок")


class ConstructionStage(LookupModel):
    """Этап строительства: котлован, фундамент, ..., сдан."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Этап строительства")
        verbose_name_plural = _("Этапы строительства")


class Decoration(LookupModel):
    """Отделка квартиры: без отделки, чистовая, предчистовая, с ремонтом и т.п."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Тип отделки")
        verbose_name_plural = _("Типы отделки")


class PremisesDecoration(LookupModel):
    """Отделка помещений (отдельно от квартирной — для МОП / холлов / фасадов)."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Отделка помещений")
        verbose_name_plural = _("Отделки помещений")


class HomeMaterial(LookupModel):
    """Материал дома: кирпич / монолит / панель / каркас."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Материал дома")
        verbose_name_plural = _("Материалы дома")


class OutputWindows(LookupModel):
    """Вид из окон: во двор / на улицу / торцевые / угловые."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Вид из окна")
        verbose_name_plural = _("Виды из окон")


class OccupiedBy(LookupModel):
    """Кем занято / забронировано (учётная категория)."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Кем занято")
        verbose_name_plural = _("Категории занятости")


class Badge(LookupModel):
    """Тэги квартир: новинка, акция, хит, последняя и т.п.

    Extra: `color` (hex) — отображаемый цвет плашки на карточке квартиры.
    """

    HEX_COLOR_REGEX = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"
    color = models.CharField(
        _("Цвет"),
        max_length=7,
        blank=True,
        validators=[
            RegexValidator(
                regex=HEX_COLOR_REGEX,
                message=_("Цвет должен быть в формате #RGB или #RRGGBB."),
            ),
        ],
        help_text=_("Hex, напр. #22C55E"),
    )

    class Meta(LookupModel.Meta):
        verbose_name = _("Тег (бейдж)")
        verbose_name_plural = _("Теги квартир")


# --- Payment-related lookups --------------------------------------------------


class PaymentMethod(LookupModel):
    """Способы оплаты на уровне договора: 100% / рассрочка / ипотека."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Способ оплаты")
        verbose_name_plural = _("Способы оплаты")


class PaymentInPercent(LookupModel):
    """Процентная шкала оплаты — ступенчатые уровни первого взноса, которые
    участвуют в расчёте скидок (`DiscountRule` их FK'ает в Этапе 3).

    Extra: `percent` (0..100) — собственно значение.
    """

    percent = PercentField(_("Процент"))

    class Meta(LookupModel.Meta):
        verbose_name = _("Шаг процента оплаты")
        verbose_name_plural = _("Шкала процентов оплаты")
        ordering = ["percent"]


# --- Geography ----------------------------------------------------------------


class Region(LookupModel):
    """Область / вилоят."""

    class Meta(LookupModel.Meta):
        verbose_name = _("Регион")
        verbose_name_plural = _("Регионы")


class Location(LookupModel):
    """Населённый пункт (город / район) — может быть привязан к региону."""

    region = models.ForeignKey(
        Region,
        verbose_name=_("Регион"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="locations",
    )

    class Meta(LookupModel.Meta):
        verbose_name = _("Населённый пункт")
        verbose_name_plural = _("Населённые пункты")
