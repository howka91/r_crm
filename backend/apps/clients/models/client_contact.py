"""ClientContact — representative / signatory of a client (was `Employee`
in the legacy schema; renamed per CLAUDE.md glossary).

Holds ID-document data (`passport` JSON) so contracts can be filled in
automatically. `is_chief` marks the default signatory when a single client
has multiple contacts.

`passport` shape (by convention — not validated at ORM level):

    {
      "series": "AB",
      "number": "1234567",
      "issued_by": "ОВД Чиланзарского района",
      "issued_date": "2019-05-12",
      "registration_address": "г. Ташкент, ..."
    }
"""
from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ClientContact(BaseModel):
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="contacts",
        verbose_name=_("Клиент"),
    )
    full_name = models.CharField(_("ФИО"), max_length=255)
    role = models.CharField(
        _("Роль"), max_length=128, blank=True,
        help_text=_("Например: директор, главный бухгалтер, подписант."),
    )
    is_chief = models.BooleanField(_("Главный подписант"), default=False)

    phones = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
        verbose_name=_("Телефоны"),
    )
    email = models.EmailField(_("Email"), max_length=128, blank=True)

    passport = models.JSONField(_("Паспортные данные"), default=dict, blank=True)
    birth_date = models.DateField(_("Дата рождения"), null=True, blank=True)

    inn = models.CharField(_("ИНН"), max_length=16, blank=True)
    pin = models.CharField(_("ПИНФЛ"), max_length=16, blank=True)

    class Meta:
        verbose_name = _("Контакт клиента")
        verbose_name_plural = _("Контакты клиентов")
        ordering = ["-is_chief", "id"]

    def __str__(self) -> str:
        return self.full_name or f"Contact #{self.pk}"
