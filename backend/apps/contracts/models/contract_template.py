"""ContractTemplate — template for PDF contract generation.

Two parallel authoring flows, both producing PDF:

  * **HTML** (Phase 5.3 default) — ``source="html"``. Admin edits via the
    Tiptap WYSIWYG editor; ``body`` holds the HTML; render path is
    WeasyPrint (in-process, no subprocess).
  * **DOCX** — ``source="docx"``. Lawyer authors the contract in MS Word
    with Jinja-style ``{{ dotted.path }}`` tags, uploads the file; render
    path is `docxtpl` (fill tags) → `soffice --headless --convert-to pdf`
    (LibreOffice, bundled in the backend image).

Each template picks exactly one flow — no cross-conversion. The wizard
UI shows both options side by side so managers without Word skills can
still produce templates through the HTML editor.

Placeholders
------------

* HTML flow: body uses ``{{key}}``; valid keys declared per-template in
  ``placeholders`` as ``[{key, path, label}]``. Strict — unknown keys
  are rejected at render time.
* DOCX flow: body uses Jinja2 ``{{ contract.contract_number }}`` —
  direct dotted paths resolved against the same ``build_context`` tree.
  ``placeholders`` in this mode stores the *catalog* of tags found in
  the uploaded file (populated by the validator), so the picker UI can
  show what the template already uses.

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
    class Source(models.TextChoices):
        HTML = "html", _("HTML (встроенный редактор)")
        DOCX = "docx", _("DOCX (Word-файл)")

    title = models.CharField(_("Название"), max_length=255, db_index=True)
    source = models.CharField(
        _("Источник"),
        max_length=8,
        choices=Source.choices,
        default=Source.HTML,
        db_index=True,
        help_text=_(
            "html — шаблон редактируется в Tiptap в браузере; "
            "docx — юрист загружает .docx, из которого рендерится PDF."
        ),
    )
    body = models.TextField(
        _("HTML-шаблон"),
        blank=True,
        default="",
        help_text=_(
            "HTML, сохранённый Tiptap-редактором. Используется только "
            "для source=html. Плейсхолдеры — {{key}}."
        ),
    )
    # Authored .docx file for source=docx flow. Blank for HTML templates.
    file = models.FileField(
        _("DOCX-файл"),
        upload_to="contract_templates/docx/%Y/%m/",
        null=True,
        blank=True,
        help_text=_(
            "Word-файл с тегами Jinja2 вида {{ contract.contract_number }}. "
            "Рендерится в PDF через docxtpl + LibreOffice."
        ),
    )
    placeholders = models.JSONField(
        _("Плейсхолдеры"),
        default=list,
        blank=True,
        help_text=_(
            "Для html-шаблонов — список [{\"key\": \"...\", \"path\": \"...\", "
            "\"label\": \"...\"}]. Для docx — автоматически собранный список "
            "тегов, найденных в файле (для отображения в каталоге плейсхолдеров)."
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
