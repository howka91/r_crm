"""DRF viewsets for the references app.

Each viewset is permission-gated via `HasPermission(key)` in `get_permissions`,
mirroring the pattern established in `apps.users.views` (RoleViewSet,
StaffViewSet).

Lookup viewsets (13 of them) share the `references.lookups` permission bundle
and are built via the `make_lookup_viewset(model)` factory.
"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import HasPermission
from apps.references.models import LOOKUP_MODELS, Currency, Developer, SalesOffice
from apps.references.serializers import (
    LOOKUP_SERIALIZERS,
    CurrencySerializer,
    DeveloperSerializer,
    SalesOfficeSerializer,
)

# DRF action → suffix of the permission key ("clients.view" etc.)
_ACTION_SUFFIX: dict[str, str] = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


def _permissions_for(base: str, action: str | None) -> list:
    """Build DRF permission list for a ViewSet action.

    Custom `@action`s (not in the CRUD map) fall back to auth-only — register
    their specific permission on the decorator if needed.
    """
    suffix = _ACTION_SUFFIX.get(action or "")
    if suffix is None:
        return [IsAuthenticated()]
    return [IsAuthenticated(), HasPermission(f"{base}.{suffix}")]


class DeveloperViewSet(viewsets.ModelViewSet):
    schema_tags = ["Справочники"]
    queryset = Developer.objects.all()
    serializer_class = DeveloperSerializer
    filterset_fields = ("is_active",)
    search_fields = ("inn", "director", "bank_account")

    def get_permissions(self):
        return _permissions_for("references.developers", self.action)


class SalesOfficeViewSet(viewsets.ModelViewSet):
    schema_tags = ["Справочники"]
    queryset = SalesOffice.objects.all()
    serializer_class = SalesOfficeSerializer
    filterset_fields = ("is_active",)
    search_fields = ("address",)

    def get_permissions(self):
        return _permissions_for("references.offices", self.action)


class CurrencyViewSet(viewsets.ModelViewSet):
    schema_tags = ["Справочники"]
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    filterset_fields = ("is_active",)
    search_fields = ("code",)

    def get_permissions(self):
        return _permissions_for("references.currencies", self.action)


# --- Lookup factory --------------------------------------------------------


def make_lookup_viewset(model_cls: type) -> type[viewsets.ModelViewSet]:
    """Build a ModelViewSet subclass for the given LookupModel concrete class.

    Uses `_permissions_for("references.lookups", action)` — all 13 lookups
    share a single permission bundle (see `apps.core.permission_tree`).
    """
    serializer_cls = LOOKUP_SERIALIZERS[model_cls]

    def get_permissions(self):
        return _permissions_for("references.lookups", self.action)

    return type(
        f"{model_cls.__name__}ViewSet",
        (viewsets.ModelViewSet,),
        {
            "queryset": model_cls.objects.all(),
            "serializer_class": serializer_cls,
            "filterset_fields": ("is_active",),
            "get_permissions": get_permissions,
            "schema_tags": ["Справочники"],
        },
    )


LOOKUP_VIEWSETS: dict[type, type[viewsets.ModelViewSet]] = {
    model: make_lookup_viewset(model) for model in LOOKUP_MODELS
}
