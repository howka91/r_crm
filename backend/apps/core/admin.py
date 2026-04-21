from django.contrib import admin

from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "method", "path", "status_code", "ip_address")
    list_filter = ("method", "status_code", "created_at")
    search_fields = ("path", "ip_address", "actor__email")
    readonly_fields = (
        "created_at",
        "actor",
        "method",
        "path",
        "status_code",
        "ip_address",
        "user_agent",
        "payload",
        "response_summary",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # type: ignore[override]
        return False
