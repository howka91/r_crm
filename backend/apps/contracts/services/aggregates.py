"""Read-only aggregate helpers for Contract list/detail views.

Pure functions. No side effects, no signals — invoked from serializers when
the list/detail endpoint renders. Each call assumes ContractViewSet has
prefetched ``schedules`` and ``schedules__payments``; without that prefetch
they still work correctness-wise but will run extra queries.
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from apps.contracts.models import Contract, Payment, PaymentSchedule


# Fixed render order for the payment-types-used badge so the UI always shows
# the same chip layout regardless of which type was first encountered.
_PAYMENT_TYPE_ORDER: tuple[str, ...] = (
    Payment.Type.CASH,
    Payment.Type.BANK,
    Payment.Type.BARTER,
)


def payment_types_used(contract: Contract) -> list[str]:
    """Distinct payment types across all active payments of the contract."""
    seen: set[str] = set()
    for schedule in contract.schedules.all():
        for payment in schedule.payments.all():
            if payment.is_active:
                seen.add(payment.payment_type)
    return [t for t in _PAYMENT_TYPE_ORDER if t in seen]


def monthly_debt(contract: Contract) -> Decimal:
    """Sum of overdue debt: schedules with due_date <= today and not paid."""
    today = date_type.today()
    total = Decimal("0.00")
    for schedule in contract.schedules.all():
        if not schedule.is_active:
            continue
        if schedule.status == PaymentSchedule.Status.PAID:
            continue
        if schedule.due_date > today:
            continue
        total += schedule.debt
    return total


def remaining_debt(contract: Contract) -> Decimal:
    """Sum of debt across every active schedule line of the contract."""
    total = Decimal("0.00")
    for schedule in contract.schedules.all():
        if schedule.is_active:
            total += schedule.debt
    return total


def monthly_payment(contract: Contract) -> Decimal | None:
    """Recurring installment from the linked Calculation, if any."""
    calc = contract.calculation
    return calc.monthly_payment if calc else None
