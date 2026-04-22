"""Shared abstract models and the AuditLog model."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import I18nField
from apps.core.managers import SoftDeleteManager


class TimeStampedModel(models.Model):
    """Abstract base with created_at / modified_at."""

    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    modified_at = models.DateTimeField(_("Изменено"), auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel):
    """Abstract base: TimeStampedModel + soft-delete flag + custom manager.

    All business models inherit from this unless there's a strong reason not to.
    """

    is_active = models.BooleanField(_("Активен"), default=True, db_index=True)

    # Default manager hides soft-deleted rows; `all_objects` sees everything.
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        self.is_active = False
        self.save(update_fields=["is_active", "modified_at"])

    def restore(self) -> None:
        self.is_active = True
        self.save(update_fields=["is_active", "modified_at"])


class LookupModel(BaseModel):
    """Abstract base for simple reference tables: multilingual name + sort order.

    Thirteen `references.*` lookups share this shape (ApartmentType, RoomType,
    ConstructionStage, Decoration, PremisesDecoration, HomeMaterial, OutputWindows,
    OccupiedBy, Badge, PaymentMethod, PaymentInPercent, Region, Location). Each
    subclass only needs its own `Meta.verbose_name` / `Meta.verbose_name_plural`.
    """

    name = I18nField(verbose_name=_("Название"))
    sort = models.PositiveSmallIntegerField(
        _("Порядок"), default=0, db_index=True,
        help_text=_("Чем меньше — тем выше в списке"),
    )

    class Meta:
        abstract = True
        ordering = ["sort", "id"]

    def __str__(self) -> str:
        if isinstance(self.name, dict):
            return self.name.get("ru") or self.name.get("uz") or f"#{self.pk}"
        return str(self.name)


class AuditLog(models.Model):
    """Every state-changing HTTP request is logged here.

    Populated by `apps.core.middleware.AuditLogMiddleware`.
    """

    class Method(models.TextChoices):
        POST = "POST", "POST"
        PUT = "PUT", "PUT"
        PATCH = "PATCH", "PATCH"
        DELETE = "DELETE", "DELETE"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("Кто"),
    )
    method = models.CharField(
        _("Метод"), max_length=8, choices=Method.choices, db_index=True
    )
    path = models.CharField(_("Путь"), max_length=512, db_index=True)
    status_code = models.PositiveSmallIntegerField(_("HTTP статус"))
    ip_address = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    user_agent = models.CharField(_("User-Agent"), max_length=512, blank=True)
    payload = models.JSONField(_("Тело запроса"), default=dict, blank=True)
    response_summary = models.JSONField(_("Ответ (обрезка)"), default=dict, blank=True)
    created_at = models.DateTimeField(_("Когда"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Запись аудита")
        verbose_name_plural = _("Журнал аудита")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["path", "-created_at"]),
        ]

    def __str__(self) -> str:
        actor = self.actor_id or "anon"
        return f"[{self.method}] {self.path} → {self.status_code} (actor={actor})"
