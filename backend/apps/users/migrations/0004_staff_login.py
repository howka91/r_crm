"""Switch Staff auth from `email` to `login`.

Three-step schema change to stay safe on DBs with existing rows:

  1. Add `login` as nullable CharField, no unique yet.
  2. Data-migration: backfill `login` from `email` (the previous USERNAME_FIELD).
     If the email happens to collide across rows (shouldn't, email was unique),
     a numeric suffix is appended.
  3. Tighten `login` to NOT NULL + UNIQUE; relax `email` to blank-allowed and
     drop its unique constraint (email is now optional contact info).

No changes to `USERNAME_FIELD` are encoded at the migration level — Django
reads USERNAME_FIELD from the model class at runtime. That means the ALTER
happens when Django picks up the new `models.py`; migrations only shape the
DB columns.
"""
from __future__ import annotations

from django.db import migrations, models


def backfill_login(apps, schema_editor):
    Staff = apps.get_model("users", "Staff")
    seen: set[str] = set()
    for staff in Staff.objects.all().order_by("date_joined", "id"):
        base = (staff.email or "").strip() or f"user-{str(staff.id)[:8]}"
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}-{suffix}"
            suffix += 1
        seen.add(candidate)
        staff.login = candidate
        staff.save(update_fields=["login"])


def reverse_backfill(apps, schema_editor):
    # Nothing to undo at data-level — the column itself is removed when the
    # schema step is reversed.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_role_name"),
    ]

    operations = [
        # Step 1: add login as nullable — no db_index yet, the unique
        # constraint in step 3a creates its own implicit index (and the
        # `_like` helper index Postgres needs for prefix search). Emitting
        # db_index=True here would collide with step 3a on re-apply.
        migrations.AddField(
            model_name="staff",
            name="login",
            field=models.CharField(
                max_length=150,
                null=True,
                help_text="Короткий уникальный идентификатор для входа в CRM.",
                verbose_name="Логин",
            ),
        ),
        # Step 2: backfill from email.
        migrations.RunPython(backfill_login, reverse_backfill),
        # Step 3a: enforce NOT NULL + UNIQUE on login.
        migrations.AlterField(
            model_name="staff",
            name="login",
            field=models.CharField(
                max_length=150,
                unique=True,
                help_text="Короткий уникальный идентификатор для входа в CRM.",
                verbose_name="Логин",
            ),
        ),
        # Step 3b: drop unique on email + let it be blank.
        migrations.AlterField(
            model_name="staff",
            name="email",
            field=models.EmailField(
                blank=True,
                max_length=254,
                verbose_name="Email",
            ),
        ),
        # Re-sort Staff by login (matches the new Meta.ordering).
        migrations.AlterModelOptions(
            name="staff",
            options={
                "ordering": ["full_name", "login"],
                "verbose_name": "Сотрудник",
                "verbose_name_plural": "Сотрудники",
            },
        ),
    ]
