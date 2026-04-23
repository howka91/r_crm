"""Atomic per-project contract-number minting.

Legacy `clients_contract.contract_number` was entered by hand, which caused
double-numbering under concurrent entry. The new scheme makes the number a
side-effect of sending a draft to approval:

* draft has `contract_number = ""`
* on `send_to_wait` transition, `mint_contract_number(project)` is called
  inside the same `transaction.atomic()` as the state change.

The counter lives on `Project.contract_number_index` (bumped under
`select_for_update` so two concurrent drafts can't collide) and the format
is `{prefix}-{index:05d}` — the prefix is per-project (e.g. `ЯМ` → `ЯМ-00001`).
When prefix is empty, we emit the plain zero-padded number.
"""
from __future__ import annotations

from django.db import transaction

from apps.objects.models import Project


def mint_contract_number(project: Project) -> str:
    """Return the next contract number for `project` and persist the counter.

    Must be called inside or alongside a transaction that wraps the caller's
    state change — otherwise the counter can drift from reality on crash.

    Pattern::

        with transaction.atomic():
            number = mint_contract_number(project)
            contract.contract_number = number
            contract.action = Contract.Action.WAIT
            contract.save(update_fields=["contract_number", "action"])
    """
    with transaction.atomic():
        # select_for_update locks the Project row for the duration of the
        # transaction; a second minter with the same project waits.
        locked = Project.objects.select_for_update().get(pk=project.pk)
        locked.contract_number_index += 1
        locked.save(update_fields=["contract_number_index"])
        idx = locked.contract_number_index
        prefix = (locked.contract_number_prefix or "").strip()
        return f"{prefix}-{idx:05d}" if prefix else f"{idx:05d}"
