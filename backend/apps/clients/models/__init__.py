"""Clients models — package entry point.

Mirrors the layout of apps.references.models and apps.objects.models: one
file per substantial model, re-exported so `from apps.clients.models import
Client` keeps working. `ClientStatus` / `ClientGroup` are small LookupModel
subclasses tied to the clients domain only, so they live here rather than
in references.
"""
from apps.clients.models.client import Client
from apps.clients.models.client_contact import ClientContact
from apps.clients.models.client_group import ClientGroup
from apps.clients.models.client_status import ClientStatus
from apps.clients.models.requisite import Requisite

__all__ = [
    "ClientStatus",
    "ClientGroup",
    "Client",
    "ClientContact",
    "Requisite",
]
