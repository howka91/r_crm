"""References models — package entry point.

Models are split into one-file-per-model (for substantial models) and a single
`lookups.py` for the 13 simple LookupModel subclasses. The `__init__` re-exports
everything so existing imports — `from apps.references.models import Developer`
— keep working, and so Django's app-model discovery sees them as attributes of
the `apps.references.models` package.

Layout rule for the project:
  - `models.py` (single file) — for apps with 1–3 models.
  - `models/` package (one file per model) — for apps with 4+ models, or where
    lookups are grouped in a shared `lookups.py`.
See `frontend/ARCHITECTURE.md` for the equivalent front-end rule.
"""
from apps.references.models._validators import phone_validator
from apps.references.models.currency import Currency
from apps.references.models.developer import Developer
from apps.references.models.lookups import (
    ApartmentType,
    Badge,
    ConstructionStage,
    Decoration,
    HomeMaterial,
    Location,
    OccupiedBy,
    OutputWindows,
    PaymentInPercent,
    PaymentMethod,
    PremisesDecoration,
    Region,
    RoomType,
)
from apps.references.models.planning import Planning
from apps.references.models.sales_office import SalesOffice

# The ordered list of LookupModel subclasses. Used by serializers.py /
# views.py / urls.py to register each lookup without copy-pasting 13 blocks.
LOOKUP_MODELS = [
    ApartmentType,
    RoomType,
    ConstructionStage,
    Decoration,
    PremisesDecoration,
    HomeMaterial,
    OutputWindows,
    OccupiedBy,
    Badge,
    PaymentMethod,
    PaymentInPercent,
    Region,
    Location,
]

__all__ = [
    "phone_validator",
    "Developer",
    "SalesOffice",
    "Currency",
    "Planning",
    # Lookups
    "ApartmentType",
    "RoomType",
    "ConstructionStage",
    "Decoration",
    "PremisesDecoration",
    "HomeMaterial",
    "OutputWindows",
    "OccupiedBy",
    "Badge",
    "PaymentMethod",
    "PaymentInPercent",
    "Region",
    "Location",
    "LOOKUP_MODELS",
]
