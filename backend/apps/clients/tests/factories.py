"""factory-boy factories for the clients app."""
from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from apps.clients.models import (
    Client,
    ClientContact,
    ClientGroup,
    ClientStatus,
    Requisite,
)


class ClientStatusFactory(DjangoModelFactory):
    class Meta:
        model = ClientStatus

    name = factory.LazyFunction(lambda: {"ru": "Активный", "uz": "Faol", "oz": "Фаол"})
    color = "#22c55e"


class ClientGroupFactory(DjangoModelFactory):
    class Meta:
        model = ClientGroup

    name = factory.LazyFunction(lambda: {"ru": "VIP", "uz": "VIP", "oz": "VIP"})


class ClientFactory(DjangoModelFactory):
    class Meta:
        model = Client

    entity = "phys"
    full_name = factory.Sequence(lambda n: f"Иванов Иван {n}")
    phones = factory.LazyFunction(lambda: ["+998901234567"])
    emails = factory.LazyFunction(lambda: ["client@example.com"])


class ClientContactFactory(DjangoModelFactory):
    class Meta:
        model = ClientContact

    client = factory.SubFactory(ClientFactory)
    full_name = factory.Sequence(lambda n: f"Петров Петр {n}")
    role = "подписант"
    phones = factory.LazyFunction(lambda: ["+998902345678"])


class RequisiteFactory(DjangoModelFactory):
    class Meta:
        model = Requisite

    client = factory.SubFactory(ClientFactory)
    type = "local"
    bank_requisite = factory.LazyFunction(
        lambda: {"account": "2020...", "bank": "Hamkorbank", "mfo": "00449"},
    )
