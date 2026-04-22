"""Project (ЖК — жилой комплекс). Root of the objects hierarchy.

One `Developer` (references app) owns many `Project`s; each `Project` contains
many `Building`s. The `contract_number_index` is an auto-increment counter
scoped to the project — used by the contracts app to mint unique per-project
contract numbers (e.g. "ЯМ-00001", "ЯМ-00002") without cross-project collisions.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.models import BaseModel


class Project(BaseModel):
    developer = models.ForeignKey(
        "references.Developer",
        on_delete=models.PROTECT,
        related_name="projects",
        verbose_name=_("Застройщик"),
    )
    title = I18nField(verbose_name=_("Название"))
    address = models.CharField(_("Адрес"), max_length=512, blank=True)
    description = I18nField(verbose_name=_("Описание"), blank=True)

    # List of banks accepting payments for apartments in this project.
    # Shape: [{"name": "...", "logo": "...", "account": "..."}, ...]
    banks = models.JSONField(_("Банки"), default=list, blank=True)

    # Per-project sequence for contract numbers. Contracts app increments this
    # inside a transaction+select_for_update when minting a new contract.
    contract_number_index = models.PositiveIntegerField(
        _("Счётчик договоров"),
        default=0,
        help_text=_("Последний выданный порядковый номер договора в рамках ЖК."),
    )

    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
    )

    class Meta:
        verbose_name = _("Жилой комплекс")
        verbose_name_plural = _("Жилые комплексы")
        ordering = ["sort", "id"]

    def __str__(self) -> str:
        if isinstance(self.title, dict):
            return self.title.get("ru") or self.title.get("uz") or f"Project #{self.pk}"
        return str(self.title)
