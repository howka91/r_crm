"""Admin registrations for the contracts app."""
from __future__ import annotations

from django.contrib import admin

from apps.contracts.models import (
    Contract,
    ContractTemplate,
    Payment,
    PaymentSchedule,
)


class PaymentScheduleInline(admin.TabularInline):
    model = PaymentSchedule
    extra = 0
    fields = ("due_date", "amount", "paid_amount", "status")
    readonly_fields = ()
    show_change_link = True


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contract_number",
        "project",
        "apartment",
        "signer",
        "action",
        "is_signed",
        "is_paid",
        "total_amount",
        "date",
    )
    list_filter = ("action", "is_signed", "is_paid", "is_mortgage", "project")
    search_fields = ("contract_number", "related_person", "description")
    autocomplete_fields = ("project", "apartment", "calculation", "signer", "author")
    filter_horizontal = ("payment_methods",)
    inlines = [PaymentScheduleInline]
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        (None, {
            "fields": (
                "project", "apartment", "calculation", "signer", "author",
                "contract_number", "date", "send_date", "description",
            ),
        }),
        ("Суммы и способы оплаты", {
            "fields": ("total_amount", "down_payment", "payment_methods"),
        }),
        ("Workflow", {
            "fields": ("action", "is_signed", "is_paid", "is_mortgage"),
        }),
        ("Документ / snapshot", {
            "fields": ("requisite", "document", "old", "file", "qr", "related_person"),
            "classes": ("collapse",),
        }),
        ("Служебное", {
            "fields": ("is_active", "created_at", "modified_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "is_active", "modified_at")
    list_filter = ("is_active",)
    search_fields = ("title",)
    autocomplete_fields = ("author",)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("paid_at", "amount", "payment_type", "receipt_number", "recorded_by")
    autocomplete_fields = ("recorded_by",)


@admin.register(PaymentSchedule)
class PaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "contract", "due_date", "amount", "paid_amount", "status")
    list_filter = ("status",)
    search_fields = ("contract__contract_number",)
    autocomplete_fields = ("contract",)
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "schedule", "paid_at", "amount", "payment_type",
        "receipt_number", "recorded_by",
    )
    list_filter = ("payment_type",)
    search_fields = ("receipt_number", "comment")
    autocomplete_fields = ("schedule", "recorded_by")
