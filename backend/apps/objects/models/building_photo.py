"""BuildingPhoto — gallery entry on a Building (корпус).

Same shape as `ProjectPhoto` but scoped to a single building. See that
model's docstring for the cover/sort rationale.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class BuildingPhoto(BaseModel):
    building = models.ForeignKey(
        "objects.Building",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Корпус"),
    )
    file = models.ImageField(
        _("Фото"),
        upload_to="objects/buildings/photos/%Y/%m/",
    )
    caption = models.CharField(
        _("Подпись"),
        max_length=255,
        blank=True,
    )
    sort = models.PositiveSmallIntegerField(
        _("Порядок"),
        default=0,
        db_index=True,
        help_text=_("Минимальное значение — обложка."),
    )

    class Meta:
        verbose_name = _("Фото корпуса")
        verbose_name_plural = _("Фото корпусов")
        ordering = ["sort", "id"]

    def __str__(self) -> str:
        return self.caption or f"BuildingPhoto #{self.pk}"
