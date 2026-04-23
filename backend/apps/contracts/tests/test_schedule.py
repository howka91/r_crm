"""Tests for the PaymentSchedule generation service."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta

from apps.contracts.models import PaymentSchedule
from apps.contracts.services.schedule import (
    ScheduleBuildError,
    generate_schedule,
)
from apps.contracts.tests.factories import ContractFactory, PaymentFactory, PaymentScheduleFactory
from apps.objects.tests.factories import (
    ApartmentFactory,
    CalculationFactory,
    PaymentInPercentFactory,
)


def _calc_for(contract, **overrides):
    """Create a Calculation attached to contract.apartment."""
    defaults = dict(
        apartment=contract.apartment,
        payment_percent=PaymentInPercentFactory(),
        installment_months=12,
        monthly_payment=Decimal("50000000.00"),
        initial_fee=Decimal("150000000.00"),
        new_total_price=Decimal("750000000.00"),
    )
    defaults.update(overrides)
    return CalculationFactory(**defaults)


@pytest.mark.django_db
class TestGenerateSchedule:
    def test_builds_initial_fee_plus_monthly_installments(self):
        contract = ContractFactory(date=date(2026, 5, 1))
        calc = _calc_for(contract, installment_months=3)
        contract.calculation = calc
        contract.save(update_fields=["calculation"])

        rows = generate_schedule(contract)
        assert len(rows) == 4  # 1 initial + 3 monthly

        # Row 0 is the down-payment on the contract date.
        assert rows[0].due_date == date(2026, 5, 1)
        assert rows[0].amount == Decimal("150000000.00")

        # Rows 1..3 step one calendar month each.
        assert rows[1].due_date == date(2026, 6, 1)
        assert rows[2].due_date == date(2026, 7, 1)
        assert rows[3].due_date == date(2026, 8, 1)
        for row in rows[1:]:
            assert row.amount == Decimal("50000000.00")

    def test_raises_without_calculation(self):
        contract = ContractFactory()
        contract.calculation = None
        contract.save(update_fields=["calculation"])
        with pytest.raises(ScheduleBuildError):
            generate_schedule(contract)

    def test_zero_initial_fee_skipped(self):
        contract = ContractFactory(date=date(2026, 1, 15))
        calc = _calc_for(
            contract, installment_months=2, initial_fee=Decimal("0.00"),
        )
        contract.calculation = calc
        contract.save(update_fields=["calculation"])

        rows = generate_schedule(contract)
        assert len(rows) == 2
        # First row is already the first monthly installment, one month after date.
        assert rows[0].due_date == date(2026, 2, 15)

    def test_regeneration_replaces_existing(self):
        contract = ContractFactory(date=date(2026, 1, 1))
        # Seed with unrelated schedule rows + a payment.
        ps = PaymentScheduleFactory(contract=contract)
        PaymentFactory(schedule=ps)
        assert PaymentSchedule.objects.filter(contract=contract).count() == 1

        calc = _calc_for(contract, installment_months=2)
        contract.calculation = calc
        contract.save(update_fields=["calculation"])

        rows = generate_schedule(contract)
        # Old rows wiped; 3 new rows (1 initial + 2 monthly).
        assert PaymentSchedule.objects.filter(contract=contract).count() == 3
        assert len(rows) == 3

    def test_zero_installment_months(self):
        contract = ContractFactory(date=date(2026, 1, 1))
        calc = _calc_for(contract, installment_months=0)
        contract.calculation = calc
        contract.save(update_fields=["calculation"])
        rows = generate_schedule(contract)
        # Only the initial fee row (if nonzero).
        assert len(rows) == 1
        assert rows[0].amount == Decimal("150000000.00")

    def test_end_of_month_rollover(self):
        """relativedelta should clip Jan 31 → Feb 28 / Feb 29 correctly."""
        contract = ContractFactory(date=date(2026, 1, 31))
        calc = _calc_for(
            contract, installment_months=2, initial_fee=Decimal("0.00"),
        )
        contract.calculation = calc
        contract.save(update_fields=["calculation"])
        rows = generate_schedule(contract)
        # relativedelta(months=1) from Jan 31, 2026 = Feb 28, 2026 (non-leap).
        expected_first = date(2026, 1, 31) + relativedelta(months=1)
        assert rows[0].due_date == expected_first
