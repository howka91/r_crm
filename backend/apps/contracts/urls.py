"""URL routes for the contracts app.

Mounted under `/api/v1/` by `conf.urls`:

    /api/v1/contracts/
    /api/v1/contract-templates/
    /api/v1/payment-schedules/
    /api/v1/payments/

Workflow transition endpoints land here in Phase 5.2 as DRF custom actions
on `ContractViewSet`; payments-service endpoints in Phase 6.
"""
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.contracts.views import (
    ContractTemplateViewSet,
    ContractViewSet,
    PaymentScheduleViewSet,
    PaymentViewSet,
)

router = DefaultRouter()
router.register("contracts", ContractViewSet, basename="contract")
router.register("contract-templates", ContractTemplateViewSet, basename="contract-template")
router.register("payment-schedules", PaymentScheduleViewSet, basename="payment-schedule")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
]
