"""URL routes for the objects app.

Mounted under `/api/v1/` by `conf.urls`:
  /api/v1/projects/
  /api/v1/buildings/
  /api/v1/sections/
  /api/v1/floors/
"""
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.objects.views import (
    ApartmentStatusLogViewSet,
    ApartmentViewSet,
    BuildingViewSet,
    FloorViewSet,
    ProjectViewSet,
    SectionViewSet,
)

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("buildings", BuildingViewSet, basename="building")
router.register("sections", SectionViewSet, basename="section")
router.register("floors", FloorViewSet, basename="floor")
router.register("apartments", ApartmentViewSet, basename="apartment")
router.register(
    "apartment-status-logs",
    ApartmentStatusLogViewSet,
    basename="apartment-status-log",
)

urlpatterns = [
    path("", include(router.urls)),
]
