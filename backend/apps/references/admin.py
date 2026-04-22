"""Django admin for the references app.

Rich entities get custom admins; the 13 lookups share a single `LookupAdmin`
class registered via a loop.
"""
from __future__ import annotations

from django.contrib import admin

from apps.references.models import (
    LOOKUP_MODELS,
    Currency,
    Developer,
    SalesOffice,
)


# --- Rich entities ---------------------------------------------------------


@admin.register(Developer)
class DeveloperAdmin(admin.ModelAdmin):
    list_display = ("id", "_name_ru", "director", "inn", "phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("director", "inn", "bank_account")
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        (None, {"fields": ("name", "is_active")}),
        ("Контакты", {"fields": ("director", "address", "email", "phone")}),
        ("Банк / реквизиты", {
            "fields": ("bank_name", "bank_account", "inn", "nds", "oked"),
        }),
        ("Дополнительно", {"fields": ("extra",)}),
        ("Метаданные", {"fields": ("created_at", "modified_at")}),
    )

    @admin.display(description="Название (ru)")
    def _name_ru(self, obj: Developer) -> str:
        return (obj.name or {}).get("ru") or "—"


@admin.register(SalesOffice)
class SalesOfficeAdmin(admin.ModelAdmin):
    list_display = ("id", "_name_ru", "address", "phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("address",)
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        (None, {"fields": ("name", "is_active")}),
        ("Расположение", {"fields": ("address", "latitude", "longitude")}),
        ("Контакты / график", {"fields": ("phone", "work_start", "work_end", "photo")}),
        ("Метаданные", {"fields": ("created_at", "modified_at")}),
    )

    @admin.display(description="Название (ru)")
    def _name_ru(self, obj: SalesOffice) -> str:
        return (obj.name or {}).get("ru") or "—"


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "symbol", "_name_ru", "rate", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code",)
    readonly_fields = ("created_at", "modified_at")

    @admin.display(description="Название (ru)")
    def _name_ru(self, obj: Currency) -> str:
        return (obj.name or {}).get("ru") or "—"


# --- Simple lookups --------------------------------------------------------


class LookupAdmin(admin.ModelAdmin):
    """Shared admin for all LookupModel subclasses."""

    list_display = ("id", "_name_ru", "sort", "is_active")
    list_filter = ("is_active",)
    list_editable = ("sort", "is_active")
    readonly_fields = ("created_at", "modified_at")
    ordering = ("sort", "id")

    @admin.display(description="Название (ru)")
    def _name_ru(self, obj) -> str:
        return (obj.name or {}).get("ru") or "—"


for _model in LOOKUP_MODELS:
    admin.site.register(_model, LookupAdmin)
