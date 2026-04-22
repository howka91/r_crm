"""Admin registrations for the objects app."""
from __future__ import annotations

from django.contrib import admin

from apps.objects.models import Building, Floor, Project, Section


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
