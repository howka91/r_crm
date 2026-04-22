"""Shared validators for references models."""
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

UZ_PHONE_REGEX = r"^\+?998\d{9}$"

phone_validator = RegexValidator(
    regex=UZ_PHONE_REGEX,
    message=_("Телефон должен быть в формате +998XXXXXXXXX."),
)
