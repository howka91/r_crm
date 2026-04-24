"""Planning (планировка квартиры) — shared catalog of floor layouts.

One `Planning` describes a specific apartment layout within a project
(ЖК): "3-комнатная торцевая", "Пентхаус", etc. An apartment references
its layout via `Apartment.planning` (nullable FK) so one planning can
be reused across hundreds of identical apartments. Each entry carries
two images — the 2D schematic ("вид сверху") and the 3D render.

Scope is strict: a planning belongs to exactly one `Project`. Layouts
don't travel between developers or between ЖК — even visually similar
architectures have different dimensions, so sharing would be a footgun.
The cross-project invariant is enforced on Apartment write (see
ApartmentSerializer.validate).
"""
from __future__ import annotations

from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel


class Planning(BaseModel):
    project = models.ForeignKey(
        "objects.Project",
        on_delete=models.PROTECT,
        related_name="plannings",
        verbose_name=_("ЖК"),
    )
    # Manager-facing short label shown next to the name in pickers and
    # audit logs, e.g. "3К-А" or "P-01". Optional, but when set it's
    # unique within a project (partial index — empty codes don't collide).
    code = models.CharField(_("Код"), max_length=50, blank=True)
    name = I18nField(verbose_name=_("Название"))
    rooms_count = models.PositiveSmallIntegerField(
        _("Комнат"), null=True, blank=True,
    )
    area = models.DecimalField(
        _("Площадь, м²"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    image_2d = models.ImageField(
        _("Изображение 2D"),
        upload_to="references/plannings/2d/%Y/%m/",
        null=True,
        blank=True,
    )
    image_3d = models.ImageField(
        _("Изображение 3D"),
        upload_to="references/plannings/3d/%Y/%m/",
        null=True,
        blank=True,
    )
    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("Планировка")
        verbose_name_plural = _("Планировки")
        ordering = ["sort", "id"]
        constraints = [
            UniqueConstraint(
                fields=["project", "code"],
                condition=Q(code__gt=""),
                name="refs_planning_unique_code_per_project",
            ),
        ]

    def __str__(self) -> str:
        label = ""
        if isinstance(self.name, dict):
            label = self.name.get("ru") or self.name.get("uz") or ""
        if not label:
            label = f"#{self.pk}"
        return f"{self.code} · {label}" if self.code else label
