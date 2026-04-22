"""Custom model fields shared across apps.

- `I18nField`: JSON field constrained to shape `{"ru": str, "uz": str, "oz": str}`.
- `MoneyField`: Decimal with sane defaults for UZS amounts (max ~10^12 UZS).
- `AreaField`: Decimal for square metres.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

SUPPORTED_LANGS: tuple[str, ...] = ("ru", "uz", "oz")


def validate_i18n(value: Any) -> None:
    """Ensure value is a dict with all supported language keys as strings."""
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValidationError(_("I18n field must be a JSON object."))
    for lang in SUPPORTED_LANGS:
        if lang not in value:
            raise ValidationError(
                _("I18n field is missing language key: %(lang)s") % {"lang": lang},
            )
        if not isinstance(value[lang], str):
            raise ValidationError(
                _("I18n field value for %(lang)s must be a string.")
                % {"lang": lang},
            )


class I18nField(models.JSONField):
    """JSONField storing translations in a fixed shape {ru, uz, oz}.

    Default value is an empty string per language so the field is always well-formed.
    """

    description = _("Multilingual text (ru / uz latin / oz cyrillic)")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("default", empty_i18n)
        # Dedupe: Django's JSONField.deconstruct() may surface the validator
        # again on reload, and a bare .append() would accumulate duplicates.
        validators = list(kwargs.get("validators") or [])
        if validate_i18n not in validators:
            validators.append(validate_i18n)
        kwargs["validators"] = validators
        super().__init__(*args, **kwargs)


def empty_i18n() -> dict[str, str]:
    """Default factory for I18nField."""
    return {lang: "" for lang in SUPPORTED_LANGS}


class MoneyField(models.DecimalField):
    """Decimal field with defaults suitable for UZS amounts.

    Max 10^12 - 0.01 (i.e., up to 999,999,999,999.99). Two decimal places.
    """

    description = _("Decimal money amount (UZS by default)")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_digits", 14)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("default", Decimal("0.00"))
        super().__init__(*args, **kwargs)


class AreaField(models.DecimalField):
    """Decimal field for square metres. Up to 999999.99."""

    description = _("Area in square metres")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_digits", 8)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("default", Decimal("0.00"))
        super().__init__(*args, **kwargs)


class PercentField(models.DecimalField):
    """Percent value, 0.00 — 100.00."""

    description = _("Percent (0 — 100)")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_digits", 5)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("default", Decimal("0.00"))
        super().__init__(*args, **kwargs)
