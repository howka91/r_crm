"""DRF viewsets for the contracts app.

Permission bases map to the tree in `apps.core.permission_tree`:

  * `ContractViewSet`          → `contracts.unsigned.*` (draft lifecycle)
  * `ContractTemplateViewSet`  → `references.templates.*` (shared with refs)
  * `PaymentScheduleViewSet`   → piggybacks on `contracts.unsigned.*` for
                                 CRUD until 5.2 brings the payments service
                                 (which will gate schedule creation behind
                                 contract signing).
  * `PaymentViewSet`           → same story; moves to `finance.*` in Phase 6.

Workflow transition endpoints (`/contracts/:id/send-to-wait/`, `/approve/`,
`/sign/`, `/request-edit/`) arrive in Phase 5.2. For 5.1 the
`action` / `is_signed` / `is_paid` fields are read-only on PATCH — callers
cannot bypass the workflow by editing them directly.
"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.contracts.models import (
    Contract,
    ContractTemplate,
    Payment,
    PaymentSchedule,
)
from apps.contracts.serializers import (
    ContractSerializer,
    ContractTemplateSerializer,
    PaymentScheduleSerializer,
    PaymentSerializer,
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


class ContractViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    """CRUD for contracts.

    `queryset` eagerly prefetches the common denormalisation targets
    (project, apartment chain, signer + client, author) so the list endpoint
    stays O(1) per row. `contracts.unsigned` is the permission base — in
    5.2 the signed-view will get its own filtered endpoint.
    """

    queryset = (
        Contract.objects
        .select_related(
            "project",
            "apartment",
            "apartment__floor",
            "apartment__floor__section",
            "apartment__floor__section__building",
            "calculation",
            "signer",
            "signer__client",
            "author",
        )
        .prefetch_related("payment_methods")
        .all()
    )
    serializer_class = ContractSerializer
    filterset_fields = (
        "is_active",
        "project",
        "apartment",
        "signer",
        "action",
        "is_signed",
        "is_paid",
        "is_mortgage",
    )
    search_fields = (
        "contract_number",
        "related_person",
        "signer__full_name",
        "signer__client__full_name",
    )
    ordering_fields = ("date", "contract_number", "total_amount", "created_at")

    def get_permissions(self):
        return _permissions_for("contracts.unsigned", self.action)


class ContractTemplateViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = ContractTemplate.objects.select_related("author").all()
    serializer_class = ContractTemplateSerializer
    filterset_fields = ("is_active",)
    search_fields = ("title",)

    def get_permissions(self):
        return _permissions_for("references.templates", self.action)


class PaymentScheduleViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = PaymentSchedule.objects.select_related("contract").all()
    serializer_class = PaymentScheduleSerializer
    filterset_fields = ("is_active", "contract", "status")
    ordering_fields = ("due_date", "amount")

    def get_permissions(self):
        return _permissions_for("contracts.unsigned", self.action)


class PaymentViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.select_related(
        "schedule", "schedule__contract", "recorded_by",
    ).all()
    serializer_class = PaymentSerializer
    filterset_fields = ("is_active", "schedule", "payment_type")
    search_fields = ("receipt_number",)
    ordering_fields = ("paid_at", "amount")

    def get_permissions(self):
        return _permissions_for("contracts.unsigned", self.action)
