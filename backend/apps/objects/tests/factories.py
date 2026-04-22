"""factory-boy factories for the objects app."""
from __future__ import annotations

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.objects.models import (
    Apartment,
    Building,
    Calculation,
    DiscountRule,
    Floor,
    PaymentPlan,
    Project,
    Section,
)
from apps.references.models import PaymentInPercent
from apps.references.tests.factories import DeveloperFactory


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    developer = factory.SubFactory(DeveloperFactory)
    title = factory.LazyFunction(lambda: {"ru": "Тест-ЖК", "uz": "Test JK", "oz": "Тест ЖК"})
    address = factory.Faker("address")
    description = factory.LazyFunction(lambda: {"ru": "", "uz": "", "oz": ""})


class BuildingFactory(DjangoModelFactory):
    class Meta:
        model = Building

    project = factory.SubFactory(ProjectFactory)
    title = factory.LazyFunction(lambda: {"ru": "Корпус 1", "uz": "Blok 1", "oz": "Блок 1"})
    number = factory.Sequence(lambda n: f"{n + 1}")


class SectionFactory(DjangoModelFactory):
    class Meta:
        model = Section

    building = factory.SubFactory(BuildingFactory)
    title = factory.LazyFunction(lambda: {"ru": "Подъезд 1", "uz": "Podyezd 1", "oz": "Подъезд 1"})
    number = factory.Sequence(lambda n: (n % 20) + 1)


class FloorFactory(DjangoModelFactory):
    class Meta:
        model = Floor

    section = factory.SubFactory(SectionFactory)
    number = factory.Sequence(lambda n: (n % 30) + 1)
    price_per_sqm = Decimal("15000000.00")


class ApartmentFactory(DjangoModelFactory):
    class Meta:
        model = Apartment

    floor = factory.SubFactory(FloorFactory)
    number = factory.Sequence(lambda n: str(n + 1))
    rooms_count = 2
    area = Decimal("50.00")
    total_price = Decimal("750000000.00")


class PaymentInPercentFactory(DjangoModelFactory):
    class Meta:
        model = PaymentInPercent

    name = factory.LazyFunction(lambda: {"ru": "100%", "uz": "100%", "oz": "100%"})
    percent = Decimal("100.00")


class PaymentPlanFactory(DjangoModelFactory):
    class Meta:
        model = PaymentPlan

    project = factory.SubFactory(ProjectFactory)
    name = factory.LazyFunction(
        lambda: {"ru": "Стандарт", "uz": "Standart", "oz": "Стандарт"},
    )
    down_payment_percent = Decimal("30.00")
    installment_months = 12


class DiscountRuleFactory(DjangoModelFactory):
    class Meta:
        model = DiscountRule

    project = factory.SubFactory(ProjectFactory)
    area_start = Decimal("0.00")
    area_end = Decimal("200.00")
    payment_percent = factory.SubFactory(PaymentInPercentFactory)
    discount_percent = Decimal("5.00")
    is_duplex = False


class CalculationFactory(DjangoModelFactory):
    class Meta:
        model = Calculation

    apartment = factory.SubFactory(ApartmentFactory)
    payment_percent = factory.SubFactory(PaymentInPercentFactory)
    discount_percent = Decimal("0.00")
    new_price_per_sqm = Decimal("15000000.00")
    new_total_price = Decimal("750000000.00")
