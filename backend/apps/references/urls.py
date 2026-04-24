"""URL routes for the references app.

Mounted under `/api/v1/` by `conf.urls`:
  /api/v1/developers/
  /api/v1/sales-offices/
  /api/v1/currencies/
  /api/v1/{apartment-types,room-types,construction-stages,decorations,
           premises-decorations,home-materials,output-windows,occupied-by,
           badges,payment-methods,payment-in-percent,regions,locations}/
"""
from __future__ import annotations

import re

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.references.models import LOOKUP_MODELS
from apps.references.views import (
    LOOKUP_VIEWSETS,
    CurrencyViewSet,
    DeveloperViewSet,
    PlanningViewSet,
    SalesOfficeViewSet,
)


def _kebab(name: str) -> str:
    """'PaymentInPercent' → 'payment-in-percent'."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


router = DefaultRouter()
router.register("developers", DeveloperViewSet, basename="developer")
router.register("sales-offices", SalesOfficeViewSet, basename="sales-office")
router.register("currencies", CurrencyViewSet, basename="currency")
router.register("plannings", PlanningViewSet, basename="planning")

# Register each lookup under its kebab-cased class name.
for model in LOOKUP_MODELS:
    route = _kebab(model.__name__)
    router.register(route, LOOKUP_VIEWSETS[model], basename=route)

urlpatterns = [
    path("", include(router.urls)),
]
