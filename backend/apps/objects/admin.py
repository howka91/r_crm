"""Admin registrations for the objects app."""
from __future__ import annotations

from django.contrib import admin

from apps.objects.models import (
    Apartment,
    ApartmentStatusLog,
    Building,
    BuildingPhoto,
    Calculation,
    DiscountRule,
    Floor,
    PaymentPlan,
    PriceHistory,
    Project,
    ProjectPhoto,
    Section,
)


class ProjectPhotoInline(admin.TabularInline):
    model = ProjectPhoto
    extra = 0
    fields = ("file", "caption", "sort", "is_active")


class BuildingPhotoInline(admin.TabularInline):
    model = BuildingPhoto
    extra = 0
    fields = ("file", "caption", "sort", "is_active")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "developer", "sort", "is_active")
    list_filter = ("is_active", "developer")
    search_fields = ("address",)
    ordering = ("sort", "id")
    inlines = [ProjectPhotoInline]


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "number", "sort", "is_active")
    list_filter = ("is_active", "project")
    search_fields = ("number", "cadastral_number")
    ordering = ("project_id", "sort", "id")
    inlines = [BuildingPhotoInline]


@admin.register(ProjectPhoto)
class ProjectPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "caption", "sort", "is_active")
    list_filter = ("project", "is_active")
    list_select_related = ("project",)
    ordering = ("project_id", "sort", "id")


@admin.register(BuildingPhoto)
class BuildingPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "building", "caption", "sort", "is_active")
    list_filter = ("building", "is_active")
    list_select_related = ("building",)
    ordering = ("building_id", "sort", "id")


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


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "project", "down_payment_percent", "installment_months", "sort", "is_active")
    list_filter = ("is_active", "project")
    ordering = ("project_id", "sort", "id")


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id", "project", "area_start", "area_end",
        "payment_percent", "discount_percent", "is_duplex", "is_active",
    )
    list_filter = ("is_active", "is_duplex", "project")
    ordering = ("project_id", "sort", "id")


@admin.register(Calculation)
class CalculationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "apartment", "payment_percent", "discount_percent",
        "new_price_per_sqm", "new_total_price", "initial_fee", "monthly_payment",
    )
    list_filter = ("payment_percent", "is_active")
    search_fields = ("apartment__number",)
    ordering = ("apartment_id", "payment_percent_id")


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "floor", "old_price", "new_price", "changed_by", "created_at")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in PriceHistory._meta.fields)
