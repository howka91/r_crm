"""Serializers for auth, Staff, and Role."""
from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.permission_tree import all_permission_keys
from apps.users.models import PaymentType, Role, Staff


# --- Role -------------------------------------------------------------------


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = [
            "id",
            "code",
            "name",
            "permissions",
            "allowed_payment_types",
            "is_active",
            "created_at",
            "modified_at",
        ]
        read_only_fields = ("id", "created_at", "modified_at")

    def validate_allowed_payment_types(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Должен быть список.")
        valid = {t.value for t in PaymentType}
        invalid = [v for v in value if v not in valid]
        if invalid:
            raise serializers.ValidationError(
                f"Недопустимые значения: {invalid}. Разрешены: {sorted(valid)}."
            )
        return value

    def validate_permissions(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Должен быть объект.")
        allowed = set(all_permission_keys())
        unknown = [k for k in value.keys() if k not in allowed]
        if unknown:
            raise serializers.ValidationError(
                f"Неизвестные ключи прав: {unknown[:5]}"
                + ("…" if len(unknown) > 5 else "")
            )
        non_bool = [k for k, v in value.items() if not isinstance(v, bool)]
        if non_bool:
            raise serializers.ValidationError(
                f"Значения должны быть bool: {non_bool[:5]}"
            )
        return value


class RoleBriefSerializer(serializers.ModelSerializer):
    """Compact role representation embedded inside Staff responses."""

    class Meta:
        model = Role
        fields = ("id", "code", "name", "permissions", "allowed_payment_types")


# --- Staff ------------------------------------------------------------------


class StaffSerializer(serializers.ModelSerializer):
    role = RoleBriefSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.filter(is_active=True),
        source="role",
        write_only=True,
        required=False,
        allow_null=True,
    )
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = Staff
        fields = (
            "id",
            "email",
            "full_name",
            "phone_number",
            "language",
            "theme",
            "photo",
            "is_active",
            "is_superuser",
            "role",
            "role_id",
            "password",
            "date_joined",
            "last_login",
        )
        read_only_fields = ("id", "date_joined", "last_login", "is_superuser")

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Пароль обязателен при создании."})
        staff = Staff.objects.create_user(password=password, **validated_data)
        return staff

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# --- Auth -------------------------------------------------------------------


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError(
                {"detail": "Неверный email или пароль."},
                code="authentication_failed",
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Учётная запись отключена."},
                code="inactive",
            )

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": StaffSerializer(user, context=self.context).data,
        }
