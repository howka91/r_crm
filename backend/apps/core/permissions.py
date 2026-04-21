"""Permission check primitives.

A role stores `permissions` as a **flat dict** `{dotted_key: bool}`:

    {
        "clients": True,
        "clients.view": True,
        "clients.create": False,
        "contracts.signed.view": True,
    }

Checking a key also checks every ancestor — if a parent module is disabled, all
its descendants are disabled regardless of their own flag. This matches the
architecture: "If a parent node is off — all children are unavailable too."

The canonical list of valid keys lives in `apps.core.permission_tree.PERMISSION_TREE`.
This module just consumes it for DRF permission enforcement.
"""
from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


def check(permissions: dict[str, Any] | None, dotted_key: str) -> bool:
    """Return True iff `dotted_key` and all its ancestors are True in `permissions`.

    A missing key is treated as False (deny-by-default).
    """
    if not permissions:
        return False
    parts = dotted_key.split(".")
    for i in range(1, len(parts) + 1):
        prefix = ".".join(parts[:i])
        if not permissions.get(prefix):
            return False
    return True


class HasPermission(BasePermission):
    """DRF permission: grant access iff the caller's role has `key` enabled.

    Usage:

        class ApartmentViewSet(ModelViewSet):
            permission_classes = [HasPermission("objects.apartments.view")]

    Superusers bypass this check.
    """

    message = "Недостаточно прав для этого действия."

    def __init__(self, key: str) -> None:
        self.key = key

    def __call__(self, *args, **kwargs):
        # DRF instantiates each class in permission_classes with no args. We were
        # already instantiated with the key; return self so DRF gets a usable
        # BasePermission instance.
        return self

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        role = getattr(user, "role", None)
        if role is None:
            return False
        return check(getattr(role, "permissions", None), self.key)
