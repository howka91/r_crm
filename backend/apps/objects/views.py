"""DRF viewsets for the objects app.

Pattern mirrors `apps.references.views`: each ViewSet gets its own permission
base via `_permissions_for(base, action)`. Custom `@action`s (e.g. `book` on
ApartmentViewSet in phase 3.2) carry their own permission gates.

`floor.edit_price` is a dedicated extra permission (see permission_tree) —
not enforced here yet; phase 3.3 ties it to the explicit price-change action
on FloorViewSet.
"""
from __future__ import annotations

from django.db import transaction
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.mixins import ProtectedDestroyMixin
from apps.core.permissions import HasPermission, check as check_permission
from apps.objects.models import (
    Apartment,
    ApartmentStatusLog,
    Building,
    BuildingPhoto,
    Calculation,
    DiscountRule,
    Floor,
    PaymentPlan,
    PriceHistory,
    Project,
    ProjectPhoto,
    Section,
)
from apps.objects.serializers import (
    ApartmentSerializer,
    ApartmentStatusLogSerializer,
    BookApartmentInputSerializer,
    BuildingPhotoSerializer,
    BuildingSerializer,
    CalculationSerializer,
    ChangeFloorPriceInputSerializer,
    ChangeStatusInputSerializer,
    DiscountRuleSerializer,
    DuplicateSectionInputSerializer,
    FloorSerializer,
    PaymentPlanSerializer,
    PriceHistorySerializer,
    ProjectPhotoSerializer,
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
from apps.objects.services.section_duplication import duplicate_section

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
    schema_tags = ["Объекты"]
    # `prefetch_related("photos")` lets ProjectSerializer.get_cover()
    # pull the cover without an extra query per row — otherwise the
    # hub card grid would do N+1 on 20 projects.
    queryset = (
        Project.objects
        .select_related("developer")
        .prefetch_related("photos")
        .all()
    )
    serializer_class = ProjectSerializer
    filterset_fields = ("is_active", "developer")
    search_fields = ("address",)

    def get_permissions(self):
        if self.action == "inventory":
            return [IsAuthenticated(), HasPermission("objects.apartments.view")]
        return _permissions_for("objects.projects", self.action)

    @action(detail=True, methods=["get"], url_path="inventory")
    def inventory(self, request: Request, pk: str | None = None) -> Response:
        """Return the full Buildings → Sections → Floors → Apartments tree
        for this project in one payload.

        Shaped to match what the frontend inventory grid and the contract
        wizard's ApartmentPicker already consume — four flat collections
        rather than a nested tree, so the existing in-memory lookups
        (by floor id, by section id) keep working without a reshape.

        Beats the previous fan-out of four unbounded `/buildings/`,
        `/sections/`, `/floors/`, `/apartments/` requests with in-memory
        filtering — that is O(project) × O(all-apartments-in-db) and
        breaks past ~5k apartments overall.
        """
        project: Project = self.get_object()
        buildings_qs = (
            Building.objects
            .filter(project=project)
            .prefetch_related("photos")  # so BuildingSerializer.cover hits no N+1
            .order_by("sort", "id")
        )
        sections_qs = (
            Section.objects
            .filter(building__project=project)
            .select_related("building")
            .order_by("sort", "id")
        )
        floors_qs = (
            Floor.objects
            .filter(section__building__project=project)
            .select_related("section")
            .order_by("sort", "number")
        )
        apartments_qs = (
            Apartment.objects
            .filter(floor__section__building__project=project)
            .select_related("floor", "floor__section", "floor__section__building")
            .prefetch_related("characteristics")
            .order_by("sort", "number")
        )
        ctx = {"request": request}
        return Response(
            {
                "buildings": BuildingSerializer(buildings_qs, many=True, context=ctx).data,
                "sections": SectionSerializer(sections_qs, many=True, context=ctx).data,
                "floors": FloorSerializer(floors_qs, many=True, context=ctx).data,
                "apartments": ApartmentSerializer(apartments_qs, many=True, context=ctx).data,
            },
            status=http_status.HTTP_200_OK,
        )


class BuildingViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    schema_tags = ["Объекты"]
    queryset = (
        Building.objects
        .select_related("project")
        .prefetch_related("photos")
        .all()
    )
    serializer_class = BuildingSerializer
    filterset_fields = ("is_active", "project")
    search_fields = ("number", "cadastral_number")

    def get_permissions(self):
        return _permissions_for("objects.buildings", self.action)


class SectionViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    schema_tags = ["Объекты"]
    queryset = Section.objects.select_related("building", "building__project").all()
    serializer_class = SectionSerializer
    filterset_fields = ("is_active", "building")

    def get_permissions(self):
        # `duplicate` is effectively a bulk-create — gate it by the create
        # permission on sections (not view/edit, which wouldn't be enough).
        if self.action == "duplicate":
            return [
                IsAuthenticated(),
                HasPermission("objects.sections.create"),
            ]
        return _permissions_for("objects.sections", self.action)

    def destroy(self, request: Request, *args, **kwargs):  # type: ignore[override]
        """Default destroy is blocked by ProtectedError when floors exist.

        Pass `?force=true` to cascade — deletes every Apartment in the
        section (which cascades Calculations + ApartmentStatusLogs via the
        models' on_delete=CASCADE), then every Floor (which cascades
        PriceHistory), then the Section itself. Runs in one transaction.

        Uses `all_objects` (the plain Manager) on bulk deletes because
        `objects` is a SoftDeleteManager whose `.delete()` only flips
        `is_active=False` — which would leave the rows in place and the
        parent PROTECT check would still block the Section delete.
        """
        if request.query_params.get("force") == "true":
            section: Section = self.get_object()
            with transaction.atomic():
                Apartment.all_objects.filter(floor__section=section).delete()
                Floor.all_objects.filter(section=section).delete()
                section.delete()
            return Response(status=http_status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request: Request, pk: str | None = None) -> Response:
        """Clone this Section (plus all its Floors and Apartments) into the
        specified target Building. Useful when the user has built one
        "template" section and wants the rest of the project to mirror it.

        Apartments are copied with a clean booking state (status=free,
        no booking_expires_at). Calculations and planning files are not
        copied — re-run the pricing service / re-upload as needed.
        """
        src: Section = self.get_object()
        payload = DuplicateSectionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        target_id = payload.validated_data["target_building_id"]
        try:
            target = Building.objects.get(pk=target_id)
        except Building.DoesNotExist:
            return Response(
                {"target_building_id": "Корпус не найден."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        result = duplicate_section(src, target)
        new_section = Section.objects.get(pk=result.new_section_id)
        return Response(
            {
                "section": SectionSerializer(new_section).data,
                "floors_created": result.floors_created,
                "apartments_created": result.apartments_created,
            },
            status=http_status.HTTP_201_CREATED,
        )


class FloorViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    schema_tags = ["Объекты"]
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

    def destroy(self, request: Request, *args, **kwargs):  # type: ignore[override]
        """Pass `?force=true` to cascade-delete every Apartment (and its
        Calculations / ApartmentStatusLogs) before removing the Floor.
        Without it, Apartment.floor's PROTECT blocks the delete and the
        shared ProtectedDestroyMixin returns 409.

        See SectionViewSet.destroy for why `all_objects` is used on the bulk.
        """
        if request.query_params.get("force") == "true":
            floor: Floor = self.get_object()
            with transaction.atomic():
                Apartment.all_objects.filter(floor=floor).delete()
                floor.delete()
            return Response(status=http_status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)

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
    schema_tags = ["Объекты"]
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

    schema_tags = ["Объекты"]
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
    schema_tags = ["Объекты"]
    queryset = PaymentPlan.objects.select_related("project").all()
    serializer_class = PaymentPlanSerializer
    filterset_fields = ("is_active", "project")

    def get_permissions(self):
        return _permissions_for("objects.payment_plans", self.action)


class DiscountRuleViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    schema_tags = ["Объекты"]
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
    schema_tags = ["Объекты"]
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

    schema_tags = ["Объекты"]
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


# --- Photo galleries ----------------------------------------------------
#
# Two nearly-identical ViewSets, one per parent model. Kept separate
# (rather than a generic base) because permissions hang off different
# permission-tree branches — objects.projects vs objects.buildings —
# and the multipart payload uses different FK field names.


class ProjectPhotoViewSet(viewsets.ModelViewSet):
    schema_tags = ["Объекты"]
    queryset = ProjectPhoto.objects.select_related("project").all()
    serializer_class = ProjectPhotoSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_fields = ("project", "is_active")
    ordering_fields = ("sort", "id")

    def get_permissions(self):
        # Reuse the project's CRUD keys — if you can edit the ЖК,
        # you can manage its photos.
        return _permissions_for("objects.projects", self.action)

    @action(detail=True, methods=["post"], url_path="make-cover")
    def make_cover(self, request: Request, pk: str | None = None) -> Response:
        """Promote this photo to sort=0 and push everyone else down by 1.

        Keeps the ordering dense (0, 1, 2, …) after the rewrite so the
        "first photo = cover" invariant remains trivially readable.
        Wrapped in a transaction so a concurrent upload can't slip in
        between the push and the promote.
        """
        photo: ProjectPhoto = self.get_object()
        with transaction.atomic():
            siblings = (
                ProjectPhoto.objects
                .select_for_update()
                .filter(project_id=photo.project_id)
                .exclude(pk=photo.pk)
                .order_by("sort", "id")
            )
            for idx, s in enumerate(siblings, start=1):
                if s.sort != idx:
                    s.sort = idx
                    s.save(update_fields=["sort", "modified_at"])
            if photo.sort != 0:
                photo.sort = 0
                photo.save(update_fields=["sort", "modified_at"])
        return Response(
            ProjectPhotoSerializer(photo, context={"request": request}).data,
            status=http_status.HTTP_200_OK,
        )


class BuildingPhotoViewSet(viewsets.ModelViewSet):
    schema_tags = ["Объекты"]
    queryset = BuildingPhoto.objects.select_related("building").all()
    serializer_class = BuildingPhotoSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_fields = ("building", "is_active")
    ordering_fields = ("sort", "id")

    def get_permissions(self):
        return _permissions_for("objects.buildings", self.action)

    @action(detail=True, methods=["post"], url_path="make-cover")
    def make_cover(self, request: Request, pk: str | None = None) -> Response:
        photo: BuildingPhoto = self.get_object()
        with transaction.atomic():
            siblings = (
                BuildingPhoto.objects
                .select_for_update()
                .filter(building_id=photo.building_id)
                .exclude(pk=photo.pk)
                .order_by("sort", "id")
            )
            for idx, s in enumerate(siblings, start=1):
                if s.sort != idx:
                    s.sort = idx
                    s.save(update_fields=["sort", "modified_at"])
            if photo.sort != 0:
                photo.sort = 0
                photo.save(update_fields=["sort", "modified_at"])
        return Response(
            BuildingPhotoSerializer(photo, context={"request": request}).data,
            status=http_status.HTTP_200_OK,
        )
