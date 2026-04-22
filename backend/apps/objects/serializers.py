"""DRF serializers for the objects app.

Per-model serializer + a `children_count` read-only field on the parent
serializers (Project/Building/Section) so list views can show e.g.
"5 корпусов" without an extra round-trip.

`price_per_sqm` on Floor is a string in JSON (DRF default for Decimal),
matching the `MoneyField` convention established in references.Currency.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.objects.models import (
    Apartment,
    ApartmentStatusLog,
    Building,
    Floor,
    Project,
    Section,
)


class ProjectSerializer(serializers.ModelSerializer):
    developer_name = serializers.SerializerMethodField()
    buildings_count = serializers.IntegerField(
        source="buildings.count", read_only=True,
    )

    class Meta:
        model = Project
        fields = (
            "id",
            "developer",
            "developer_name",
            "title",
            "address",
            "description",
            "banks",
            "contract_number_index",
            "sort",
            "is_active",
            "buildings_count",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "developer_name",
            "contract_number_index",
            "buildings_count",
            "created_at",
            "modified_at",
        )

    def get_developer_name(self, obj: Project) -> dict | None:
        dev = obj.developer
        return dev.name if dev else None


class BuildingSerializer(serializers.ModelSerializer):
    sections_count = serializers.IntegerField(
        source="sections.count", read_only=True,
    )

    class Meta:
        model = Building
        fields = (
            "id",
            "project",
            "title",
            "number",
            "cadastral_number",
            "date_of_issue",
            "planning_file",
            "sort",
            "is_active",
            "sections_count",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "sections_count",
            "created_at",
            "modified_at",
        )


class SectionSerializer(serializers.ModelSerializer):
    floors_count = serializers.IntegerField(
        source="floors.count", read_only=True,
    )

    class Meta:
        model = Section
        fields = (
            "id",
            "building",
            "title",
            "number",
            "planning_file",
            "sort",
            "is_active",
            "floors_count",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "floors_count",
            "created_at",
            "modified_at",
        )


class FloorSerializer(serializers.ModelSerializer):
    apartments_count = serializers.IntegerField(
        source="apartments.count", read_only=True,
    )

    class Meta:
        model = Floor
        fields = (
            "id",
            "section",
            "number",
            "price_per_sqm",
            "sort",
            "is_active",
            "apartments_count",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "apartments_count", "created_at", "modified_at")


class ApartmentSerializer(serializers.ModelSerializer):
    """Full Apartment shape. `status` is writable via create/update — but only
    to allowable values. For state transitions post-create, clients should
    hit the `change-status` action; writing `status` directly via PATCH is
    supported for superusers and initial data import (no transition check)."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Apartment
        fields = (
            "id",
            "floor",
            "number",
            "rooms_count",
            "area",
            "total_bti_area",
            "total_price",
            "surcharge",
            "is_duplex",
            "is_studio",
            "is_euro_planning",
            "planning_file",
            "decoration",
            "output_window",
            "occupied_by",
            "characteristics",
            "status",
            "status_display",
            "booking_expires_at",
            "sort",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "status_display",
            "booking_expires_at",
            "created_at",
            "modified_at",
        )


class ApartmentStatusLogSerializer(serializers.ModelSerializer):
    """Read-only — writes happen inside services.apartments.change_status."""

    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ApartmentStatusLog
        fields = (
            "id",
            "apartment",
            "old_status",
            "new_status",
            "changed_by",
            "changed_by_name",
            "comment",
            "created_at",
        )
        read_only_fields = fields

    def get_changed_by_name(self, obj: ApartmentStatusLog) -> str | None:
        return obj.changed_by.full_name if obj.changed_by else None


class ChangeStatusInputSerializer(serializers.Serializer):
    """Payload for the `POST /apartments/:id/change-status/` action."""

    new_status = serializers.ChoiceField(choices=Apartment.Status.choices)
    comment = serializers.CharField(max_length=512, required=False, allow_blank=True)
