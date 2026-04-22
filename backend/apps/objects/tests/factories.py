"""factory-boy factories for the objects app."""
from __future__ import annotations

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.objects.models import Apartment, Building, Floor, Project, Section
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
