"""DRF serializers for the contracts app.

Listings denormalise the hot fields so a contracts table doesn't have to
make follow-up fetches: apartment number, project title, signer name, and
`client_id` (reached via `signer.client` — there is no direct FK, see
`contract.py`).

Workflow transitions (`action` → `wait/edit/approve/sign_in`) are NOT
changeable via plain PATCH — the serializer marks `action` read-only on
update; transitions live in `services.transitions` and ship in Phase 5.2
as dedicated ViewSet actions.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.contracts.models import (
    Contract,
    ContractTemplate,
    Payment,
    PaymentSchedule,
)
from apps.contracts.services import aggregates


# --- ContractTemplate -----------------------------------------------------


class ContractTemplateSerializer(serializers.ModelSerializer):
    project_title = serializers.SerializerMethodField()
    is_global = serializers.BooleanField(read_only=True)
    # DOCX file (only populated when source="docx"). DRF serializes as
    # absolute URL when a request is in context.
    file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = ContractTemplate
        fields = (
            "id",
            "title",
            "source",
            "body",
            "file",
            "placeholders",
            "project",
            "project_title",
            "is_global",
            "author",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "project_title", "is_global", "created_at", "modified_at")

    def get_project_title(self, obj: ContractTemplate):
        return getattr(obj.project, "title", None) if obj.project_id else None

    def validate(self, attrs):
        """Cross-field checks that depend on `source`.

        For html-sourced templates, `body` is the authoring surface and
        must carry content; `file` must stay empty. For docx-sourced
        templates it is reversed: `file` is required, `body` unused.

        On partial_update we fall back to the instance values when the
        field isn't in attrs — so flipping only `title` doesn't require
        re-posting the whole bundle.
        """
        source = attrs.get("source") or (
            self.instance.source if self.instance else ContractTemplate.Source.HTML
        )
        body = attrs.get("body") if "body" in attrs else (
            self.instance.body if self.instance else ""
        )
        file = attrs.get("file") if "file" in attrs else (
            self.instance.file if self.instance else None
        )
        if source == ContractTemplate.Source.HTML:
            if not (body or "").strip():
                raise serializers.ValidationError(
                    {"body": "HTML-шаблон не может быть пустым."},
                )
        elif source == ContractTemplate.Source.DOCX:
            if not file:
                raise serializers.ValidationError(
                    {"file": "DOCX-файл обязателен для шаблонов этого типа."},
                )
        return attrs

    def validate_placeholders(self, value):
        """Every entry must have `key` + `path` as non-empty strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Должен быть массив объектов.")
        seen: set[str] = set()
        for idx, entry in enumerate(value):
            if not isinstance(entry, dict):
                raise serializers.ValidationError(
                    f"Элемент #{idx}: ожидается объект {{key, path, label}}.",
                )
            key = (entry.get("key") or "").strip()
            path = (entry.get("path") or "").strip()
            if not key or not path:
                raise serializers.ValidationError(
                    f"Элемент #{idx}: key и path обязательны.",
                )
            if key in seen:
                raise serializers.ValidationError(
                    f"Ключ {key!r} указан более одного раза.",
                )
            seen.add(key)
        return value


# --- Contract -------------------------------------------------------------


