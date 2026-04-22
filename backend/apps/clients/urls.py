"""URL routes for the clients app.

Mounted under `/api/v1/` by `conf.urls`:
  /api/v1/clients/
  /api/v1/client-contacts/
  /api/v1/client-requisites/
  /api/v1/client-statuses/
  /api/v1/client-groups/
"""
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.clients.views import (
    ClientContactViewSet,
    ClientGroupViewSet,
    ClientStatusViewSet,
    ClientViewSet,
    RequisiteViewSet,
)

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("client-contacts", ClientContactViewSet, basename="client-contact")
router.register("client-requisites", RequisiteViewSet, basename="client-requisite")
router.register("client-statuses", ClientStatusViewSet, basename="client-status")
router.register("client-groups", ClientGroupViewSet, basename="client-group")

urlpatterns = [
    path("", include(router.urls)),
]
