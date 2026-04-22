"""DRF serializers for the objects app.

Per-model serializer + a `children_count` read-only field on the parent
serializers (Project/Building/Section) so list views can show e.g.
"5 корпусов" without an extra round-trip.

`price_per_sqm` on Floor is a string in JSON (DRF default for Decimal),
matching the `MoneyField` convention established in references.Currency.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.objects.models import Building, Floor, Project, Section


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
    class Meta:
        model = Floor
        fields = (
            "id",
            "section",
            "number",
            "price_per_sqm",
            "sort",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")
