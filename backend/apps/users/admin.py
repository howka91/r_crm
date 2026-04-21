"""Django admin for users app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import Role, Staff


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "is_active", "created_at", "modified_at")
    list_filter = ("is_active",)
    search_fields = ("code",)
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        (None, {"fields": ("code", "name", "is_active")}),
        ("Права", {"fields": ("permissions", "allowed_payment_types")}),
        ("Метаданные", {"fields": ("created_at", "modified_at")}),
    )


@admin.register(Staff)
class StaffAdmin(DjangoUserAdmin):
    list_display = ("email", "full_name", "role", "is_active", "is_superuser")
    list_filter = ("is_active", "is_superuser", "role", "language")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личное", {"fields": ("full_name", "phone_number", "photo", "language", "theme")}),
        ("Права", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "role", "is_staff", "is_superuser"),
        }),
    )
    filter_horizontal = ("groups", "user_permissions")
