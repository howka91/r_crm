"""Shared ViewSet mixins.

`ProtectedDestroyMixin` — converts a `ProtectedError` raised by
`instance.delete()` (caused by a `PROTECT` foreign key) into a 409 Conflict
response with a machine-readable payload, instead of letting it bubble up as
an uncaught 500.

Use on any ModelViewSet whose model is protected against child-deletion:

    class ProjectViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
        ...
"""
from __future__ import annotations

from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response


class ProtectedDestroyMixin:
    """Turn `ProtectedError` into a clean 409 response with details."""

    def perform_destroy(self, instance):  # type: ignore[override]
        try:
            instance.delete()
        except ProtectedError as exc:
            # exc.protected_objects is a set-like of the FKs that block delete.
            # Summarise by related model for a compact payload.
            counts: dict[str, int] = {}
            for obj in exc.protected_objects:
                label = obj._meta.label  # e.g. "objects.Building"
                counts[label] = counts.get(label, 0) + 1
            # Surface via a DRF response — `destroy()` default will call us and
            # then return 204; we need to abort the default flow.
            self._protected_response = Response(
                {
                    "detail": "Нельзя удалить: есть связанные записи.",
                    "blocked_by": counts,
                },
                status=status.HTTP_409_CONFLICT,
            )

    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        instance = self.get_object()
        self._protected_response = None
        self.perform_destroy(instance)
        if self._protected_response is not None:
            return self._protected_response
        return Response(status=status.HTTP_204_NO_CONTENT)
