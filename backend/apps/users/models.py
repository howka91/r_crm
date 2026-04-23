"""Users domain — Staff (operator account) and Role (permission bundle)."""
from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.permission_tree import default_permissions

# --- Validators -----------------------------------------------------------

UZ_PHONE_REGEX = r"^\+?998\d{9}$"

phone_validator = RegexValidator(
    regex=UZ_PHONE_REGEX,
    message=_("Телефон должен быть в формате +998XXXXXXXXX."),
)


# --- Role ------------------------------------------------------------------


class PaymentType(models.TextChoices):
    """Mirror of old `Role.is_payment_bank/cash/barter`, now as an enum list
    stored inside `Role.allowed_payment_types` JSON."""

    BANK = "bank", _("Банк")
    CASH = "cash", _("Наличные")
    BARTER = "barter", _("Бартер")


class Role(models.Model):
    """A named bundle of permissions that can be assigned to one or more Staff.

    `permissions` is a flat `{dotted_key: bool}` dict whose keys must all appear
    in `apps.core.permission_tree.PERMISSION_TREE`. See `apps.core.permissions`
    for check semantics (parent-off-disables-children).
    """

    name = I18nField(verbose_name=_("Название"))
    # Short, unique, latin-only code for the role (used in logs, URLs).
    code = models.SlugField(_("Код"), max_length=64, unique=True)
    permissions = models.JSONField(_("Разрешения"), default=dict)
    allowed_payment_types = models.JSONField(
        _("Разрешённые типы оплаты"),
        default=list,
        help_text=_("Список: bank / cash / barter"),
    )
    is_active = models.BooleanField(_("Активна"), default=True, db_index=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    modified_at = models.DateTimeField(_("Изменено"), auto_now=True)

    class Meta:
        verbose_name = _("Роль")
        verbose_name_plural = _("Роли")
        ordering = ["code"]

    def __str__(self) -> str:
        # Prefer ru label, fall back to code.
        if isinstance(self.name, dict):
            return self.name.get("ru") or self.name.get("uz") or self.code
        return self.code

    def save(self, *args, **kwargs):
        # Make sure permissions dict has every tree key defined — fill missing
        # keys with False so a role always has a complete map.
        defaults = default_permissions(False)
        defaults.update(self.permissions or {})
        self.permissions = defaults
        super().save(*args, **kwargs)


# --- Staff -----------------------------------------------------------------


class Language(models.TextChoices):
    RU = "ru", "Русский"
    UZ = "uz", "Oʻzbekcha"
    OZ = "oz", "Ўзбекча"


class Theme(models.TextChoices):
    LIGHT = "light", _("Светлая")
    DARK = "dark", _("Тёмная")


class StaffManager(BaseUserManager):
    """Login-based auth — `login` is USERNAME_FIELD, `email` is optional contact."""

    use_in_migrations = True

    def _create_user(self, login: str, password: str | None, **extra_fields):
        if not login:
            raise ValueError("Login is required")
        # Normalise any stray email-shaped input, but leave plain logins alone.
        email = extra_fields.get("email") or ""
        if email:
            extra_fields["email"] = self.normalize_email(email)
        user = self.model(login=login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, login: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(login, password, **extra_fields)

    def create_superuser(self, login: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(login, password, **extra_fields)


class Staff(AbstractUser):
    """CRM operator / employee account.

    UUID primary key per architecture (Staff is the only model to use UUIDs;
    everything else uses BigAutoField).
    """

    # Drop default username; we authenticate by email.
    username = None
    first_name = None
    last_name = None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    login = models.CharField(
        _("Логин"),
        max_length=150,
        unique=True,  # unique=True implies an index; db_index=True would dupe
        help_text=_("Короткий уникальный идентификатор для входа в CRM."),
    )
    email = models.EmailField(_("Email"), blank=True)
    full_name = models.CharField(_("ФИО"), max_length=255, blank=True)
    phone_number = models.CharField(
        _("Телефон"),
        max_length=13,
        blank=True,
        validators=[phone_validator],
    )
    language = models.CharField(
        _("Язык интерфейса"),
        max_length=2,
        choices=Language.choices,
        default=Language.RU,
    )
    theme = models.CharField(
        _("Тема"),
        max_length=5,
        choices=Theme.choices,
        default=Theme.LIGHT,
    )
    photo = models.ImageField(
        _("Фото"),
        upload_to="staff/photos/",
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        Role,
        verbose_name=_("Роль"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="staff",
    )

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS: list[str] = []

    objects = StaffManager()

    class Meta:
        verbose_name = _("Сотрудник")
        verbose_name_plural = _("Сотрудники")
        ordering = ["full_name", "login"]

    def __str__(self) -> str:
        return self.full_name or self.login
