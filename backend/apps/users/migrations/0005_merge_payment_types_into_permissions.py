"""Fold `Role.allowed_payment_types` into the `Role.permissions` tree.

Before: Role had two permission-ish fields — `permissions: {key: bool}` for
the main tree and `allowed_payment_types: list[str]` for bank/cash/barter
toggles. Dual modeling, two UIs, two validations.

After: the three toggles live in the tree as `finance.payment_types.bank`
/ `.cash` / `.barter`. This migration copies any legacy list values into
the JSON dict, then drops the list column.
"""
from __future__ import annotations

from django.db import migrations, models


def migrate_payment_types(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    for role in Role.objects.all():
        perms = dict(role.permissions or {})
        legacy = list(getattr(role, "allowed_payment_types", None) or [])
        for kind in ("bank", "cash", "barter"):
            key = f"finance.payment_types.{kind}"
            perms[key] = kind in legacy
        # Parent node must be True too (permission check cascades up); only
        # flip it on if at least one channel is enabled — otherwise leave
        # whatever the role already had at finance.payment_types.
        if any(kind in legacy for kind in ("bank", "cash", "barter")):
            perms["finance.payment_types"] = True
        role.permissions = perms
        role.save(update_fields=["permissions"])


def reverse_migrate(apps, schema_editor):
    # Best-effort reverse: rebuild the list from the dict values. Run only
    # when rolling back to the old code (which still expects the column).
    Role = apps.get_model("users", "Role")
    for role in Role.objects.all():
        perms = role.permissions or {}
        role.allowed_payment_types = [
            k for k in ("bank", "cash", "barter")
            if perms.get(f"finance.payment_types.{k}")
        ]
        role.save(update_fields=["allowed_payment_types"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_staff_login"),
    ]

    operations = [
        migrations.RunPython(migrate_payment_types, reverse_migrate),
        migrations.RemoveField(
            model_name="role",
            name="allowed_payment_types",
        ),
    ]
