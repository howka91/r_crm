"""Building (корпус/блок). FK → Project, contains many Sections.

Intentionally NOT named `Apartment` — in the legacy DB `apartments_apartment`
was a building (!). The new naming convention (CLAUDE.md#naming) flips this:
Building = корпус, Apartment = квартира. The legacy migration script must
map `apartments_apartment` → `objects.Building` accordingly.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel


class Building(BaseModel):
    project = models.ForeignKey(
        "objects.Project",
        on_delete=models.PROTECT,
        related_name="buildings",
        verbose_name=_("ЖК"),
    )
    title = I18nField(verbose_name=_("Название"))

    # External building number as it appears in signage / legal docs ("Блок 3",
    # "Корпус 12А"). Free-form because legacy data includes letters.
    number = models.CharField(_("Номер корпуса"), max_length=32, blank=True)

    cadastral_number = models.CharField(
        _("Кадастровый номер"), max_length=64, blank=True, db_index=True,
    )
    date_of_issue = models.DateField(_("Дата ввода в эксплуатацию"), null=True, blank=True)

    planning_file = models.FileField(
        _("Файл планировки корпуса"),
        upload_to="objects/buildings/planning/",
        null=True,
        blank=True,
    )

    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("Корпус")
        verbose_name_plural = _("Корпуса")
        ordering = ["project_id", "sort", "id"]

    def __str__(self) -> str:
        if isinstance(self.title, dict):
            t = self.title.get("ru") or self.title.get("uz")
            if t:
                return t
        return f"Building #{self.pk}"
