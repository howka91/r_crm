"""django-filter sets for the contracts app."""
from __future__ import annotations

from django_filters import rest_framework as filters

from apps.contracts.models import Contract


class ContractFilterSet(filters.FilterSet):
    """ContractViewSet filter set.

    Replaces the old ``filterset_fields`` tuple so we can add ``payment_type``
    — a contract is matched if any of its non-soft-deleted payments uses the
    requested channel. Distinct keeps a contract from showing up multiple
    times when several of its payments match.
    """

    payment_type = filters.CharFilter(method="filter_by_payment_type")

    class Meta:
        model = Contract
        fields = (
            "is_active",
            "project",
            "apartment",
            "signer",
            "signer__client__status",
            "action",
            "is_signed",
            "is_paid",
            "is_mortgage",
        )

    def filter_by_payment_type(self, queryset, name, value):
        return queryset.filter(
            schedules__payments__payment_type=value,
            schedules__payments__is_active=True,
        ).distinct()
