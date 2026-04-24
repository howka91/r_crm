"""Render a contract from its template to a PDF attached to ``Contract.file``.

Two parallel pipelines — selected by ``ContractTemplate.source``:

**html** (Tiptap-authored):

    body (HTML) → placeholder substitution via `template.placeholders`
                → QR data-URI injected
                → WeasyPrint → PDF bytes

Everything runs in-process, no subprocess.

**docx** (Word-authored by a lawyer):

    file (.docx) → docxtpl renders Jinja2 tags ({{ contract.number }})
                → intermediate .docx written to tempdir
                → `soffice --headless --convert-to pdf` → PDF bytes

Both paths share the same `build_context(contract)` tree, so the same
dotted paths (`client.full_name`, `apartment.number`, `__qr__`) work in
either authoring flow.

The service does **not** change `action` / `is_signed`. Workflow is the
caller's responsibility; calling docgen on any status is allowed, but
the ViewSet gates regeneration on signed contracts the same way it
gates schedule regeneration.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any

from django.core.files.base import ContentFile
from django.template import Context, Variable, VariableDoesNotExist
from django.template.defaultfilters import stringfilter  # noqa: F401 — load defaultfilters
from django.utils.html import escape

from apps.contracts.models import Contract, ContractTemplate
from apps.contracts.services.qr import make_qr_data_uri, make_qr_png
from apps.contracts.services.snapshot import build_context

# --- Placeholder substitution -------------------------------------------

# Matches `{{key}}` or `{{ key }}` — whitespace-tolerant, simple identifier.
# We deliberately do NOT support `{{ client.full_name }}` directly in the
# body: callers must declare every placeholder in `template.placeholders`
# with a `key` and its `path`. This keeps the template surface controlled
# and typo-proof.
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class DocgenError(Exception):
    """Base class for docgen failures that should surface as 400/409."""


class TemplateNotSet(DocgenError):
    """Contract.template is None — menedzher must pick one first."""


class UnknownPlaceholder(DocgenError):
    """Template body references a `{{key}}` not declared in placeholders."""

    def __init__(self, unknown: list[str]) -> None:
        super().__init__(
            f"Шаблон использует необъявленные плейсхолдеры: {unknown[:10]}"
            + (" …" if len(unknown) > 10 else "")
        )
        self.unknown = unknown


class DocxRenderFailed(DocgenError):
    """LibreOffice failed to convert the filled .docx to PDF."""


@dataclass(frozen=True)
class DocgenResult:
    contract: Contract
    pdf_path: str          # value of Contract.file.name after save
    pdf_size: int
    filled: dict[str, Any]  # snapshot of resolved placeholder values


def _resolve_path(path: str, context: Context) -> Any:
    """Walk a dotted path via Django's template Variable machinery.

    Missing links resolve to empty string — matches what WeasyPrint
    would render for an empty `{{x}}` anyway, and avoids surprising 500s
    on partially-filled contracts (no calculation yet, no signer, etc.).
    """
    try:
        return Variable(path).resolve(context)
    except (VariableDoesNotExist, AttributeError, KeyError, TypeError):
        return ""


def _build_placeholder_values(
    template: ContractTemplate, ctx: Context,
) -> dict[str, str]:
    """Turn the admin-declared `placeholders` list into a resolved map.

    Output keys are placeholder *keys* (what the admin writes in {{…}}).
    Values are stringified + HTML-escaped so injection via ``.replace``
    is safe.
    """
    resolved: dict[str, str] = {}
    for entry in template.placeholders or []:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        path = entry.get("path")
        if not key or not path:
            continue
        raw = _resolve_path(str(path), ctx)
        # None / missing → empty string to keep layout intact.
        resolved[str(key)] = "" if raw is None else escape(str(raw))
    return resolved


def _substitute(body: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Replace every `{{key}}` in `body` with its value.

    Returns the filled HTML plus a list of unknown keys (those present
    in the body but missing from `values`). Unknown keys are left as
    literal `{{key}}` in the output — the caller decides whether to
    fail or soldier on.
    """
    unknown: list[str] = []

    def _repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in values:
            return values[key]
        unknown.append(key)
        return match.group(0)

    return _PLACEHOLDER_RE.sub(_repl, body), unknown


