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


# --- ContractTemplate -----------------------------------------------------


class ContractTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractTemplate
        fields = (
            "id",
            "title",
            "file",
            "author",
            "placeholders",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")


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
    author_name = serializers.SerializerMethodField()

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

    class Meta:
        model = Contract
        fields = (
            "id",
            # links
            "project", "project_title",
            "apartment", "apartment_number",
            "calculation",
            "signer", "signer_name", "client_id", "client_name",
            "author", "author_name",
            # core data
            "contract_number",
            "date",
            "send_date",
            "related_person",
            "description",
            # money
            "total_amount",
            "down_payment",
            # payment channels
            "payment_methods",
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
            "signer_name",
            "client_id",
            "client_name",
            "author_name",
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
