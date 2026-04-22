"""ApartmentStatusLog — append-only ledger of status transitions.

Written exclusively by `apps.objects.services.apartments.change_status` so
that every transition has an actor and a transaction boundary. Never mutate
existing rows.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ApartmentStatusLog(models.Model):
    apartment = models.ForeignKey(
        "objects.Apartment",
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name=_("Квартира"),
    )
    old_status = models.CharField(
        _("Старый статус"), max_length=16, blank=True,
    )
    new_status = models.CharField(
        _("Новый статус"), max_length=16,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apartment_status_changes",
        verbose_name=_("Кто изменил"),
    )
    comment = models.CharField(_("Комментарий"), max_length=512, blank=True)
    created_at = models.DateTimeField(_("Когда"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Запись лога статусов")
        verbose_name_plural = _("Лог статусов квартир")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["apartment", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Apt #{self.apartment_id}: {self.old_status or '∅'} → {self.new_status}"
