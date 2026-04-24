"""ProjectPhoto — gallery entry on a Project (ЖК).

Stores a single image with an optional caption and an integer `sort`
order. The photo with the lowest `sort` (tiebreak by id) is the cover —
shown on the hub card and as the hero on the project overview tab.

No explicit `is_cover` flag: drag-sort (future) or the "Make cover"
action rewrite `sort`, and the cover is always `photos[0]`. Keeps the
invariant simple — no risk of two covers or zero covers.

`on_delete=CASCADE` on the FK: photos are cosmetic, deleting the ЖК
should take them with it. Files on disk are left behind by Django (no
FieldFile.delete) — a manual cleanup command can prune orphans later.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ProjectPhoto(BaseModel):
    project = models.ForeignKey(
        "objects.Project",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("ЖК"),
    )
    file = models.ImageField(
        _("Фото"),
        upload_to="objects/projects/photos/%Y/%m/",
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
        verbose_name = _("Фото ЖК")
        verbose_name_plural = _("Фото ЖК")
        ordering = ["sort", "id"]

    def __str__(self) -> str:
        return self.caption or f"Photo #{self.pk}"
