"""Views for users: auth endpoints + Staff/Role CRUD ViewSets."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.permission_tree import PERMISSION_TREE
from apps.core.permissions import HasPermission
from apps.users.models import Role
from apps.users.serializers import (
    LoginSerializer,
    RoleSerializer,
    StaffSerializer,
)

Staff = get_user_model()


# --- Auth ------------------------------------------------------------------


class LoginView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        request=LoginSerializer,
        responses={200: OpenApiResponse(description="access + refresh + user")},
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RefreshView(TokenRefreshView):
    """Re-export simplejwt's refresh view under our URL."""

    permission_classes = (AllowAny,)
    authentication_classes = ()


class LogoutView(APIView):
    """Blacklist the caller's refresh token so it can't be used again."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request={"type": "object", "properties": {"refresh": {"type": "string"}}},
        responses={205: OpenApiResponse(description="Token blacklisted")},
    )
    def post(self, request: Request) -> Response:
        token_str = request.data.get("refresh")
        if not token_str:
            return Response(
                {"detail": "Поле 'refresh' обязательно."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token_str).blacklist()
        except TokenError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    """Return the current authenticated staff profile."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=StaffSerializer)
    def get(self, request: Request) -> Response:
        return Response(StaffSerializer(request.user, context={"request": request}).data)


# --- Permission tree ---------------------------------------------------------


class PermissionTreeView(APIView):
    """Return the full hardcoded permission tree (for role-editor UI)."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: OpenApiResponse(description="Permission tree")})
    def get(self, request: Request) -> Response:
        return Response({"tree": PERMISSION_TREE})


# --- CRUD --------------------------------------------------------------------


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by("code")
    serializer_class = RoleSerializer
    filterset_fields = ("is_active",)
    search_fields = ("code",)

    def get_permissions(self):
        action_map = {
            "list": "administration.roles.view",
            "retrieve": "administration.roles.view",
            "create": "administration.roles.create",
            "update": "administration.roles.edit",
            "partial_update": "administration.roles.edit",
            "destroy": "administration.roles.delete",
        }
        key = action_map.get(self.action)
        if key is None:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasPermission(key)]


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().select_related("role")
    serializer_class = StaffSerializer
    filterset_fields = ("is_active", "role", "language")
    search_fields = ("login", "email", "full_name", "phone_number")

    def get_permissions(self):
        action_map = {
            "list": "administration.users.view",
            "retrieve": "administration.users.view",
            "create": "administration.users.create",
            "update": "administration.users.edit",
            "partial_update": "administration.users.edit",
            "destroy": "administration.users.delete",
        }
        key = action_map.get(self.action)
        if key is None:
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasPermission(key)]

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request: Request, pk=None) -> Response:
        """Admin-initiated password reset. Requires `administration.users.edit`."""
        if not HasPermission("administration.users.edit").has_permission(request, self):
            return Response(status=status.HTTP_403_FORBIDDEN)
        new_password = request.data.get("new_password")
        if not new_password or len(new_password) < 8:
            return Response(
                {"detail": "Пароль должен быть минимум 8 символов."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        staff = self.get_object()
        staff.set_password(new_password)
        staff.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
