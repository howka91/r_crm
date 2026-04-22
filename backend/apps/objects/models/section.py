"""Section (подъезд). FK → Building, contains many Floors."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel


class Section(BaseModel):
    building = models.ForeignKey(
        "objects.Building",
        on_delete=models.PROTECT,
        related_name="sections",
        verbose_name=_("Корпус"),
    )
    title = I18nField(verbose_name=_("Название"))

    # Podyezd number as customers see it ("Подъезд 1").
    number = models.PositiveSmallIntegerField(_("Номер подъезда"), default=1)

    planning_file = models.FileField(
        _("Файл планировки подъезда"),
        upload_to="objects/sections/planning/",
        null=True,
        blank=True,
    )

    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("Подъезд")
        verbose_name_plural = _("Подъезды")
        ordering = ["building_id", "sort", "number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["building", "number"],
                name="objects_section_unique_number_per_building",
            ),
        ]

    def __str__(self) -> str:
        if isinstance(self.title, dict):
            t = self.title.get("ru") or self.title.get("uz")
            if t:
                return t
        return f"Section #{self.number}"
