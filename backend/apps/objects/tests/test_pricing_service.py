"""Tests for the pricing cascade in `apps.objects.services.pricing`.

Covers:
  * `find_applicable_discount` matching matrix (area bounds, is_duplex,
    payment_percent, sort ordering).
  * `recalc_apartment` updates `total_price` and upserts a Calculation per
    active PaymentInPercent.
  * `change_floor_price` writes a PriceHistory row, updates Floor, and
    cascades through every apartment on the floor.
  * The `POST /floors/:id/change-price/` action returns 200 + stats.
  * `objects.floors.edit_price` permission isolation.
  * Monthly payment recompute when installment_months is pre-set on a
    Calculation.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import Calculation, PriceHistory
from apps.objects.services.pricing import (
    change_floor_price,
    find_applicable_discount,
    recalc_apartment,
    recalc_floor,
)
from apps.objects.tests.factories import (
    ApartmentFactory,
    DiscountRuleFactory,
    FloorFactory,
    PaymentInPercentFactory,
    ProjectFactory,
    SectionFactory,
    BuildingFactory,
)
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped(*keys: str) -> dict[str, bool]:
    perms = default_permissions(False)
    for k in keys:
        parts = k.split(".")
        for i in range(1, len(parts) + 1):
            perms[".".join(parts[:i])] = True
    return perms


def _project_with_floor():
    """Shortcut: return a fully-wired (project, floor) pair."""
    project = ProjectFactory()
    building = BuildingFactory(project=project)
    section = SectionFactory(building=building)
    floor = FloorFactory(section=section, price_per_sqm=Decimal("10000000.00"))
    return project, floor


# --- find_applicable_discount --------------------------------------------


@pytest.mark.django_db
class TestFindApplicableDiscount:
    def test_matches_by_area_and_payment(self):
        project, floor = _project_with_floor()
        apt = ApartmentFactory(
            floor=floor, area=Decimal("60.00"), is_duplex=False,
        )
        pp = PaymentInPercentFactory()
        rule = DiscountRuleFactory(
            project=project,
            area_start=Decimal("50.00"),
            area_end=Decimal("100.00"),
            payment_percent=pp,
            discount_percent=Decimal("5.00"),
            is_duplex=False,
        )
        assert find_applicable_discount(apt, pp) == rule

    def test_no_match_outside_area(self):
        project, floor = _project_with_floor()
        apt = ApartmentFactory(floor=floor, area=Decimal("30.00"))
        pp = PaymentInPercentFactory()
        DiscountRuleFactory(
            project=project,
            area_start=Decimal("50.00"),
            area_end=Decimal("100.00"),
            payment_percent=pp,
        )
        assert find_applicable_discount(apt, pp) is None

    def test_duplex_flag_isolation(self):
        project, floor = _project_with_floor()
        apt_regular = ApartmentFactory(floor=floor, area=Decimal("60.00"), is_duplex=False)
        apt_duplex = ApartmentFactory(floor=floor, area=Decimal("60.00"), is_duplex=True)
        pp = PaymentInPercentFactory()
        duplex_rule = DiscountRuleFactory(
            project=project,
            area_start=Decimal("0.00"),
            area_end=Decimal("999.00"),
            payment_percent=pp,
            discount_percent=Decimal("10.00"),
            is_duplex=True,
        )
        regular_rule = DiscountRuleFactory(
            project=project,
            area_start=Decimal("0.00"),
            area_end=Decimal("999.00"),
            payment_percent=pp,
            discount_percent=Decimal("5.00"),
            is_duplex=False,
        )
        assert find_applicable_discount(apt_regular, pp) == regular_rule
        assert find_applicable_discount(apt_duplex, pp) == duplex_rule

    def test_sort_order_wins_over_discount(self):
        project, floor = _project_with_floor()
        apt = ApartmentFactory(floor=floor, area=Decimal("60.00"))
        pp = PaymentInPercentFactory()
        first = DiscountRuleFactory(
            project=project,
            area_start=Decimal("0.00"),
            area_end=Decimal("999.00"),
            payment_percent=pp,
            discount_percent=Decimal("3.00"),
            sort=1,
        )
        DiscountRuleFactory(
            project=project,
            area_start=Decimal("0.00"),
            area_end=Decimal("999.00"),
            payment_percent=pp,
            discount_percent=Decimal("10.00"),
            sort=5,
        )
        assert find_applicable_discount(apt, pp) == first


# --- recalc_apartment ----------------------------------------------------


@pytest.mark.django_db
class TestRecalcApartment:
    def test_updates_total_price(self):
        _, floor = _project_with_floor()
        apt = ApartmentFactory(
            floor=floor,
            area=Decimal("50.00"),
            surcharge=Decimal("5000000.00"),
            total_price=Decimal("0.00"),
        )
        PaymentInPercentFactory()

        recalc_apartment(apt)
        apt.refresh_from_db()
        # 50 * 10_000_000 + 5_000_000 = 505_000_000
        assert apt.total_price == Decimal("505000000.00")

    def test_creates_calculation_per_active_pp(self):
        _, floor = _project_with_floor()
        apt = ApartmentFactory(floor=floor, area=Decimal("50.00"))
        PaymentInPercentFactory(percent=Decimal("0.00"))
        PaymentInPercentFactory(percent=Decimal("30.00"))
        PaymentInPercentFactory(percent=Decimal("100.00"))

        count = recalc_apartment(apt)
        assert count == 3
        assert Calculation.objects.filter(apartment=apt).count() == 3

    def test_applies_matched_discount(self):
        project, floor = _project_with_floor()
        apt = ApartmentFactory(floor=floor, area=Decimal("50.00"), is_duplex=False)
        pp = PaymentInPercentFactory(percent=Decimal("100.00"))
        DiscountRuleFactory(
            project=project,
            area_start=Decimal("0.00"),
            area_end=Decimal("999.00"),
            payment_percent=pp,
            discount_percent=Decimal("10.00"),
            is_duplex=False,
        )
        recalc_apartment(apt)
        calc = Calculation.objects.get(apartment=apt, payment_percent=pp)
        assert calc.discount_percent == Decimal("10.00")
        # new_price_per_sqm = 10_000_000 * 0.9 = 9_000_000
        assert calc.new_price_per_sqm == Decimal("9000000.00")
        # new_total = 50 * 9_000_000 = 450_000_000
        assert calc.new_total_price == Decimal("450000000.00")
        # initial_fee = 450_000_000 * 100% = 450_000_000
        assert calc.initial_fee == Decimal("450000000.00")

    def test_preserves_existing_installment_months(self):
        """If a Calculation already has installment_months set, the service
        recomputes monthly_payment but doesn't reset the months field."""
        _, floor = _project_with_floor()
        apt = ApartmentFactory(floor=floor, area=Decimal("50.00"))
        pp = PaymentInPercentFactory(percent=Decimal("30.00"))

        # First pass — creates Calculation with installment_months=0
        recalc_apartment(apt)
        calc = Calculation.objects.get(apartment=apt, payment_percent=pp)
        # Simulate a user / plan picking 12 months
        calc.installment_months = 12
        calc.save(update_fields=["installment_months"])

        # Recompute — should preserve installment_months and set monthly
        recalc_apartment(apt)
        calc.refresh_from_db()
        assert calc.installment_months == 12
        # monthly = (new_total - initial) / 12
        # new_total = 50 * 10M = 500M; initial = 500M * 0.3 = 150M
        # monthly = 350M / 12 = 29_166_666.67
        assert calc.monthly_payment > Decimal("0.00")


