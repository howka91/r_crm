"""ContractTemplate — HTML template for PDF contract generation.

Design decision (Phase 5.3): we store templates as HTML (not .docx) because:

  * The admin UI is a Tiptap WYSIWYG editor — producing HTML natively
    with inline styles (fonts, sizes, bold/italic/underline, alignment).
  * HTML → PDF via WeasyPrint runs in-process in the backend, no
    separate LibreOffice container. That drops ~500 MB from compose and
    cuts conversion latency.
  * Previews are trivial — render the same template to HTML in the
    browser.

Placeholders
------------

The body uses `{{key}}` markers. Valid keys are declared per-template by
the admin in ``placeholders``::

    [
      {"key": "contract_number", "path": "contract.contract_number",  "label": "Номер договора"},
      {"key": "client_name",     "path": "client.full_name",          "label": "ФИО клиента"},
      {"key": "apartment_no",    "path": "apartment.number",          "label": "Номер квартиры"},
      ...
    ]

`key` is what the admin writes inside `{{…}}`. `path` is a dotted path
that the docgen service resolves against the contract tree at render
time (via Django's template `Variable` machinery). `label` is shown in
the placeholder picker UI.

Scope: global vs per-project
----------------------------

``project`` is a nullable FK to Project:

  * ``project=None``  — global template, usable for any contract.
  * ``project=X``     — project-scoped; only contracts under X see it in
                        the wizard.

Managing global templates (creating or editing a row with
``project=None``) requires the extra permission
``references.templates.manage_global`` on top of the generic
``references.templates.{create,edit}``. Enforced in the ViewSet.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ContractTemplate(BaseModel):
    title = models.CharField(_("Название"), max_length=255, db_index=True)
    body = models.TextField(
        _("HTML-шаблон"),
        blank=True,
        default="",
        help_text=_(
            "HTML, сохранённый Tiptap-редактором. Плейсхолдеры — {{key}}; "
            "соответствия key → path задаются ниже в placeholders."
        ),
    )
    placeholders = models.JSONField(
        _("Плейсхолдеры"),
        default=list,
        blank=True,
        help_text=_(
            "Список объектов [{\"key\": \"...\", \"path\": \"...\", \"label\": \"...\"}]. "
            "key используется в {{…}}, path — дотточный путь в контексте контракта."
        ),
    )
    project = models.ForeignKey(
        "objects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_templates",
        verbose_name=_("ЖК"),
        help_text=_("Пусто — глобальный шаблон, доступен любому контракту."),
    )
    author = models.ForeignKey(
        "users.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_templates",
        verbose_name=_("Автор"),
    )

    class Meta:
        verbose_name = _("Шаблон договора")
        verbose_name_plural = _("Шаблоны договоров")
        ordering = ["project_id", "-modified_at", "id"]

    def __str__(self) -> str:
        return self.title or f"Template #{self.pk}"

    @property
    def is_global(self) -> bool:
        return self.project_id is None
