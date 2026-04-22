"""DRF viewsets for the objects app.

Pattern mirrors `apps.references.views`: each ViewSet gets its own permission
base via `_permissions_for(base, action)`. Custom `@action`s (e.g. `book` on
ApartmentViewSet in phase 3.2) carry their own permission gates.

`floor.edit_price` is a dedicated extra permission (see permission_tree) —
not enforced here yet; phase 3.3 ties it to the explicit price-change action
on FloorViewSet.
"""
from __future__ import annotations

from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import ProtectedDestroyMixin
from apps.core.permissions import HasPermission
from apps.objects.models import (
    Apartment,
    ApartmentStatusLog,
    Building,
    Floor,
    Project,
    Section,
)
from apps.objects.serializers import (
    ApartmentSerializer,
    ApartmentStatusLogSerializer,
    BuildingSerializer,
    ChangeStatusInputSerializer,
    FloorSerializer,
    ProjectSerializer,
    SectionSerializer,
)
from apps.objects.services.apartments import (
    InvalidStatusTransition,
    change_status,
)

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


class ProjectViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Project.objects.select_related("developer").all()
    serializer_class = ProjectSerializer
    filterset_fields = ("is_active", "developer")
    search_fields = ("address",)

    def get_permissions(self):
        return _permissions_for("objects.projects", self.action)


class BuildingViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Building.objects.select_related("project").all()
    serializer_class = BuildingSerializer
    filterset_fields = ("is_active", "project")
    search_fields = ("number", "cadastral_number")

    def get_permissions(self):
        return _permissions_for("objects.buildings", self.action)


class SectionViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Section.objects.select_related("building", "building__project").all()
    serializer_class = SectionSerializer
    filterset_fields = ("is_active", "building")

    def get_permissions(self):
        return _permissions_for("objects.sections", self.action)


class FloorViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Floor.objects.select_related("section", "section__building").all()
    serializer_class = FloorSerializer
    filterset_fields = ("is_active", "section")

    def get_permissions(self):
        return _permissions_for("objects.floors", self.action)


class ApartmentViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = (
        Apartment.objects
        .select_related("floor", "floor__section", "floor__section__building")
        .prefetch_related("characteristics")
        .all()
    )
    serializer_class = ApartmentSerializer
    filterset_fields = ("is_active", "floor", "status")
    search_fields = ("number",)

    def get_permissions(self):
        # The custom `change_status` action carries its own permission key
        # (`objects.apartments.change_status`) — distinct from the standard
        # edit flow so roles can separate "can edit apartment metadata" from
        # "can move apartment through the sales pipeline".
        if self.action == "change_status":
            return [
                IsAuthenticated(),
                HasPermission("objects.apartments.change_status"),
            ]
        # CRUD falls back to the standard map, mirroring the rest of the app.
        return _permissions_for("objects.apartments", self.action)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request: Request, pk: str | None = None) -> Response:
        """Move the apartment through the status workflow.

        Calls `services.apartments.change_status` (the single source of truth
        for legal transitions). Returns the updated apartment plus the id of
        the log row so the client can refetch the log if needed.
        """
        apt: Apartment = self.get_object()
        payload = ChangeStatusInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            result = change_status(
                apt,
                payload.validated_data["new_status"],
                by=request.user if request.user.is_authenticated else None,
                comment=payload.validated_data.get("comment", ""),
            )
        except InvalidStatusTransition as e:
            return Response(
                {"detail": str(e), "code": "invalid_transition"},
                status=http_status.HTTP_409_CONFLICT,
            )
        apt.refresh_from_db()
        return Response(
            {
                "apartment": ApartmentSerializer(apt).data,
                "log_id": result.log_id,
            },
            status=http_status.HTTP_200_OK,
        )


class ApartmentStatusLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only log access. Scoped under the apartment view permission —
    if you can see an apartment, you can see its log."""

    queryset = (
        ApartmentStatusLog.objects
        .select_related("apartment", "changed_by")
        .all()
    )
    serializer_class = ApartmentStatusLogSerializer
    filterset_fields = ("apartment",)

    def get_permissions(self):
        return _permissions_for("objects.apartments", self.action)
