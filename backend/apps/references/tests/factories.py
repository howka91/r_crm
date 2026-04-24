"""factory-boy factories for the references app."""
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.references.models import Currency, Developer, Planning, SalesOffice


class DeveloperFactory(DjangoModelFactory):
    class Meta:
        model = Developer

    name = factory.LazyFunction(lambda: {"ru": "Тест-застройщик", "uz": "Test quruvchi", "oz": "Тест қурувчи"})
    director = factory.Faker("name")
    address = factory.Faker("address")
    email = factory.Sequence(lambda n: f"dev{n}@example.com")
    phone = "+998901234567"
    inn = factory.Sequence(lambda n: f"30000000{n:04d}")


class SalesOfficeFactory(DjangoModelFactory):
    class Meta:
        model = SalesOffice

    name = factory.LazyFunction(lambda: {"ru": "Офис", "uz": "Ofis", "oz": "Офис"})
    address = factory.Faker("address")
    latitude = Decimal("41.3111")
    longitude = Decimal("69.2797")
    phone = "+998901234567"


class PlanningFactory(DjangoModelFactory):
    class Meta:
        model = Planning

    # `project` is required — pass it explicitly (no SubFactory default
    # to avoid pulling in ProjectFactory at import time).
    name = factory.LazyFunction(lambda: {
        "ru": "Тест-планировка",
        "uz": "Test reja",
        "oz": "Тест режа",
    })
    code = factory.Sequence(lambda n: f"P-{n:03d}")
    rooms_count = 2
    area = Decimal("50.00")


class CurrencyFactory(DjangoModelFactory):
    class Meta:
        model = Currency
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: ["USD", "EUR", "RUB", "UZS"][n % 4])
    symbol = "$"
    name = factory.LazyFunction(lambda: {"ru": "Валюта", "uz": "Valyuta", "oz": "Валюта"})
    rate = Decimal("12500.00")
