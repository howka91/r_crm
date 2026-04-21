"""URL routes for the users app.

Mounted under `/api/v1/` by `conf.urls`.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.users.views import (
    LoginView,
    LogoutView,
    MeView,
    PermissionTreeView,
    RefreshView,
    RoleViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register("staff", StaffViewSet, basename="staff")
router.register("roles", RoleViewSet, basename="role")

urlpatterns = [
    # Auth
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    # Permissions
    path("permissions/tree/", PermissionTreeView.as_view(), name="permissions-tree"),
    # CRUD
    path("", include(router.urls)),
]
