"""DRF viewsets for the clients app.

Pattern mirrors apps.objects.views: each ViewSet gets its own permission
base via `_permissions_for(base, action)`, ProtectedDestroyMixin turns
ProtectedError into a 409.
"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.clients.models import (
    Client,
    ClientContact,
    ClientGroup,
    ClientStatus,
    Requisite,
)
from apps.clients.serializers import (
    ClientContactSerializer,
    ClientGroupSerializer,
    ClientSerializer,
    ClientStatusSerializer,
    RequisiteSerializer,
)
from apps.core.mixins import ProtectedDestroyMixin
from apps.core.permissions import HasPermission

_ACTION_SUFFIX: dict[str, str] = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


def _permissions_for(base: str, action: str | None) -> list:
    suffix = _ACTION_SUFFIX.get(action or "")
    if suffix is None:
        return [IsAuthenticated()]
    return [IsAuthenticated(), HasPermission(f"{base}.{suffix}")]


class ClientStatusViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = ClientStatus.objects.all()
    serializer_class = ClientStatusSerializer
    filterset_fields = ("is_active",)

    def get_permissions(self):
        return _permissions_for("clients.statuses", self.action)


class ClientGroupViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = ClientGroup.objects.all()
    serializer_class = ClientGroupSerializer
    filterset_fields = ("is_active",)

    def get_permissions(self):
        return _permissions_for("clients.groups", self.action)


class ClientViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = (
        Client.objects
        .select_related("manager", "status")
        .prefetch_related("groups")
        .all()
    )
    serializer_class = ClientSerializer
    filterset_fields = ("is_active", "entity", "status", "manager", "groups")
    search_fields = ("full_name", "inn", "pin")

    def get_permissions(self):
        return _permissions_for("clients", self.action)


class ClientContactViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = ClientContact.objects.select_related("client").all()
    serializer_class = ClientContactSerializer
    filterset_fields = ("is_active", "client", "is_chief")
    search_fields = ("full_name", "inn", "pin")

    def get_permissions(self):
        return _permissions_for("clients.contacts", self.action)


class RequisiteViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Requisite.objects.select_related("client").all()
    serializer_class = RequisiteSerializer
    filterset_fields = ("is_active", "client", "type")

    def get_permissions(self):
        return _permissions_for("clients.requisites", self.action)