# Base CSS injected before the template body so every template renders
# consistently — regardless of what the admin typed. Keeps page-break
# semantics in one place (editor + PDF must agree) and caps images so a
# giant logo can't push layout off the page.
_BASE_CSS = """
<style>
  @page { size: A4; margin: 18mm 15mm; }
  body { font-family: "DejaVu Sans", "Noto Sans", sans-serif; font-size: 11pt; line-height: 1.45; }
  .page-break {
    break-before: page;
    page-break-before: always;
    clear: both;
    height: 0;
    border: 0;
    margin: 0;
    padding: 0;
  }
  img { max-width: 100%; }
  img[data-align="left"] {
    float: left;
    margin: 0 14px 6px 0;
    max-width: 50%;
  }
  img[data-align="right"] {
    float: right;
    margin: 0 0 6px 14px;
    max-width: 50%;
  }
  img[data-align="center"] {
    display: block;
    margin: 4px auto;
    float: none;
  }
  .template-logo, img.logo { max-height: 110px; }
  table { border-collapse: collapse; }
</style>
"""


def _render_pdf(html: str) -> bytes:
    """Run HTML through WeasyPrint, return PDF bytes.

    Imported lazily — WeasyPrint pulls a chain of native libraries
    (pango, cairo, gdk-pixbuf) that are expensive to import at module
    load time, especially in test environments that never actually
    render.
    """
    # Local import on purpose — see docstring.
    from weasyprint import HTML  # type: ignore[import-not-found]

    # Prepend the shared base stylesheet so .page-break / image sizing
    # work in every template without the admin adding boilerplate CSS.
    return HTML(string=_BASE_CSS + html).write_pdf()


# --- Public entry point -------------------------------------------------


def generate_pdf(
    contract: Contract, *, strict: bool = True,
) -> DocgenResult:
    """Render `contract` to PDF and attach it to ``contract.file``.

    Dispatches on `contract.template.source`: HTML-authored templates go
    through WeasyPrint; DOCX-authored ones through docxtpl+LibreOffice.

    Parameters
    ----------
    contract:
        A Contract with ``template`` set. For source=html the template
        must have ``body``; for source=docx — ``file``.
    strict:
        HTML path only — raise ``UnknownPlaceholder`` when the body
        references `{{key}}` that isn't declared in
        ``template.placeholders``. Set False to let unknown keys pass
        through as literal text (useful for previewing). Ignored for
        docx templates (Jinja2 fails loudly on its own).

    Returns
    -------
    DocgenResult — the saved file path, its byte size, and the dict of
    resolved placeholder values (also persisted into
    ``contract.document`` for reproducibility).
    """
    template = contract.template
    if template is None:
        raise TemplateNotSet(
            "Нельзя сгенерировать PDF: у договора не выбран шаблон."
        )

    if template.source == ContractTemplate.Source.DOCX:
        return _generate_pdf_from_docx(contract, template)
    return _generate_pdf_from_html(contract, template, strict=strict)


def _generate_pdf_from_html(
    contract: Contract, template: ContractTemplate, *, strict: bool,
) -> DocgenResult:
    ctx = Context(build_context(contract))
    values = _build_placeholder_values(template, ctx)

    # Standard extras that aren't in admin's map but are always useful.
    values.setdefault("__qr__", make_qr_data_uri(contract.contract_number or f"id:{contract.pk}"))

    filled_html, unknown = _substitute(template.body or "", values)
    if unknown and strict:
        raise UnknownPlaceholder(sorted(set(unknown)))

    pdf_bytes = _render_pdf(filled_html)

    # Snapshot the resolved values so `Contract.document` records exactly
    # what was printed. Useful for the edit workflow's `old[]` log.
    contract.document = {
        "template_id": template.id,
        "template_title": template.title,
        "source": ContractTemplate.Source.HTML,
        "values": values,
    }
    filename = _pdf_filename(contract)
    contract.file.save(filename, ContentFile(pdf_bytes), save=False)
    contract.save(update_fields=["file", "document", "modified_at"])

    return DocgenResult(
        contract=contract,
        pdf_path=contract.file.name,
        pdf_size=len(pdf_bytes),
        filled=values,
    )


# --- DOCX path -----------------------------------------------------------


