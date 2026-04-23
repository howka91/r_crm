"""ContractTemplate — `.docx` file + declared placeholders.

`placeholders` is a list of `{model, field, field_name, description}` entries
that describe which values the template expects. The docgen service (Phase
5.3) reads this list, pulls the corresponding values off the Contract tree
(apartment, client, calculation, project.developer, …) and fills the `.docx`
before converting to PDF.

Shape example::

    [
      {"model": "Client", "field": "full_name", "field_name": "ФИО клиента"},
      {"model": "Apartment", "field": "number", "field_name": "№ квартиры"},
      {"model": "Contract", "field": "total_amount", "field_name": "Сумма"},
    ]

Legacy stored these rows in a separate `clients_contracttemplatefield` table
(39 rows across 14 templates). We collapse into a JSONField because the
volume is tiny and they're always loaded alongside the template.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ContractTemplate(BaseModel):
    title = models.CharField(_("Название"), max_length=255, db_index=True)
    file = models.FileField(
        _("Файл шаблона (.docx)"), upload_to="contract_templates/",
    )
    author = models.ForeignKey(
        "users.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_templates",
        verbose_name=_("Автор"),
    )
    placeholders = models.JSONField(
        _("Плейсхолдеры"), default=list, blank=True,
        help_text=_("Список описаний полей: [{model, field, field_name, description}]"),
    )

    class Meta:
        verbose_name = _("Шаблон договора")
        verbose_name_plural = _("Шаблоны договоров")
        ordering = ["-modified_at", "id"]

    def __str__(self) -> str:
        return self.title or f"Template #{self.pk}"
