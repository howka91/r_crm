"""Objects models — package entry point.

Layout mirrors `apps.references.models`: one file per substantial model.
The hierarchy here is 4 levels — Project → Building → Section → Floor — with
Apartment arriving in phase 3.2. Each model is a FK chain: `on_delete=PROTECT`
by default so deleting a parent with children is always a deliberate act.

Re-exports so `from apps.objects.models import Project` keeps working, and so
Django's app-model discovery finds every model on `apps.objects.models`.
"""
from apps.objects.models.apartment import Apartment
from apps.objects.models.apartment_status_log import ApartmentStatusLog
from apps.objects.models.building import Building
from apps.objects.models.calculation import Calculation
from apps.objects.models.discount_rule import DiscountRule
from apps.objects.models.floor import Floor
from apps.objects.models.payment_plan import PaymentPlan
from apps.objects.models.price_history import PriceHistory
from apps.objects.models.project import Project
from apps.objects.models.section import Section

__all__ = [
    "Project",
    "Building",
    "Section",
    "Floor",
    "Apartment",
    "ApartmentStatusLog",
    "PaymentPlan",
    "DiscountRule",
    "Calculation",
    "PriceHistory",
]
