"""factory-boy factories for the contracts app."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.clients.tests.factories import ClientContactFactory
from apps.contracts.models import (
    Contract,
    ContractTemplate,
    Payment,
    PaymentSchedule,
)
from apps.objects.tests.factories import ApartmentFactory, ProjectFactory


class ContractFactory(DjangoModelFactory):
    """Creates a contract with matching apartment↔project invariant.

    `apartment`'s Project comes from `project` — otherwise the apartment lives
    under a separate auto-generated ЖК and the serializer's cross-project
    check fails. Override `project=` and the apartment will be minted under it.
    """
    class Meta:
        model = Contract

    project = factory.SubFactory(ProjectFactory)
    apartment = factory.LazyAttribute(
        lambda o: ApartmentFactory(floor__section__building__project=o.project),
    )
    signer = factory.SubFactory(ClientContactFactory)
    contract_number = factory.Sequence(lambda n: f"ЯМ-{n:05d}")
    date = factory.LazyFunction(date.today)
    total_amount = Decimal("750000000.00")
    down_payment = Decimal("225000000.00")


class ContractTemplateFactory(DjangoModelFactory):
    class Meta:
        model = ContractTemplate

    title = factory.Sequence(lambda n: f"Шаблон {n}")
    body = "<p>Default test template body</p>"
    placeholders = factory.LazyFunction(list)
    project = None  # global by default


class PaymentScheduleFactory(DjangoModelFactory):
    class Meta:
        model = PaymentSchedule

    contract = factory.SubFactory(ContractFactory)
    due_date = factory.LazyFunction(date.today)
    amount = Decimal("50000000.00")
    paid_amount = Decimal("0.00")


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    schedule = factory.SubFactory(PaymentScheduleFactory)
    amount = Decimal("10000000.00")
    payment_type = "cash"
    paid_at = factory.LazyFunction(date.today)
