"""ClientStatus — small domain-specific lookup (Лид / Активен / Закрыт ...).

Kept inside `apps.clients` instead of `references` because the values are
only meaningful inside the sales pipeline. `color` lets the frontend paint
a status chip consistently across list and detail views.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import LookupModel


class ClientStatus(LookupModel):
    color = models.CharField(
        _("Цвет"), max_length=16, blank=True,
        help_text=_("Любой CSS-цвет или пресет из chip палитры."),
    )

    class Meta(LookupModel.Meta):
        verbose_name = _("Статус клиента")
        verbose_name_plural = _("Статусы клиентов")
