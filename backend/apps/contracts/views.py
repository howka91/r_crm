"""DRF viewsets for the contracts app.

Permission bases map to the tree in `apps.core.permission_tree`:

  * `ContractViewSet`          → `contracts.unsigned.*` (draft lifecycle +
                                  workflow transitions as custom actions).
  * `ContractTemplateViewSet`  → `references.templates.*` (shared with refs).
  * `PaymentScheduleViewSet`   → piggybacks on `contracts.unsigned.*`;
                                  typically populated by the schedule
                                  service, not by direct CRUD.
  * `PaymentViewSet`           → same story; moves to `finance.*` in Phase 6.

Custom workflow actions on ContractViewSet (Phase 5.2):

    POST /contracts/:id/send-to-wait/       → `contracts.unsigned.send_to_wait`
    POST /contracts/:id/approve/            → `contracts.unsigned.approve`
    POST /contracts/:id/sign/               → `contracts.unsigned.sign`
    POST /contracts/:id/request-edit/       → `contracts.unsigned.request_edit`
    POST /contracts/:id/generate-schedule/  → `contracts.unsigned.generate_schedule`

Direct PATCH on `action` / `is_signed` / `is_paid` stays read-only — the
serializer enforces that; the transitions above are the only supported
path.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

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
from apps.contracts.services import schedule as schedule_svc
from apps.contracts.services import transitions
from apps.core.mixins import ProtectedDestroyMixin
from apps.core.permissions import HasPermission

_ACTION_SUFFIX: dict[str, str] = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
    # Custom actions that slot under the same permission base as CRUD.
    "send_to_wait": "send_to_wait",
    "approve": "approve",
    "sign": "sign",
    "request_edit": "request_edit",
    "generate_schedule": "generate_schedule",
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

    # --- Workflow transitions (Phase 5.2) --------------------------------

    def _transition_response(self, result: transitions.TransitionResult) -> Response:
        data = self.get_serializer(result.contract).data
        # Surface the minted contract number distinctly from the full payload
        # so the UI can show a toast "Договор №… отправлен на согласование".
        if result.minted_number:
            data["__minted_contract_number"] = result.minted_number
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="send-to-wait")
    def send_to_wait(self, request: Request, pk=None) -> Response:
        """request → wait. Mints contract_number on first call."""
        contract = self.get_object()
        try:
            result = transitions.send_to_wait(contract, request.user)
        except transitions.TransitionError as e:
            return Response(
                {"detail": str(e), "current_action": e.current},
                status=status.HTTP_409_CONFLICT,
            )
        return self._transition_response(result)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk=None) -> Response:
        """wait → approve."""
        contract = self.get_object()
        try:
            result = transitions.approve(contract, request.user)
        except transitions.TransitionError as e:
            return Response(
                {"detail": str(e), "current_action": e.current},
                status=status.HTTP_409_CONFLICT,
            )
        return self._transition_response(result)

    @action(detail=True, methods=["post"])
    def sign(self, request: Request, pk=None) -> Response:
        """approve → sign_in (+ is_signed=True). Terminal transition."""
        contract = self.get_object()
        try:
            result = transitions.sign(contract, request.user)
        except transitions.TransitionError as e:
            return Response(
                {"detail": str(e), "current_action": e.current},
                status=status.HTTP_409_CONFLICT,
            )
        return self._transition_response(result)

    @action(detail=True, methods=["post"], url_path="request-edit")
    def request_edit(self, request: Request, pk=None) -> Response:
        """wait → edit. Accepts optional `{"reason": "..."}` for the audit snapshot."""
        contract = self.get_object()
        reason = str(request.data.get("reason", "") or "")
        try:
            result = transitions.request_edit(contract, request.user, reason=reason)
        except transitions.TransitionError as e:
            return Response(
                {"detail": str(e), "current_action": e.current},
                status=status.HTTP_409_CONFLICT,
            )
        return self._transition_response(result)

    @action(detail=True, methods=["post"], url_path="generate-schedule")
    def generate_schedule(self, request: Request, pk=None) -> Response:
        """Rebuild PaymentSchedule rows from the contract's Calculation.

        Destructive — wipes existing schedule (and cascading Payments).
        Blocked on signed contracts: once `is_signed=True`, money has likely
        moved and regeneration would orphan Payment rows.
        """
        contract = self.get_object()
        if contract.is_signed:
            return Response(
                {"detail": "Нельзя пересобрать график у подписанного договора."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            rows = schedule_svc.generate_schedule(contract)
        except schedule_svc.ScheduleBuildError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "count": len(rows),
                "schedule": PaymentScheduleSerializer(rows, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


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