class ContractSerializer(serializers.ModelSerializer):
    # Denormalised for listings — avoid N+1 on the contracts table.
    project_title = serializers.SerializerMethodField()
    apartment_number = serializers.CharField(
        source="apartment.number", read_only=True,
    )
    signer_name = serializers.CharField(source="signer.full_name", read_only=True)
    client_id = serializers.IntegerField(source="signer.client_id", read_only=True)
    client_name = serializers.CharField(
        source="signer.client.full_name", read_only=True,
    )
    client_phone = serializers.SerializerMethodField()
    client_status_id = serializers.IntegerField(
        source="signer.client.status_id", read_only=True,
    )
    client_status_name = serializers.SerializerMethodField()
    client_status_color = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()

    # Apartment / pricing snapshot used by the report table.
    apartment_area = serializers.DecimalField(
        source="apartment.area",
        max_digits=8, decimal_places=2, read_only=True,
    )
    apartment_price_per_sqm = serializers.SerializerMethodField()

    # Aggregates over the contract's payment schedules (see services.aggregates).
    payment_types_used = serializers.SerializerMethodField()
    monthly_payment = serializers.SerializerMethodField()
    monthly_debt = serializers.SerializerMethodField()
    remaining_debt = serializers.SerializerMethodField()

    # Drafts may be created without an assigned contract_number; DRF's
    # default introspection pegs CharField+blank+no-default as required, so
    # we declare it explicitly.
    contract_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True,
    )
    related_person = serializers.CharField(
        max_length=255, required=False, allow_blank=True,
    )
    description = serializers.CharField(required=False, allow_blank=True)
    client_note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Contract
        fields = (
            "id",
            # links
            "project", "project_title",
            "apartment", "apartment_number",
            "calculation",
            "signer", "signer_name", "client_id", "client_name",
            "client_phone",
            "client_status_id", "client_status_name", "client_status_color",
            "author", "author_name",
            "template",
            # core data
            "contract_number",
            "date",
            "send_date",
            "related_person",
            "description",
            "client_note",
            # apartment denorm
            "apartment_area",
            "apartment_price_per_sqm",
            # money
            "total_amount",
            "down_payment",
            "monthly_payment",
            "monthly_debt",
            "remaining_debt",
            # payment channels (declared methods)
            "payment_methods",
            # actual channels used (aggregate from Payment rows)
            "payment_types_used",
            # workflow
            "action",
            "is_signed",
            "is_paid",
            "is_mortgage",
            # snapshot
            "requisite",
            "document",
            "old",
            "file",
            "qr",
            # audit
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "project_title",
            "apartment_number",
            "apartment_area",
            "apartment_price_per_sqm",
            "signer_name",
            "client_id",
            "client_name",
            "client_phone",
            "client_status_id",
            "client_status_name",
            "client_status_color",
            "author_name",
            "payment_types_used",
            "monthly_payment",
            "monthly_debt",
            "remaining_debt",
            # Workflow transitions go through dedicated endpoints in 5.2.
            "action",
            "is_signed",
            "is_paid",
            "created_at",
            "modified_at",
        )
        extra_kwargs = {
            "down_payment": {"required": False},
            "total_amount": {"required": False},
        }
        # Disable DRF's auto-generated UniqueTogetherValidator for
        # (project, contract_number). It ignores individual field
        # `required=False` and forces both fields to be supplied on every
        # request — which breaks draft creation with a blank number. DB-level
        # partial unique index still catches real collisions (via
        # IntegrityError), and the contract-number service in 5.2 will
        # generate numbers atomically with `select_for_update` on Project.
        validators: list = []

    def get_project_title(self, obj: Contract) -> Any:
        title = getattr(obj.project, "title", None)
        return title if title else None

    def get_author_name(self, obj: Contract) -> str | None:
        return obj.author.full_name if obj.author_id and obj.author else None

    def get_client_phone(self, obj: Contract) -> str:
        client = getattr(obj.signer, "client", None) if obj.signer_id else None
        phones = getattr(client, "phones", None) or []
        return phones[0] if phones else ""

    def _client_status(self, obj: Contract):
        client = getattr(obj.signer, "client", None) if obj.signer_id else None
        return getattr(client, "status", None) if client else None

    def get_client_status_name(self, obj: Contract):
        status = self._client_status(obj)
        # `name` is an I18nField (JSON {ru, uz, oz}); return the dict so the
        # frontend chooses the locale.
        return status.name if status else None

    def get_client_status_color(self, obj: Contract) -> str | None:
        status = self._client_status(obj)
        return status.color if status else None

    def get_apartment_price_per_sqm(self, obj: Contract):
        # Prefer the calculation snapshot (matches `total_amount` after
        # discounts); fall back to the floor's posted price.
        if obj.calculation_id and obj.calculation:
            return obj.calculation.new_price_per_sqm
        apartment = obj.apartment
        if apartment and apartment.floor_id:
            return apartment.floor.price_per_sqm
        return None

    def get_payment_types_used(self, obj: Contract) -> list[str]:
        return aggregates.payment_types_used(obj)

    def get_monthly_payment(self, obj: Contract):
        return aggregates.monthly_payment(obj)

    def get_monthly_debt(self, obj: Contract):
        return aggregates.monthly_debt(obj)

    def get_remaining_debt(self, obj: Contract):
        return aggregates.remaining_debt(obj)

    def validate(self, attrs: dict) -> dict:
        # Total amount must be >= down payment (matches UI expectation).
        total = attrs.get(
            "total_amount",
            getattr(self.instance, "total_amount", Decimal("0.00")),
        )
        down = attrs.get(
            "down_payment",
            getattr(self.instance, "down_payment", Decimal("0.00")),
        )
        if down and total and down > total:
            raise serializers.ValidationError(
                {"down_payment": "Первый взнос не может превышать сумму договора."},
            )
        # Apartment must belong to the contract's project — no cross-ЖК assignments.
        apartment = attrs.get("apartment") or getattr(self.instance, "apartment", None)
        project = attrs.get("project") or getattr(self.instance, "project", None)
        if apartment and project:
            apt_project_id = apartment.floor.section.building.project_id
            if apt_project_id != project.id:
                raise serializers.ValidationError(
                    {"apartment": "Квартира принадлежит другому ЖК."},
                )
        return attrs


# --- PaymentSchedule ------------------------------------------------------


class PaymentScheduleSerializer(serializers.ModelSerializer):
    debt = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True,
    )

    class Meta:
        model = PaymentSchedule
        fields = (
            "id",
            "contract",
            "due_date",
            "amount",
            "paid_amount",
            "debt",
            "status",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id", "paid_amount", "debt", "created_at", "modified_at",
        )


# --- Payment --------------------------------------------------------------


class PaymentSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(
        source="recorded_by.full_name", read_only=True,
    )
    contract_id = serializers.IntegerField(
        source="schedule.contract_id", read_only=True,
    )

    class Meta:
        model = Payment
        fields = (
            "id",
            "schedule",
            "contract_id",
            "amount",
            "payment_type",
            "paid_at",
            "recorded_by",
            "recorded_by_name",
            "receipt_number",
            "comment",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id", "contract_id", "recorded_by_name",
            "created_at", "modified_at",
        )

    def validate(self, attrs: dict) -> dict:
        """`comment` is required for barter — bartered goods can't be
        identified from the cash amount alone, the description carries the
        actual exchanged item."""
        payment_type = attrs.get("payment_type")
        if payment_type is None and self.instance is not None:
            payment_type = self.instance.payment_type
        if "comment" in attrs:
            comment = attrs["comment"]
        elif self.instance is not None:
            comment = self.instance.comment
        else:
            comment = ""
        if payment_type == Payment.Type.BARTER and not (comment or "").strip():
            raise serializers.ValidationError(
                {"comment": "Описание обязательно при бартере."},
            )
        return attrs
