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

import os
import uuid
from datetime import date as _date_today

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
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
    # `.all_objects` (not the default SoftDeleteManager) so archived
    # templates stay visible in the catalog with an "Inactive" chip —
    # managers flip is_active to retire a template without losing it.
    # Matches the policy established for other reference ViewSets.
    queryset = (
        ContractTemplate.all_objects
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

    # --- Image upload for logos / inline pictures ------------------------
    #
    # Returns a URL the Tiptap editor drops into an <img src="...">. Files
    # live under MEDIA_ROOT/contract_templates/images/YYYY/MM/ with a uuid
    # name to avoid collisions and make purging predictable. Permitted
    # content types are locked to a small image whitelist — SVG is allowed
    # (WeasyPrint renders it natively and <img src> in the editor treats
    # it as a picture, no script execution).

    _IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
    _IMAGE_ALLOWED_MIMES = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/gif": ".gif",
    }

    @action(
        detail=False,
        methods=["post"],
        url_path="upload-image",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request: Request) -> Response:
        # Permission: anyone who may create *or* edit templates. Gating via
        # get_permissions + _ACTION_SUFFIX would fit only one of the two;
        # checking both explicitly is simpler and accurate.
        from apps.core.permissions import check as perm_check

        role = getattr(request.user, "role", None)
        perms = getattr(role, "permissions", None)
        allowed = (
            request.user.is_superuser
            or perm_check(perms, "references.templates.create")
            or perm_check(perms, "references.templates.edit")
        )
        if not allowed:
            return Response(
                {"detail": "Недостаточно прав для загрузки изображений."},
                status=status.HTTP_403_FORBIDDEN,
            )

        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Ожидался файл в поле `file`."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mime = (getattr(upload, "content_type", "") or "").lower()
        ext = self._IMAGE_ALLOWED_MIMES.get(mime)
        if ext is None:
            return Response(
                {
                    "detail": (
                        f"Неподдерживаемый тип файла: {mime or 'unknown'}. "
                        "Допустимы PNG, JPG, WebP, GIF, SVG."
                    ),
                    "code": "unsupported_media_type",
                },
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        if upload.size > self._IMAGE_MAX_BYTES:
            return Response(
                {
                    "detail": "Файл слишком большой (лимит 5 МБ).",
                    "code": "file_too_large",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = _date_today.today()
        rel_dir = os.path.join(
            "contract_templates", "images",
            f"{today.year:04d}", f"{today.month:02d}",
        )
        filename = f"{uuid.uuid4().hex}{ext}"
        rel_path = os.path.join(rel_dir, filename)

        saved_path = default_storage.save(
            rel_path, ContentFile(upload.read()),
        )
        url = settings.MEDIA_URL.rstrip("/") + "/" + saved_path.replace(os.sep, "/")
        return Response(
            {
                "url": url,
                "filename": filename,
                "size": upload.size,
                "content_type": mime,
            },
            status=status.HTTP_201_CREATED,
        )

    # --- DOCX template validation ---------------------------------------
    #
    # Called from the frontend during .docx upload before persisting the
    # template. Returns the list of Jinja2 tags found in the file split
    # into known / unknown roots so the UI can warn the author about
    # typos (e.g. `{{ clinet.name }}`) before saving.

    _DOCX_MAX_BYTES = 10 * 1024 * 1024  # 10 MB — generous for lawyer files
    _DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @action(
        detail=False,
        methods=["post"],
        url_path="validate-docx",
        parser_classes=[MultiPartParser, FormParser],
    )
    def validate_docx(self, request: Request) -> Response:
        from apps.core.permissions import check as perm_check
        from apps.contracts.services import docx_validator

        role = getattr(request.user, "role", None)
        perms = getattr(role, "permissions", None)
        if not (
            request.user.is_superuser
            or perm_check(perms, "references.templates.create")
            or perm_check(perms, "references.templates.edit")
        ):
            return Response(
                {"detail": "Недостаточно прав для валидации шаблонов."},
                status=status.HTTP_403_FORBIDDEN,
            )

        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Ожидался .docx-файл в поле `file`."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mime = (getattr(upload, "content_type", "") or "").lower()
        name = (upload.name or "").lower()
        if mime != self._DOCX_MIME and not name.endswith(".docx"):
            return Response(
                {
                    "detail": "Поддерживается только .docx (Word 2007+).",
                    "code": "unsupported_media_type",
                },
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        if upload.size > self._DOCX_MAX_BYTES:
            return Response(
                {
                    "detail": "Файл слишком большой (лимит 10 МБ).",
                    "code": "file_too_large",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # docxtpl needs a real file-like with seek() — SimpleUploadedFile
            # supports that, but chain through a bytes buffer for safety.
            import io as _io
            buf = _io.BytesIO(upload.read())
            result = docx_validator.validate(buf)
        except Exception as e:  # pragma: no cover — docxtpl may raise on malformed files
            return Response(
                {
                    "detail": f"Не удалось разобрать файл как .docx: {e!s}",
                    "code": "docx_parse_failed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result.as_dict(), status=status.HTTP_200_OK)


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
