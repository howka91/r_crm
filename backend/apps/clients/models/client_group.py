"""ClientGroup — optional segmentation tag (VIP / Партнёр / Рассрочка ...).

Many clients ↔ many groups. Used for filtering and SMS audience building.
"""
from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from apps.core.models import LookupModel


class ClientGroup(LookupModel):
    class Meta(LookupModel.Meta):
        verbose_name = _("Группа клиентов")
        verbose_name_plural = _("Группы клиентов")
