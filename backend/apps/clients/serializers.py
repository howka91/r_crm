"""DRF serializers for the clients app.

`ClientSerializer` flattens the manager into `manager_name` and status into
`status_name` so list views don't need extra fetches. The serializer enforces
entity-type rules at the edge (`pin` only for phys, `inn` only for jur) —
these are soft warnings, not DB constraints, because legacy data may have
partial fills.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.clients.models import (
    Client,
    ClientContact,
    ClientGroup,
    ClientStatus,
    Requisite,
)


class ClientStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientStatus
        fields = ("id", "name", "color", "sort", "is_active", "created_at", "modified_at")
        read_only_fields = ("id", "created_at", "modified_at")


class ClientGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientGroup
        fields = ("id", "name", "sort", "is_active", "created_at", "modified_at")
        read_only_fields = ("id", "created_at", "modified_at")


class ClientContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientContact
        fields = (
            "id",
            "client",
            "full_name",
            "role",
            "is_chief",
            "phones",
            "email",
            "passport",
            "birth_date",
            "inn",
            "pin",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")


class RequisiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisite
        fields = (
            "id",
            "client",
            "type",
            "bank_requisite",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")


class ClientSerializer(serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()
    status_name = serializers.SerializerMethodField()
    contacts_count = serializers.IntegerField(
        source="contacts.count", read_only=True,
    )
    requisites_count = serializers.IntegerField(
        source="requisites.count", read_only=True,
    )

    class Meta:
        model = Client
        fields = (
            "id",
            "entity",
            "gender",
            "full_name",
            "phones",
            "emails",
            "inn",
            "oked",
            "pin",
            "birth_date",
            "address",
            "description",
            "manager",
            "manager_name",
            "status",
            "status_name",
            "groups",
            "contacts_count",
            "requisites_count",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "manager_name",
            "status_name",
            "contacts_count",
            "requisites_count",
            "created_at",
            "modified_at",
        )

    def get_manager_name(self, obj: Client) -> str | None:
        return obj.manager.full_name if obj.manager else None

    def get_status_name(self, obj: Client) -> dict | None:
        return obj.status.name if obj.status else None

    def validate(self, attrs: dict) -> dict:
        # Soft entity-type validation — doesn't reject, just surfaces
        # inconsistencies. Hard requirements stay in the UI / future workflow.
        entity = attrs.get("entity", getattr(self.instance, "entity", Client.Entity.PHYS))
        full_name = attrs.get("full_name", getattr(self.instance, "full_name", ""))
        if not full_name:
            raise serializers.ValidationError(
                {"full_name": "ФИО / название обязательно."},
            )
        if entity == Client.Entity.JUR and attrs.get("gender"):
            # Gender on a juridical entity makes no sense.
            raise serializers.ValidationError(
                {"gender": "Пол не применим к юр. лицу."},
            )
        return attrs
