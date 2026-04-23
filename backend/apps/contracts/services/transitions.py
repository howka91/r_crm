"""Contract.action state machine.

State graph (dots mark terminal state)::

    request → wait → approve → sign_in.
                 ↓       ↑
                edit ────┘

Transitions
-----------

* ``send_to_wait(contract, actor)`` — request → wait (or edit → wait).
  First-time transition also mints the contract number via
  :mod:`apps.contracts.services.numbering`. Idempotent on re-submission from
  ``edit``: does not re-mint.

* ``approve(contract, actor)`` — wait → approve.

* ``sign(contract, actor)`` — approve → sign_in and flips ``is_signed=True``.
  Terminal; after sign-in only the payments service (Phase 5.2) and
  cancellations (Phase 5.3) touch the contract.

* ``request_edit(contract, actor, reason)`` — wait → edit. Snapshots the
  current ``document`` into ``old`` with a timestamp so the previous version
  can be recovered if the edit is rejected.

Every transition runs inside its own ``transaction.atomic()`` with
``select_for_update()`` on the contract row to serialise concurrent
transitions. Non-callers raising ``TransitionError`` see the current action
in the payload.

Audit logging uses the middleware-written :class:`core.AuditLog` entry for
the HTTP request that triggered the transition; this service does **not**
write its own AuditLog row. Domain-specific history is kept in
``Contract.old`` (document snapshots) and ``Contract.action`` itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from django.db import transaction

from apps.contracts.models import Contract
from apps.contracts.services.numbering import mint_contract_number
from apps.users.models import Staff

# --- Allowed transitions table ----------------------------------------------

_ALLOWED: dict[str, set[str]] = {
    Contract.Action.REQUEST: {Contract.Action.WAIT},
    Contract.Action.WAIT: {Contract.Action.APPROVE, Contract.Action.EDIT},
    Contract.Action.APPROVE: {Contract.Action.SIGN_IN},
    Contract.Action.EDIT: {Contract.Action.WAIT},
    Contract.Action.SIGN_IN: set(),  # terminal
}


class TransitionError(Exception):
    """Raised when a caller requests an illegal action transition."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Переход {current!r} → {target!r} запрещён стейт-машиной."
        )
        self.current = current
        self.target = target


@dataclass(frozen=True)
class TransitionResult:
    contract: Contract
    previous_action: str
    new_action: str
    minted_number: str | None = None  # only set on the first send_to_wait


def _guard(contract: Contract, target: str) -> None:
    if target not in _ALLOWED[contract.action]:
        raise TransitionError(contract.action, target)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def send_to_wait(contract: Contract, actor: Staff) -> TransitionResult:
    """Move the contract to `wait`. Mints a contract number the first time.

    Re-submission from ``edit`` keeps the existing ``contract_number``.
    """
    target = Contract.Action.WAIT
    with transaction.atomic():
        locked = Contract.objects.select_for_update().get(pk=contract.pk)
        _guard(locked, target)
        previous = locked.action
        minted: str | None = None
        if not locked.contract_number:
            minted = mint_contract_number(locked.project)
            locked.contract_number = minted
        locked.action = target
        update_fields = ["action", "contract_number", "modified_at"]
        locked.save(update_fields=update_fields)
        return TransitionResult(locked, previous, target, minted)


def approve(contract: Contract, actor: Staff) -> TransitionResult:
    target = Contract.Action.APPROVE
    with transaction.atomic():
        locked = Contract.objects.select_for_update().get(pk=contract.pk)
        _guard(locked, target)
        previous = locked.action
        locked.action = target
        locked.save(update_fields=["action", "modified_at"])
        return TransitionResult(locked, previous, target)


def sign(contract: Contract, actor: Staff) -> TransitionResult:
    """Final transition: approve → sign_in, is_signed=True."""
    target = Contract.Action.SIGN_IN
    with transaction.atomic():
        locked = Contract.objects.select_for_update().get(pk=contract.pk)
        _guard(locked, target)
        previous = locked.action
        locked.action = target
        locked.is_signed = True
        locked.save(update_fields=["action", "is_signed", "modified_at"])
        return TransitionResult(locked, previous, target)


def request_edit(
    contract: Contract, actor: Staff, reason: str = "",
) -> TransitionResult:
    """wait → edit. Snapshot the current `document` into `old`."""
    target = Contract.Action.EDIT
    with transaction.atomic():
        locked = Contract.objects.select_for_update().get(pk=contract.pk)
        _guard(locked, target)
        previous = locked.action
        # Capture the pre-edit document for rollback / audit.
        snapshot = {
            "snapshot_at": _now_iso(),
            "actor_id": str(actor.id) if actor else None,
            "reason": reason,
            "document": locked.document or {},
        }
        old_list = list(locked.old or [])
        old_list.append(snapshot)
        locked.old = old_list
        locked.action = target
        locked.save(update_fields=["action", "old", "modified_at"])
        return TransitionResult(locked, previous, target)