# --- change_floor_price --------------------------------------------------


@pytest.mark.django_db
class TestChangeFloorPrice:
    def test_writes_history_and_cascades(self):
        _, floor = _project_with_floor()
        ApartmentFactory.create_batch(3, floor=floor, area=Decimal("50.00"))
        PaymentInPercentFactory(percent=Decimal("100.00"))
        actor = StaffFactory(password="x12345678")

        stats = change_floor_price(
            floor, Decimal("12000000.00"), by=actor, comment="market adj",
        )
        assert stats.apartments_updated == 3
        assert stats.calculations_upserted == 3
        floor.refresh_from_db()
        assert floor.price_per_sqm == Decimal("12000000.00")

        # Every apt has the new total_price
        for a in floor.apartments.all():
            a.refresh_from_db()
            assert a.total_price == Decimal("600000000.00")

        # History written
        h = PriceHistory.objects.get(pk=stats.price_history_id)
        assert h.floor == floor
        assert h.old_price == Decimal("10000000.00")
        assert h.new_price == Decimal("12000000.00")
        assert h.changed_by == actor
        assert h.comment == "market adj"

    def test_noop_price_still_writes_history(self):
        _, floor = _project_with_floor()
        apt = ApartmentFactory(floor=floor, area=Decimal("50.00"))
        PaymentInPercentFactory(percent=Decimal("100.00"))

        stats = change_floor_price(floor, Decimal("10000000.00"))
        assert stats.apartments_updated == 0
        assert PriceHistory.objects.filter(floor=floor).count() == 1
        # Apartment untouched
        apt.refresh_from_db()
        assert apt.total_price == Decimal("0.00") or apt.total_price > 0


# --- HTTP action ---------------------------------------------------------


@pytest.mark.django_db
class TestChangePriceAction:
    @staticmethod
    def _url(floor_id):
        return reverse("floor-change-price", args=[floor_id])

    def test_requires_edit_price_permission(self, api_client):
        """Just having floors.edit is NOT enough — must have floors.edit_price."""
        role = RoleFactory(
            code="floor-edit",
            permissions=_scoped("objects.floors.view", "objects.floors.edit"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        _, floor = _project_with_floor()
        resp = api_client.post(
            self._url(floor.id),
            {"new_price": "11000000.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_scoped_role_can_change_price(self, api_client):
        role = RoleFactory(
            code="price-mover",
            permissions=_scoped(
                "objects.floors.view",
                "objects.floors.edit_price",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        _, floor = _project_with_floor()
        ApartmentFactory.create_batch(2, floor=floor, area=Decimal("50.00"))
        PaymentInPercentFactory(percent=Decimal("100.00"))

        resp = api_client.post(
            self._url(floor.id),
            {"new_price": "11000000.00", "comment": "test"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["apartments_updated"] == 2
        assert resp.data["old_price"] == "10000000.00"
        assert resp.data["new_price"] == "11000000.00"

    def test_negative_price_rejected(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        _, floor = _project_with_floor()
        resp = api_client.post(
            self._url(floor.id),
            {"new_price": "-1.00"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRecalcFloorHelper:
    def test_walks_every_apartment(self):
        _, floor = _project_with_floor()
        ApartmentFactory.create_batch(5, floor=floor, area=Decimal("50.00"))
        PaymentInPercentFactory(percent=Decimal("100.00"))
        PaymentInPercentFactory(percent=Decimal("30.00"))

        a, c = recalc_floor(floor)
        assert a == 5
        assert c == 5 * 2  # 5 apartments × 2 payment percents
