"""Requisite — bank details record attached to a Client.

One client can have multiple requisites (internal = our bank + external =
their bank, or several per currency). Populated when minting contracts.

`bank_requisite` shape (by convention — UI builds the form, serializer
validates required keys):

    {
      "account": "2020...",
      "bank": "Hamkorbank",
      "mfo": "00449",
      "currency": "UZS"          // optional ISO 4217
    }
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Requisite(BaseModel):
    class Kind(models.TextChoices):
        INTERNAL = "internal", _("Внутренний")
        LOCAL = "local", _("Местный")

    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="requisites",
        verbose_name=_("Клиент"),
    )
    type = models.CharField(
        _("Тип"),
        max_length=16,
        choices=Kind.choices,
        default=Kind.LOCAL,
        db_index=True,
    )
    bank_requisite = models.JSONField(
        _("Банковские реквизиты"), default=dict, blank=True,
    )

    class Meta:
        verbose_name = _("Банковский реквизит")
        verbose_name_plural = _("Банковские реквизиты")
        ordering = ["id"]

    def __str__(self) -> str:
        bank = self.bank_requisite.get("bank") if isinstance(self.bank_requisite, dict) else None
        return f"{self.get_type_display()} · {bank or '—'}"
