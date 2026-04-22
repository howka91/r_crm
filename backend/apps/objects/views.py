"""DRF viewsets for the objects app.

Pattern mirrors `apps.references.views`: each ViewSet gets its own permission
base via `_permissions_for(base, action)`. Custom `@action`s (e.g. `book` on
ApartmentViewSet in phase 3.2) carry their own permission gates.

`floor.edit_price` is a dedicated extra permission (see permission_tree) —
not enforced here yet; phase 3.3 ties it to the explicit price-change action
on FloorViewSet.
"""
from __future__ import annotations

from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import ProtectedDestroyMixin
from apps.core.permissions import HasPermission, check as check_permission
from apps.objects.models import (
    Apartment,
    ApartmentStatusLog,
    Building,
    Calculation,
    DiscountRule,
    Floor,
    PaymentPlan,
    PriceHistory,
    Project,
    Section,
)
from apps.objects.serializers import (
    ApartmentSerializer,
    ApartmentStatusLogSerializer,
    BookApartmentInputSerializer,
    BuildingSerializer,
    CalculationSerializer,
    ChangeFloorPriceInputSerializer,
    ChangeStatusInputSerializer,
    DiscountRuleSerializer,
    FloorSerializer,
    PaymentPlanSerializer,
    PriceHistorySerializer,
    ProjectSerializer,
    ReleaseApartmentInputSerializer,
    SectionSerializer,
)
from apps.objects.services.apartments import (
    InvalidStatusTransition,
    change_status,
)
from apps.objects.services.booking import (
    ApartmentNotBookable,
    ApartmentNotReleasable,
    book_apartment,
    release_booking,
)
from apps.objects.services.pricing import change_floor_price, recalc_apartment

_ACTION_SUFFIX: dict[str, str] = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


def _permissions_for(base: str, action: str | None) -> list:
    suffix = _ACTION_SUFFIX.get(action or "")
    if suffix is None:
        return [IsAuthenticated()]
    return [IsAuthenticated(), HasPermission(f"{base}.{suffix}")]


class ProjectViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Project.objects.select_related("developer").all()
    serializer_class = ProjectSerializer
    filterset_fields = ("is_active", "developer")
    search_fields = ("address",)

    def get_permissions(self):
        return _permissions_for("objects.projects", self.action)


class BuildingViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Building.objects.select_related("project").all()
    serializer_class = BuildingSerializer
    filterset_fields = ("is_active", "project")
    search_fields = ("number", "cadastral_number")

    def get_permissions(self):
        return _permissions_for("objects.buildings", self.action)


class SectionViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Section.objects.select_related("building", "building__project").all()
    serializer_class = SectionSerializer
    filterset_fields = ("is_active", "building")

    def get_permissions(self):
        return _permissions_for("objects.sections", self.action)


class FloorViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Floor.objects.select_related("section", "section__building").all()
    serializer_class = FloorSerializer
    filterset_fields = ("is_active", "section")

    def get_permissions(self):
        # `change_price` has its own permission so the right to move prices
        # can be separated from generic floor editing.
        if self.action == "change_price":
            return [
                IsAuthenticated(),
                HasPermission("objects.floors.edit_price"),
            ]
        return _permissions_for("objects.floors", self.action)

    @action(detail=True, methods=["post"], url_path="change-price")
    def change_price(self, request: Request, pk: str | None = None) -> Response:
        """Cascade-aware price change: writes a PriceHistory row and
        recomputes every apartment's total_price + calculations on this
        floor, all in one transaction via services.pricing.change_floor_price.
        """
        floor: Floor = self.get_object()
        payload = ChangeFloorPriceInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        stats = change_floor_price(
            floor,
            payload.validated_data["new_price"],
            by=request.user if request.user.is_authenticated else None,
            comment=payload.validated_data.get("comment", ""),
        )
        floor.refresh_from_db()
        return Response(
            {
                "floor": FloorSerializer(floor).data,
                "old_price": str(stats.old_price),
                "new_price": str(stats.new_price),
                "apartments_updated": stats.apartments_updated,
                "calculations_upserted": stats.calculations_upserted,
                "price_history_id": stats.price_history_id,
            },
            status=http_status.HTTP_200_OK,
        )


class ApartmentViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = (
        Apartment.objects
        .select_related("floor", "floor__section", "floor__section__building")
        .prefetch_related("characteristics")
        .all()
    )
    serializer_class = ApartmentSerializer
    filterset_fields = ("is_active", "floor", "status")
    search_fields = ("number",)

    def get_permissions(self):
        # The custom `change_status` action carries its own permission key
        # (`objects.apartments.change_status`) — distinct from the standard
        # edit flow so roles can separate "can edit apartment metadata" from
        # "can move apartment through the sales pipeline".
        action_perms = {
            "change_status": "objects.apartments.change_status",
            "book": "objects.apartments.book",
            "release": "objects.apartments.change_status",
            "recalc": "objects.apartments.edit",
        }
        perm = action_perms.get(self.action or "")
        if perm:
            return [IsAuthenticated(), HasPermission(perm)]
        # CRUD falls back to the standard map, mirroring the rest of the app.
        return _permissions_for("objects.apartments", self.action)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request: Request, pk: str | None = None) -> Response:
        """Move the apartment through the status workflow.

        Calls `services.apartments.change_status` (the single source of truth
        for legal transitions). Returns the updated apartment plus the id of
        the log row so the client can refetch the log if needed.
        """
        apt: Apartment = self.get_object()
        payload = ChangeStatusInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            result = change_status(
                apt,
                payload.validated_data["new_status"],
                by=request.user if request.user.is_authenticated else None,
                comment=payload.validated_data.get("comment", ""),
            )
        except InvalidStatusTransition as e:
            return Response(
                {"detail": str(e), "code": "invalid_transition"},
                status=http_status.HTTP_409_CONFLICT,
            )
        apt.refresh_from_db()
        return Response(
            {
                "apartment": ApartmentSerializer(apt).data,
                "log_id": result.log_id,
            },
            status=http_status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="book")
    def book(self, request: Request, pk: str | None = None) -> Response:
        """Reserve the apartment for `duration_days`. VIP booking requires
        `objects.apartments.book_vip` on top of `objects.apartments.book` —
        enforced by a second check inside the handler when vip=True.
        """
        apt: Apartment = self.get_object()
        payload = BookApartmentInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        vip = payload.validated_data.get("vip", False)
        if vip and not request.user.is_superuser:
            role = getattr(request.user, "role", None)
            if not check_permission(
                getattr(role, "permissions", None),
                "objects.apartments.book_vip",
            ):
                return Response(
                    {"detail": "Требуется разрешение на бронь руководства."},
                    status=http_status.HTTP_403_FORBIDDEN,
                )

        try:
            result = book_apartment(
                apt,
                payload.validated_data["duration_days"],
                by=request.user if request.user.is_authenticated else None,
                comment=payload.validated_data.get("comment", ""),
                vip=vip,
            )
        except ApartmentNotBookable as e:
            return Response(
                {"detail": str(e), "code": "not_bookable"},
                status=http_status.HTTP_409_CONFLICT,
            )
        apt.refresh_from_db()
        return Response(
            {
                "apartment": ApartmentSerializer(apt).data,
                "booking_expires_at": result.booking_expires_at,
                "log_id": result.log_id,
            },
            status=http_status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="recalc")
    def recalc(self, request: Request, pk: str | None = None) -> Response:
        """Force a pricing recalc on a single apartment.

        Useful when: area changed, a new PaymentInPercent was added, or a
        discount rule was edited — the user wants to refresh the price matrix
        without waiting for a floor-price change. Gated by the standard edit
        permission (same as editing the apartment).
        """
        apt: Apartment = self.get_object()
        touched = recalc_apartment(apt)
        apt.refresh_from_db()
        return Response(
            {
                "apartment": ApartmentSerializer(apt).data,
                "calculations_upserted": touched,
            },
            status=http_status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="release")
    def release(self, request: Request, pk: str | None = None) -> Response:
        """Undo a booking — back to free, clears `booking_expires_at`."""
        apt: Apartment = self.get_object()
        payload = ReleaseApartmentInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            result = release_booking(
                apt,
                by=request.user if request.user.is_authenticated else None,
                comment=payload.validated_data.get("comment", ""),
            )
        except ApartmentNotReleasable as e:
            return Response(
                {"detail": str(e), "code": "not_releasable"},
                status=http_status.HTTP_409_CONFLICT,
            )
        apt.refresh_from_db()
        return Response(
            {
                "apartment": ApartmentSerializer(apt).data,
                "log_id": result.log_id,
            },
            status=http_status.HTTP_200_OK,
        )


class ApartmentStatusLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only log access. Scoped under the apartment view permission —
    if you can see an apartment, you can see its log."""

    queryset = (
        ApartmentStatusLog.objects
        .select_related("apartment", "changed_by")
        .all()
    )
    serializer_class = ApartmentStatusLogSerializer
    filterset_fields = ("apartment",)

    def get_permissions(self):
        return _permissions_for("objects.apartments", self.action)


# --- Pricing entities ----------------------------------------------------


class PaymentPlanViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = PaymentPlan.objects.select_related("project").all()
    serializer_class = PaymentPlanSerializer
    filterset_fields = ("is_active", "project")

    def get_permissions(self):
        return _permissions_for("objects.payment_plans", self.action)


class DiscountRuleViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = (
        DiscountRule.objects
        .select_related("project", "payment_percent")
        .all()
    )
    serializer_class = DiscountRuleSerializer
    filterset_fields = ("is_active", "project", "is_duplex")

    def get_permissions(self):
        return _permissions_for("objects.discounts", self.action)


class CalculationViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = (
        Calculation.objects
        .select_related("apartment", "payment_percent")
        .all()
    )
    serializer_class = CalculationSerializer
    filterset_fields = ("is_active", "apartment", "payment_percent")

    def get_permissions(self):
        return _permissions_for("objects.calculations", self.action)


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only log — write access belongs to services.pricing (phase 3.4)."""

    queryset = (
        PriceHistory.objects
        .select_related("floor", "changed_by")
        .all()
    )
    serializer_class = PriceHistorySerializer
    filterset_fields = ("floor",)

    def get_permissions(self):
        # Gated by floor-view: if you can see a floor, you can see its log.
        return _permissions_for("objects.floors", self.action)
