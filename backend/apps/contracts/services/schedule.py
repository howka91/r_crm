"""Deterministic PaymentSchedule generation from a Contract's Calculation.

Rules
-----

* Row #1 — the **initial fee** (from ``calculation.initial_fee``) is due on
  the contract's ``date``. If the initial fee is zero, the row is skipped.

* Rows #2..N — each equal to ``calculation.monthly_payment``, stepping one
  calendar month forward from ``contract.date`` (using ``relativedelta``,
  so end-of-month dates stay sensible: Jan 31 → Feb 28 → Mar 31).

* Regeneration replaces any existing schedule. Payments attached via the
  ``schedule`` FK are ``CASCADE``, so they go with it. (The service
  therefore treats regeneration as destructive — callers should only
  regenerate on draft contracts, before money has actually moved.)

The service does **not** touch the contract itself (no new fields, no
`action` flip) — it's purely a derivation step. Wiring to the workflow is
left to the ViewSet: typically the manager runs it after the contract is
approved but before signing, so the signatory PDF quotes the exact dates.
"""
from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import transaction

from apps.contracts.models import Contract, PaymentSchedule


class ScheduleBuildError(Exception):
    """Raised when a schedule can't be derived from the contract's state."""


def generate_schedule(contract: Contract) -> list[PaymentSchedule]:
    """Rebuild the payment schedule for ``contract`` from its ``calculation``.

    Returns the newly-created schedule rows in due-date order. Raises
    ``ScheduleBuildError`` if the contract has no ``calculation`` attached —
    that's the only source of installment_months / monthly_payment, so there
    isn't enough information to build anything sane.

    Existing schedule rows (and their cascading payments) are removed first
    so the caller can re-run idempotently. Signed contracts are therefore
    the caller's responsibility: blocking regeneration on signed contracts
    belongs in the ViewSet, not here.
    """
    calc = contract.calculation
    if calc is None:
        raise ScheduleBuildError(
            "Contract has no calculation attached — cannot derive schedule."
        )

    with transaction.atomic():
        # Wipe any prior schedule. CASCADE removes attached Payment rows.
        # Use all_objects to bypass SoftDeleteManager — we want the DB row
        # gone, not just flagged inactive.
        PaymentSchedule.all_objects.filter(contract=contract).delete()

        rows: list[PaymentSchedule] = []

        # Down-payment line (optional — some plans start with equal installments).
        if calc.initial_fee and calc.initial_fee > Decimal("0.00"):
            rows.append(
                PaymentSchedule.objects.create(
                    contract=contract,
                    due_date=contract.date,
                    amount=calc.initial_fee,
                )
            )

        # Monthly installments.
        monthly = calc.monthly_payment or Decimal("0.00")
        months = int(calc.installment_months or 0)
        for i in range(months):
            if monthly <= 0:
                break
            due = contract.date + relativedelta(months=i + 1)
            rows.append(
                PaymentSchedule.objects.create(
                    contract=contract,
                    due_date=due,
                    amount=monthly,
                )
            )

        return rows
