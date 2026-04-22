"""DRF viewsets for the objects app.

Pattern mirrors `apps.references.views`: each ViewSet gets its own permission
base via `_permissions_for(base, action)`. Custom `@action`s (e.g. `book` on
ApartmentViewSet in phase 3.2) carry their own permission gates.

`floor.edit_price` is a dedicated extra permission (see permission_tree) —
not enforced here yet; phase 3.3 ties it to the explicit price-change action
on FloorViewSet.
"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.mixins import ProtectedDestroyMixin
from apps.core.permissions import HasPermission
from apps.objects.models import Building, Floor, Project, Section
from apps.objects.serializers import (
    BuildingSerializer,
    FloorSerializer,
    ProjectSerializer,
    SectionSerializer,
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
