"""Admin registrations for the objects app."""
from __future__ import annotations

from django.contrib import admin

from apps.objects.models import (
    Apartment,
    ApartmentStatusLog,
    Building,
    Floor,
    Project,
    Section,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "developer", "sort", "is_active")
    list_filter = ("is_active", "developer")
    search_fields = ("address",)
    ordering = ("sort", "id")


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "number", "sort", "is_active")
    list_filter = ("is_active", "project")
    search_fields = ("number", "cadastral_number")
    ordering = ("project_id", "sort", "id")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "building", "number", "sort", "is_active")
    list_filter = ("is_active", "building")
    ordering = ("building_id", "sort", "number", "id")


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "section", "price_per_sqm", "is_active")
    list_filter = ("is_active", "section")
    ordering = ("section_id", "number", "id")


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "number", "floor", "status", "rooms_count", "area", "total_price", "is_active",
    )
    list_filter = ("status", "is_active", "floor")
    search_fields = ("number",)
    ordering = ("floor_id", "sort", "number", "id")
    filter_horizontal = ("characteristics",)
    readonly_fields = ("booking_expires_at",)


@admin.register(ApartmentStatusLog)
class ApartmentStatusLogAdmin(admin.ModelAdmin):
    list_display = ("id", "apartment", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status",)
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in ApartmentStatusLog._meta.fields)
