"""Serializers for auth, Staff, and Role."""
from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.permission_tree import all_permission_keys
from apps.users.models import Role, Staff


# --- Role -------------------------------------------------------------------


class RoleSerializer(serializers.ModelSerializer):
    # Both `code` and `name` are relaxed on input: `code` can be omitted and
    # we'll auto-generate from the Russian name; `name` accepts any subset
    # of {ru, uz, oz} and we fill missing translations from the ru value.
    code = serializers.SlugField(max_length=64, required=False, allow_blank=True)
    name = serializers.JSONField(required=False)

    class Meta:
        model = Role
        fields = [
            "id",
            "code",
            "name",
            "permissions",
            "is_active",
            "created_at",
            "modified_at",
        ]
        read_only_fields = ("id", "created_at", "modified_at")

    # --- Helpers ---

    _CYRILLIC_MAP = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }

    @classmethod
    def _slugify_cyrillic(cls, text: str) -> str:
        import re
        s = (text or "").strip().lower()
        out = []
        for ch in s:
            out.append(cls._CYRILLIC_MAP.get(ch, ch))
        slug = re.sub(r"[^a-z0-9]+", "-", "".join(out)).strip("-")
        return slug or "role"

    @classmethod
    def _next_free_code(cls, base: str, *, exclude_id: int | None = None) -> str:
        from apps.users.models import Role as _Role
        candidate = base
        suffix = 2
        qs = _Role.objects.all()
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        while qs.filter(code=candidate).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    # --- Validation ---

    def validate_name(self, value):
        """Accept partial i18n dicts; require at least a non-empty `ru`."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Должен быть объект {ru, uz, oz}.")
        ru = (value.get("ru") or "").strip()
        if not ru:
            raise serializers.ValidationError({"ru": "Название (RU) обязательно."})
        # Backfill uz/oz from ru when omitted — matches the UI simplification.
        return {
            "ru": ru,
            "uz": (value.get("uz") or "").strip() or ru,
            "oz": (value.get("oz") or "").strip() or ru,
        }

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

    # --- Create / Update hooks (auto-slugify code) ---

    def create(self, validated_data):
        code = (validated_data.get("code") or "").strip()
        if not code:
            base = self._slugify_cyrillic(validated_data["name"]["ru"])
            code = self._next_free_code(base)
        else:
            code = self._next_free_code(code)
        validated_data["code"] = code
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # If caller sends code="", treat as "keep current" — don't blank it.
        if "code" in validated_data and not (validated_data.get("code") or "").strip():
            validated_data.pop("code")
        elif "code" in validated_data:
            validated_data["code"] = self._next_free_code(
                validated_data["code"], exclude_id=instance.pk,
            )
        return super().update(instance, validated_data)


class RoleBriefSerializer(serializers.ModelSerializer):
    """Compact role representation embedded inside Staff responses."""

    class Meta:
        model = Role
        fields = ("id", "code", "name", "permissions")


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
    # Login length floor of 1 — "admin" / "1" should work. Uniqueness is on
    # the model.
    login = serializers.CharField(max_length=150)
    # Email is optional contact info, no auth role.
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, min_length=1)

    class Meta:
        model = Staff
        fields = (
            "id",
            "login",
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
    # `login` is the Staff username (USERNAME_FIELD). Email is contact info
    # only and has no auth role.
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            login=attrs["login"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError(
                {"detail": "Неверный логин или пароль."},
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