def _generate_pdf_from_docx(
    contract: Contract, template: ContractTemplate,
) -> DocgenResult:
    """Fill a lawyer-authored .docx with `docxtpl` and convert it to PDF
    via LibreOffice in headless mode.

    The context passed to docxtpl is the same tree built by
    `build_context(contract)`, plus a `qr` InlineImage so templates can
    embed a scannable QR via `{{ qr }}` tags.
    """
    if not template.file:
        raise TemplateNotSet(
            "У docx-шаблона не загружен файл — сначала приложите .docx.",
        )

    # Lazy imports — docxtpl pulls python-docx; soffice is a subprocess.
    from docxtpl import DocxTemplate, InlineImage  # type: ignore[import-not-found]
    from docx.shared import Mm  # type: ignore[import-not-found]

    # 1. Build the rendering context.
    raw_ctx = build_context(contract)

    # 2. Attach a QR InlineImage so `{{ qr }}` inside the .docx works
    #    out of the box. InlineImage needs the DocxTemplate instance, so
    #    we wire it after opening the file below.
    qr_png = make_qr_png(contract.contract_number or f"id:{contract.pk}")

    tmpdir = tempfile.mkdtemp(prefix="docgen-")
    try:
        # docxtpl needs a real file-system path for the source template.
        # Open the FieldFile explicitly with `with` so the underlying
        # storage handle closes right after we've copied bytes out —
        # otherwise tests (and long-lived workers) leak file handles.
        src_path = os.path.join(tmpdir, "template.docx")
        with template.file.open("rb") as src, open(src_path, "wb") as dst:
            for chunk in iter(lambda: src.read(65536), b""):
                dst.write(chunk)

        doc = DocxTemplate(src_path)

        qr_path = os.path.join(tmpdir, "qr.png")
        with open(qr_path, "wb") as f:
            f.write(qr_png)
        raw_ctx["qr"] = InlineImage(doc, qr_path, width=Mm(25))

        doc.render(raw_ctx)
        filled_docx = os.path.join(tmpdir, "filled.docx")
        doc.save(filled_docx)

        # 3. docx → pdf via LibreOffice headless. Each invocation spins
        #    up its own user profile so parallel requests don't clash
        #    on ~/.config/libreoffice/ file locks.
        profile_dir = os.path.join(tmpdir, f"lo-{uuid.uuid4().hex}")
        pdf_bytes = _docx_to_pdf(filled_docx, profile_dir=profile_dir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    contract.document = {
        "template_id": template.id,
        "template_title": template.title,
        "source": ContractTemplate.Source.DOCX,
        # The .docx body is opaque binary — record the list of tags the
        # validator found when the template was uploaded instead.
        "values": {
            "tags": [p.get("key") for p in (template.placeholders or []) if p.get("key")],
        },
    }
    filename = _pdf_filename(contract)
    contract.file.save(filename, ContentFile(pdf_bytes), save=False)
    contract.save(update_fields=["file", "document", "modified_at"])

    return DocgenResult(
        contract=contract,
        pdf_path=contract.file.name,
        pdf_size=len(pdf_bytes),
        filled={"source": "docx"},
    )


def _docx_to_pdf(src_docx: str, *, profile_dir: str) -> bytes:
    """Shell out to LibreOffice headless, return PDF bytes.

    `--user-profile=...` isolates each conversion so concurrent requests
    from different workers don't fight over the same ~/.config dir and
    hang forever (classic LO footgun).
    """
    out_dir = os.path.dirname(src_docx)
    cmd = [
        "soffice",
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        f"-env:UserInstallation=file://{profile_dir}",
        "--convert-to", "pdf",
        "--outdir", out_dir,
        src_docx,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=90, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise DocxRenderFailed(
            f"LibreOffice не запустился: {e!s}",
        ) from e

    if result.returncode != 0:
        raise DocxRenderFailed(
            "LibreOffice завершился с ошибкой:\n"
            + (result.stderr.decode("utf-8", errors="replace")[:800] or "empty stderr"),
        )

    # Output filename is the input base with .pdf extension.
    pdf_path = os.path.splitext(src_docx)[0] + ".pdf"
    if not os.path.exists(pdf_path):
        raise DocxRenderFailed(
            f"LibreOffice не создал PDF — ожидался {pdf_path}.",
        )
    with open(pdf_path, "rb") as f:
        return f.read()


def _pdf_filename(contract: Contract) -> str:
    """Predictable file name — contract_number or id, plus a short hash of
    modified_at so overwrites don't silently pile up in MEDIA_ROOT."""
    base = contract.contract_number or f"contract-{contract.pk}"
    # Replace characters that are problematic in filenames / URLs.
    base = re.sub(r"[^\w\-]+", "_", base)
    return f"{base}.pdf"
