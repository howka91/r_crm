"""Client — sales pipeline counterparty (phys or jur).

`phones` / `emails` use Postgres ArrayField (the project is Postgres-only
per docker-compose.yml). `entity` discriminator drives which other fields
are meaningful:

  * entity='phys' → `full_name`, `gender`, `birth_date`, `pin` (ПИНФЛ)
  * entity='jur'  → `full_name` (company), `inn`, `oked`

Keep all columns on the one table rather than splitting into two models
— in legacy the split caused double-book errors on conversion. Business
rules (which fields are required per entity type) live in the serializer.
"""
from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Client(BaseModel):
    class Entity(models.TextChoices):
        PHYS = "phys", _("Физ. лицо")
        JUR = "jur", _("Юр. лицо")

    class Gender(models.TextChoices):
        MALE = "male", _("Мужской")
        FEMALE = "female", _("Женский")

    entity = models.CharField(
        _("Тип"),
        max_length=8,
        choices=Entity.choices,
        default=Entity.PHYS,
        db_index=True,
    )
    gender = models.CharField(
        _("Пол"),
        max_length=8,
        choices=Gender.choices,
        blank=True,
        help_text=_("Применимо только для физ. лица."),
    )

    full_name = models.CharField(_("ФИО / Название"), max_length=255, db_index=True)

    phones = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
        verbose_name=_("Телефоны"),
    )
    emails = ArrayField(
        models.EmailField(max_length=128),
        default=list,
        blank=True,
        verbose_name=_("Email-адреса"),
    )

    inn = models.CharField(_("ИНН"), max_length=16, blank=True, db_index=True)
    oked = models.CharField(_("ОКЭД"), max_length=16, blank=True)
    pin = models.CharField(
        _("ПИНФЛ"), max_length=16, blank=True, db_index=True,
        help_text=_("Персональный идентификационный номер физ. лица."),
    )
    birth_date = models.DateField(_("Дата рождения"), null=True, blank=True)

    address = models.CharField(_("Адрес"), max_length=512, blank=True)
    description = models.TextField(_("Заметки"), blank=True)

    manager = models.ForeignKey(
        "users.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_clients",
        verbose_name=_("Менеджер"),
    )
    status = models.ForeignKey(
        "clients.ClientStatus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
        verbose_name=_("Статус"),
    )
    groups = models.ManyToManyField(
        "clients.ClientGroup",
        blank=True,
        related_name="clients",
        verbose_name=_("Группы"),
    )

    class Meta:
        verbose_name = _("Клиент")
        verbose_name_plural = _("Клиенты")
        ordering = ["-created_at", "id"]
        indexes = [
            models.Index(fields=["entity", "full_name"]),
        ]

    def __str__(self) -> str:
        return self.full_name or f"Client #{self.pk}"
