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
from apps.contracts.services import docgen as docgen_svc
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
    "generate_pdf": "generate_pdf",
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

    schema_tags = ["Договоры"]
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

    @action(detail=True, methods=["post"], url_path="generate-pdf")
    def generate_pdf(self, request: Request, pk=None) -> Response:
        """Render the contract's template into PDF and attach to Contract.file.

        Requires `contract.template` to be set. Blocked on signed contracts
        — once signed, the PDF is the legal artefact and re-rendering is
        a cancel-then-create-new flow.
        """
        contract = self.get_object()
        if contract.is_signed:
            return Response(
                {"detail": "Нельзя перегенерировать PDF у подписанного договора."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            result = docgen_svc.generate_pdf(contract)
        except docgen_svc.TemplateNotSet as e:
            return Response(
                {"detail": str(e), "code": "template_not_set"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except docgen_svc.UnknownPlaceholder as e:
            return Response(
                {
                    "detail": str(e),
                    "code": "unknown_placeholder",
                    "unknown": e.unknown,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        contract.refresh_from_db()
        return Response(
            {
                "contract": self.get_serializer(contract).data,
                "pdf_url": contract.file.url if contract.file else None,
                "pdf_size": result.pdf_size,
                "filled": result.filled,
            },
            status=status.HTTP_200_OK,
        )

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
    schema_tags = ["Договоры"]
    queryset = (
        ContractTemplate.objects
        .select_related("author", "project")
        .all()
    )
    serializer_class = ContractTemplateSerializer
    filterset_fields = ("is_active", "project")
    search_fields = ("title",)

    def get_permissions(self):
        return _permissions_for("references.templates", self.action)

    # --- Extra gate: creating/editing a *global* template (project is null)
    # requires the `references.templates.manage_global` key on top of the
    # generic create/edit. Lets us grant project-scoped template authorship
    # to per-project staff without exposing the global pool.

    def _enforce_global_gate(self, request, project_id) -> Response | None:
        if project_id:
            return None  # project-scoped — generic permission suffices
        if request.user.is_superuser:
            return None
        role = getattr(request.user, "role", None)
        from apps.core.permissions import check as perm_check
        if perm_check(
            getattr(role, "permissions", None),
            "references.templates.manage_global",
        ):
            return None
        return Response(
            {
                "detail": (
                    "Глобальные шаблоны (без проекта) может создавать только "
                    "роль с разрешением references.templates.manage_global."
                ),
                "code": "global_template_forbidden",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    def create(self, request, *args, **kwargs):
        blocked = self._enforce_global_gate(request, request.data.get("project"))
        if blocked is not None:
            return blocked
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # Use the incoming payload for the new project_id if present;
        # otherwise fall back to what the row currently has.
        existing = self.get_object()
        project_id = request.data.get("project", existing.project_id)
        blocked = self._enforce_global_gate(request, project_id)
        if blocked is not None:
            return blocked
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        existing = self.get_object()
        project_id = request.data.get("project", existing.project_id)
        blocked = self._enforce_global_gate(request, project_id)
        if blocked is not None:
            return blocked
        return super().partial_update(request, *args, **kwargs)


class PaymentScheduleViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    schema_tags = ["Договоры"]
    queryset = PaymentSchedule.objects.select_related("contract").all()
    serializer_class = PaymentScheduleSerializer
    filterset_fields = ("is_active", "contract", "status")
    ordering_fields = ("due_date", "amount")

    def get_permissions(self):
        return _permissions_for("contracts.unsigned", self.action)


class PaymentViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    schema_tags = ["Договоры"]
    queryset = Payment.objects.select_related(
        "schedule", "schedule__contract", "recorded_by",
    ).all()
    serializer_class = PaymentSerializer
    filterset_fields = ("is_active", "schedule", "payment_type")
    search_fields = ("receipt_number",)
    ordering_fields = ("paid_at", "amount")

    def get_permissions(self):
        return _permissions_for("contracts.unsigned", self.action)
