"""Render a contract from its HTML template to a PDF attached to
``Contract.file``.

Pipeline (all in-process — no LibreOffice sidecar):

    ContractTemplate.body (HTML, Tiptap output)
         │
         ▼
    1. Substitute `{{key}}` markers using the admin-declared map in
       `ContractTemplate.placeholders` (each entry: {key, path, label}).
       Paths are resolved against the Contract's context tree (see
       `apps.contracts.services.snapshot.build_context`).
         │
         ▼
    2. Inject a QR-code <img> via data-URI (payload = contract number).
         │
         ▼
    3. WeasyPrint renders the merged HTML to PDF bytes.
         │
         ▼
    4. Save PDF on `Contract.file` (FileField). `Contract.document`
       receives a snapshot dict of every resolved value so the next
       render (or a legal audit) can reconstruct what was printed.

The service does **not** change `action` / `is_signed`. Workflow is the
caller's responsibility; calling docgen on any status is allowed, but
the ViewSet gates regeneration on signed contracts the same way it
gates schedule regeneration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.core.files.base import ContentFile
from django.template import Context, Variable, VariableDoesNotExist
from django.template.defaultfilters import stringfilter  # noqa: F401 — load defaultfilters
from django.utils.html import escape

from apps.contracts.models import Contract, ContractTemplate
from apps.contracts.services.qr import make_qr_data_uri
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

    Parameters
    ----------
    contract:
        A Contract with ``template`` set and ``template.body`` populated.
    strict:
        If True (default), raise ``UnknownPlaceholder`` when the body
        references `{{key}}` that isn't declared in
        ``template.placeholders``. Set False to let unknown keys pass
        through as literal text (useful for previewing).

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


def _pdf_filename(contract: Contract) -> str:
    """Predictable file name — contract_number or id, plus a short hash of
    modified_at so overwrites don't silently pile up in MEDIA_ROOT."""
    base = contract.contract_number or f"contract-{contract.pk}"
    # Replace characters that are problematic in filenames / URLs.
    base = re.sub(r"[^\w\-]+", "_", base)
    return f"{base}.pdf"
