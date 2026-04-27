"""Tests for apps.contracts.services.aggregates."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.contracts.models import Payment, PaymentSchedule
from apps.contracts.services import aggregates
from apps.contracts.tests.factories import (
    ContractFactory,
    PaymentFactory,
    PaymentScheduleFactory,
)
from apps.objects.tests.factories import CalculationFactory


@pytest.mark.django_db
class TestPaymentTypesUsed:
    def test_empty_when_no_payments(self):
        contract = ContractFactory()
        assert aggregates.payment_types_used(contract) == []

    def test_unique_and_in_fixed_order(self):
        contract = ContractFactory()
        s1 = PaymentScheduleFactory(contract=contract)
        # Insert in a different order than the canonical render order to
        # prove the function imposes its own ordering.
        PaymentFactory(schedule=s1, payment_type=Payment.Type.BARTER, comment="мебель")
        PaymentFactory(schedule=s1, payment_type=Payment.Type.CASH)
        # Duplicate cash to confirm dedup.
        PaymentFactory(schedule=s1, payment_type=Payment.Type.CASH)
        PaymentFactory(schedule=s1, payment_type=Payment.Type.BANK)

        result = aggregates.payment_types_used(contract)
        assert result == [Payment.Type.CASH, Payment.Type.BANK, Payment.Type.BARTER]

    def test_skips_inactive_payments(self):
        contract = ContractFactory()
        s1 = PaymentScheduleFactory(contract=contract)
        active = PaymentFactory(schedule=s1, payment_type=Payment.Type.CASH)
        inactive = PaymentFactory(schedule=s1, payment_type=Payment.Type.BANK)
        inactive.is_active = False
        inactive.save(update_fields=["is_active"])

        assert aggregates.payment_types_used(contract) == [Payment.Type.CASH]


@pytest.mark.django_db
class TestMonthlyDebt:
    def test_only_overdue_unpaid_lines_count(self):
        contract = ContractFactory()
        today = date.today()
        # Paid (status=PAID) — must NOT count.
        PaymentScheduleFactory(
            contract=contract,
            due_date=today - timedelta(days=20),
            amount=Decimal("100.00"), paid_amount=Decimal("100.00"),
            status=PaymentSchedule.Status.PAID,
        )
        # Future, pending — must NOT count (due_date > today).
        PaymentScheduleFactory(
            contract=contract,
            due_date=today + timedelta(days=10),
            amount=Decimal("200.00"), paid_amount=Decimal("0.00"),
            status=PaymentSchedule.Status.PENDING,
        )
        # Overdue with partial payment — must count its remainder (300 - 50 = 250).
        PaymentScheduleFactory(
            contract=contract,
            due_date=today - timedelta(days=5),
            amount=Decimal("300.00"), paid_amount=Decimal("50.00"),
            status=PaymentSchedule.Status.OVERDUE,
        )
        # Due exactly today, unpaid — must count.
        PaymentScheduleFactory(
            contract=contract,
            due_date=today,
            amount=Decimal("400.00"), paid_amount=Decimal("0.00"),
            status=PaymentSchedule.Status.PENDING,
        )

        assert aggregates.monthly_debt(contract) == Decimal("650.00")


@pytest.mark.django_db
class TestRemainingDebt:
    def test_sum_across_all_active_lines(self):
        contract = ContractFactory()
        today = date.today()
        PaymentScheduleFactory(
            contract=contract,
            due_date=today - timedelta(days=10),
            amount=Decimal("500.00"), paid_amount=Decimal("100.00"),
        )
        PaymentScheduleFactory(
            contract=contract,
            due_date=today + timedelta(days=10),
            amount=Decimal("700.00"), paid_amount=Decimal("0.00"),
        )
        # Soft-deleted line — must NOT count.
        soft = PaymentScheduleFactory(
            contract=contract,
            due_date=today - timedelta(days=30),
            amount=Decimal("999.00"), paid_amount=Decimal("0.00"),
        )
        soft.is_active = False
        soft.save(update_fields=["is_active"])

        # 400 + 700 = 1100; the soft-deleted 999 is excluded.
        assert aggregates.remaining_debt(contract) == Decimal("1100.00")


@pytest.mark.django_db
class TestMonthlyPayment:
    def test_returns_calculation_value(self):
        calc = CalculationFactory(monthly_payment=Decimal("12345.67"))
        contract = ContractFactory(calculation=calc)
        assert aggregates.monthly_payment(contract) == Decimal("12345.67")

    def test_returns_none_when_no_calculation(self):
        contract = ContractFactory(calculation=None)
        assert aggregates.monthly_payment(contract) is None
