"""DRF serializers for the references app.

Rich entities (Developer / SalesOffice / Currency) get their own serializer
class. The 13 simple lookups share a generic serializer built via the
`make_lookup_serializer(model)` factory — see bottom of this module.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.references.models import (
    Badge,
    Currency,
    Developer,
    Location,
    LOOKUP_MODELS,
    PaymentInPercent,
    SalesOffice,
)


class DeveloperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = (
            "id",
            "name",
            "director",
            "address",
            "email",
            "phone",
            "bank_name",
            "bank_account",
            "inn",
            "nds",
            "oked",
            "extra",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")


class SalesOfficeSerializer(serializers.ModelSerializer):
    # `photo` is a FileField — DRF serializes as an absolute URL when a request
    # is in context (ViewSet passes it automatically).
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = SalesOffice
        fields = (
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "work_start",
            "work_end",
            "phone",
            "photo",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = (
            "id",
            "code",
            "symbol",
            "name",
            "rate",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")

    def validate_code(self, value: str) -> str:
        # Frontend may send "usd" — model.save() normalizes, but reject junk
        # (non-letters, wrong length) at the edge.
        if not value.isalpha() or len(value) != 3:
            raise serializers.ValidationError(
                "Код должен состоять из 3 букв (ISO 4217).",
            )
        return value.upper()


# --- Lookups ---------------------------------------------------------------

# Fields that every LookupModel subclass exposes. Model-specific extras
# (Badge.color, Location.region, PaymentInPercent.percent) are appended below.
_LOOKUP_BASE_FIELDS = (
    "id",
    "name",
    "sort",
    "is_active",
    "created_at",
    "modified_at",
)

# Map of `lookup subclass -> tuple of extra field names`. Used by the factory
# to extend the base fields list.
_LOOKUP_EXTRA_FIELDS: dict[type, tuple[str, ...]] = {
    Badge: ("color",),
    Location: ("region",),
    PaymentInPercent: ("percent",),
}


def make_lookup_serializer(model_cls: type) -> type[serializers.ModelSerializer]:
    """Build a ModelSerializer subclass for the given LookupModel concrete class.

    All LookupModel subclasses have the same base shape; model-specific extras
    are surfaced via `_LOOKUP_EXTRA_FIELDS`. Register with the router under
    `/api/v1/{kebab-case-name}/`.
    """
    extras = _LOOKUP_EXTRA_FIELDS.get(model_cls, ())
    fields = _LOOKUP_BASE_FIELDS + extras

    meta = type(
        "Meta",
        (),
        {
            "model": model_cls,
            "fields": fields,
            "read_only_fields": ("id", "created_at", "modified_at"),
        },
    )
    return type(
        f"{model_cls.__name__}Serializer",
        (serializers.ModelSerializer,),
        {"Meta": meta},
    )


# Eagerly build one serializer per lookup model so other modules
# (views, admin) can import them by dict key.
LOOKUP_SERIALIZERS: dict[type, type[serializers.ModelSerializer]] = {
    model: make_lookup_serializer(model) for model in LOOKUP_MODELS
}
