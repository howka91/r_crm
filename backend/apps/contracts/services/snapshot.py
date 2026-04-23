"""Build the placeholder-resolution context for a Contract.

The docgen service passes a dict of "roots" to the template engine; the
admin's ``placeholders[]`` entries specify dotted paths relative to these
roots (e.g. ``"client.full_name"``, ``"apartment.floor.section.building.number"``).

Roots exposed:

  * ``contract``    — the Contract row being rendered.
  * ``apartment``   — ``contract.apartment`` (unit being sold).
  * ``project``     — ``contract.project`` (ЖК).
  * ``developer``   — ``contract.project.developer`` (застройщик).
  * ``calculation`` — ``contract.calculation`` if attached, else None.
  * ``signer``      — ``contract.signer`` (ClientContact).
  * ``client``      — ``signer.client`` (the actual Client entity).
  * ``now``         — current datetime for `{{now|date:…}}` usage.
  * ``today``       — today's date.

The roots are raw model instances; Django's template engine resolves
attribute chains against them. Any missing intermediate (e.g. contract
without a calculation, or signer without a client) resolves to the empty
string at render time rather than raising.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from apps.contracts.models import Contract


def build_context(contract: Contract) -> dict[str, Any]:
    """Assemble the dict used as docgen template context."""
    apartment = contract.apartment
    project = contract.project
    developer = getattr(project, "developer", None) if project else None
    calculation = contract.calculation
    signer = contract.signer
    client = getattr(signer, "client", None) if signer else None

    return {
        "contract": contract,
        "apartment": apartment,
        "project": project,
        "developer": developer,
        "calculation": calculation,
        "signer": signer,
        "client": client,
        "now": datetime.now(timezone.utc),
        "today": date.today(),
    }
