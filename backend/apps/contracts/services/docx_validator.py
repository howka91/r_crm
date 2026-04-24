"""Validate a lawyer-authored .docx contract template.

Extracts all Jinja2 tags (`{{ contract.foo }}`, `{% for x in y %}`) the
uploaded file will try to render and sorts them into:

* **known** — root matches the context built by `build_context()` (see
  `KNOWN_ROOTS` below). Safe to render, shown as green chips in the UI.
* **unknown** — root that `build_context` doesn't provide. Rendering
  would crash; the UI shows them as red and refuses to save unless the
  author fixes them.

The validator only looks at the root of each dotted path — it can't
verify that `client.foo.bar` actually exists without a real contract,
and the `docxtpl` render already raises cleanly if an attribute is
missing. The point here is to catch typos *before* the template is
saved, while the author still remembers what they meant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO


# Top-level keys populated by `apps.contracts.services.snapshot.build_context`.
# Keep in sync with `build_context` — adding a new root there should be
# mirrored here so templates referencing it pass validation.
KNOWN_ROOTS: frozenset[str] = frozenset({
    "contract",
    "apartment",
    "project",
    "developer",
    "calculation",
    "signer",
    "client",
    "now",
    "today",
    # Extras we inject at render time for convenience:
    "qr",        # InlineImage, usable as `{{ qr }}`
})


@dataclass
class DocxValidationResult:
    known: list[str] = field(default_factory=list)   # tags with a known root, sorted
    unknown: list[str] = field(default_factory=list)  # tags with an unknown root
    all_tags: list[str] = field(default_factory=list)  # every tag docxtpl found

    def as_dict(self) -> dict:
        return {
            "known": self.known,
            "unknown": self.unknown,
            "all": self.all_tags,
            "is_valid": not self.unknown,
        }


def extract_tags(docx_source: str | bytes | IO) -> list[str]:
    """Pull every Jinja2 variable the template references from a .docx
    file. Accepts a path, bytes-like, or a seekable file-like.

    A .docx is a zip; the main text lives in `word/document.xml` (plus
    headers/footers in `word/header*.xml` / `word/footer*.xml`). We grep
    those XML blobs directly with `_tags_from_xml_text` — faster and
    more robust than docxtpl's `get_xml()`, which requires rendering
    the template first (and we don't have a context yet).
    """
    import zipfile

    with zipfile.ZipFile(docx_source) as zf:
        names = [
            n for n in zf.namelist()
            if n == "word/document.xml"
            or n.startswith("word/header") and n.endswith(".xml")
            or n.startswith("word/footer") and n.endswith(".xml")
        ]
        raw = "\n".join(zf.read(n).decode("utf-8", errors="replace") for n in names)
    return _tags_from_xml_text(raw)


def _tags_from_xml_text(xml_text: str) -> list[str]:
    """Collect Jinja2 variable *expressions* from a block of DOCX XML.

    Rules applied here after a week of fighting edge cases:

    * `{{ expr }}` — keep `expr` (trimmed).
    * `{% for x in y %}` — keep `y` as the iterable expression, plus
      add `x` as a loop-local variable so we don't flag it as unknown.
    * `{% if cond %}` — keep `cond`.
    * `{% set a = b %}` — keep `b`; `a` is loop-local.
    * `{% endfor %}` / `{% endif %}` / `{% else %}` / comments — ignored.
    * Filters (`{{ x | upper }}`) — strip the filter suffix.
    * Word sometimes splits a single `{{ x }}` across multiple <w:r> runs.
      docxtpl joins them back when rendering, but the raw XML may still
      have them separate. For validation we strip XML tags first, then
      scan the resulting plain text.
    """
    import re

    # Drop every XML tag — whitespace between tags may survive, which
    # is fine, because Jinja2 tolerates whitespace inside expressions.
    text = re.sub(r"<[^>]*>", "", xml_text)
    # Word's smart quotes can land inside templates; normalise a couple
    # of common offenders so `{{ client.full_name }}` typed in Word
    # still parses.
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    tags: list[str] = []
    loop_vars: set[str] = set()

    # 1. {% ... %} statements — grab the iterable / condition expression.
    for stmt in re.findall(r"\{%\s*(.+?)\s*%\}", text, re.DOTALL):
        head, _, rest = stmt.strip().partition(" ")
        head = head.lower()
        if head in {"endfor", "endif", "else", "elif", "endblock", "#"}:
            continue
        if head == "for":
            # "for a, b in items" or "for x in items" — capture loop var(s)
            # and the iterable.
            m = re.match(
                r"([\w,\s]+?)\s+in\s+(.+)", rest, re.DOTALL,
            )
            if m:
                for v in m.group(1).split(","):
                    v = v.strip()
                    if v:
                        loop_vars.add(v)
                tags.append(m.group(2).strip())
        elif head == "if":
            tags.append(rest.strip())
        elif head == "set":
            # "set a = b" — right-hand side may be a dotted path.
            m = re.match(r"(\w+)\s*=\s*(.+)", rest, re.DOTALL)
            if m:
                loop_vars.add(m.group(1).strip())
                tags.append(m.group(2).strip())

    # 2. {{ ... }} expressions.
    for expr in re.findall(r"\{\{\s*(.+?)\s*\}\}", text, re.DOTALL):
        expr = expr.strip()
        # Strip filters, we only care about the variable side.
        if "|" in expr:
            expr = expr.split("|", 1)[0].strip()
        tags.append(expr)

    # Dedup while preserving first-seen order — authors may care about
    # where the first mention was when fixing typos.
    seen: set[str] = set()
    ordered: list[str] = []
    for t in tags:
        # Simple expressions only — skip anything that looks like a
        # function call, arithmetic, or string literal.
        if not t or t.startswith(("'", '"')):
            continue
        if any(c in t for c in "()+-*/!="):
            continue
        # Collapse whitespace noise from Word.
        clean = " ".join(t.split())
        if clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)

    # Drop loop-local vars from the reported list — they're not tags
    # the author means to fill from the contract context.
    return [t for t in ordered if t.split(".")[0] not in loop_vars]


def validate(docx_source: str | bytes | IO) -> DocxValidationResult:
    """Extract tags from the template and split into known / unknown."""
    tags = extract_tags(docx_source)
    known: list[str] = []
    unknown: list[str] = []
    for tag in tags:
        root = tag.split(".")[0].strip()
        if root in KNOWN_ROOTS:
            known.append(tag)
        else:
            unknown.append(tag)
    return DocxValidationResult(
        known=sorted(set(known)),
        unknown=sorted(set(unknown)),
        all_tags=sorted(set(tags)),
    )
