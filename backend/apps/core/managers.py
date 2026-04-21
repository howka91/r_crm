"""Reusable model managers."""
from __future__ import annotations

from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that filters out soft-deleted rows by default.

    Use `.with_inactive()` to include them.
    """

    def delete(self) -> tuple[int, dict[str, int]]:  # type: ignore[override]
        """Soft-delete: set `is_active=False`."""
        return self.update(is_active=False), {}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """Actually remove rows from DB."""
        return super().delete()

    def active(self) -> "SoftDeleteQuerySet":
        return self.filter(is_active=True)

    def inactive(self) -> "SoftDeleteQuerySet":
        return self.filter(is_active=False)


class SoftDeleteManager(models.Manager):
    """Default manager that returns only active rows.

    Models using this must have an `is_active: BooleanField`.
    """

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).active()

    def with_inactive(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)
