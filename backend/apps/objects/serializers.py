"""DRF serializers for the objects app.

Per-model serializer + a `children_count` read-only field on the parent
serializers (Project/Building/Section) so list views can show e.g.
"5 корпусов" without an extra round-trip.

`price_per_sqm` on Floor is a string in JSON (DRF default for Decimal),
matching the `MoneyField` convention established in references.Currency.
"""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

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

# Shared photo upload guardrails. Larger than the 5 MB image-upload for
# Tiptap (contracts) because project/building shots can be real camera
# photos — a lawyer uploading 8 MB from a phone is common.
_PHOTO_MAX_BYTES = 10 * 1024 * 1024
_PHOTO_ALLOWED_MIMES = frozenset({
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
})


def _validate_photo_file(file) -> None:
    """Reject files that bust the shared photo limits. Raises
    DRF ValidationError (translated into 400). Kept at module level
    so both ProjectPhotoSerializer and BuildingPhotoSerializer reuse
    the exact same policy."""
    mime = (getattr(file, "content_type", "") or "").lower()
    if mime and mime not in _PHOTO_ALLOWED_MIMES:
        raise serializers.ValidationError(
            "Неподдерживаемый формат. Допустимы PNG, JPEG, WebP, GIF.",
        )
    if getattr(file, "size", 0) > _PHOTO_MAX_BYTES:
        raise serializers.ValidationError(
            "Файл больше 10 МБ — уменьшите и попробуйте снова.",
        )


def _cover_payload(photos_qs, request) -> dict | None:
    """Pick the first photo of `photos_qs` (already ordered by sort)
    and serialize a minimal {id, url, caption} preview for list screens.
    Returns None when the queryset is empty.
    """
    photo = photos_qs[0] if photos_qs else None
    if photo is None:
        return None
    url = photo.file.url if photo.file else None
    if url and request is not None:
        url = request.build_absolute_uri(url)
    return {"id": photo.id, "url": url, "caption": photo.caption}


class ProjectSerializer(serializers.ModelSerializer):
    developer_name = serializers.SerializerMethodField()
    buildings_count = serializers.IntegerField(
        source="buildings.count", read_only=True,
    )
    # Inlined cover for list screens: saves a round-trip on the hub
    # card grid. The related manager is `photos` (CASCADE), ordered by
    # `sort, id` via the model's Meta.ordering.
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id",
            "developer",
            "developer_name",
            "title",
            "address",
            "description",
            "banks",
            "contract_number_index",
            "sort",
            "is_active",
            "buildings_count",
            "cover",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "developer_name",
            "contract_number_index",
            "buildings_count",
            "cover",
            "created_at",
            "modified_at",
        )

    def get_developer_name(self, obj: Project) -> dict | None:
        dev = obj.developer
        return dev.name if dev else None

    def get_cover(self, obj: Project) -> dict | None:
        # `obj.photos.all()` uses the prefetch applied in the ViewSet
        # when available; otherwise falls back to an ordered query.
        photos = list(obj.photos.all())
        return _cover_payload(photos, self.context.get("request"))


class BuildingSerializer(serializers.ModelSerializer):
    sections_count = serializers.IntegerField(
        source="sections.count", read_only=True,
    )
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Building
        fields = (
            "id",
            "project",
            "title",
            "number",
            "cadastral_number",
            "date_of_issue",
            "planning_file",
            "sort",
            "is_active",
            "sections_count",
            "cover",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "sections_count",
            "cover",
            "created_at",
            "modified_at",
        )

    def get_cover(self, obj: Building) -> dict | None:
        photos = list(obj.photos.all())
        return _cover_payload(photos, self.context.get("request"))


class ProjectPhotoSerializer(serializers.ModelSerializer):
    file = serializers.ImageField(required=True, allow_null=False)
    # Explicit default — otherwise DRF's multipart parser treats an
    # omitted BooleanField as `False` (quirk vs JSON where omitted
    # means "not provided" and the model default kicks in).
    is_active = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = ProjectPhoto
        fields = (
            "id",
            "project",
            "file",
            "caption",
            "sort",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")

    def validate_file(self, value):
        _validate_photo_file(value)
        return value


class BuildingPhotoSerializer(serializers.ModelSerializer):
    file = serializers.ImageField(required=True, allow_null=False)
    is_active = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = BuildingPhoto
        fields = (
            "id",
            "building",
            "file",
            "caption",
            "sort",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")

    def validate_file(self, value):
        _validate_photo_file(value)
        return value


class SectionSerializer(serializers.ModelSerializer):
    floors_count = serializers.IntegerField(
        source="floors.count", read_only=True,
    )

    class Meta:
        model = Section
        fields = (
            "id",
            "building",
            "title",
            "number",
            "planning_file",
            "sort",
            "is_active",
            "floors_count",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "floors_count",
            "created_at",
            "modified_at",
        )


class FloorSerializer(serializers.ModelSerializer):
    apartments_count = serializers.IntegerField(
        source="apartments.count", read_only=True,
    )

    class Meta:
        model = Floor
        fields = (
            "id",
            "section",
            "number",
            "price_per_sqm",
            "sort",
            "is_active",
            "apartments_count",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "apartments_count", "created_at", "modified_at")


class ApartmentSerializer(serializers.ModelSerializer):
    """Full Apartment shape. `status` is writable via create/update — but only
    to allowable values. For state transitions post-create, clients should
    hit the `change-status` action; writing `status` directly via PATCH is
    supported for superusers and initial data import (no transition check)."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    # Tiny expansion of the picked planning so the drawer/inventory UI can
    # render a preview without a second round-trip to /plannings/.
    planning_preview = serializers.SerializerMethodField()

    class Meta:
        model = Apartment
        fields = (
            "id",
            "floor",
            "number",
            "rooms_count",
            "area",
            "total_bti_area",
            "total_price",
            "surcharge",
            "is_duplex",
            "is_studio",
            "is_euro_planning",
            "planning",
            "planning_preview",
            "decoration",
            "output_window",
            "occupied_by",
            "characteristics",
            "status",
            "status_display",
            "booking_expires_at",
            "sort",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = (
            "id",
            "status_display",
            "planning_preview",
            "booking_expires_at",
            "created_at",
            "modified_at",
        )

    def validate(self, attrs: dict) -> dict:
        """Reject a planning that belongs to a different ЖК than the one
        this apartment lives in. Catching this at the serializer means
        the UI gets a clean 400 instead of a silent mismatch that would
        only surface later when a manager opens the card."""
        planning = attrs.get("planning") or (
            self.instance.planning if self.instance else None
        )
        floor = attrs.get("floor") or (
            self.instance.floor if self.instance else None
        )
        if planning is not None and floor is not None:
            target_project = floor.section.building.project_id
            if planning.project_id != target_project:
                raise serializers.ValidationError(
                    {"planning": "Планировка принадлежит другому ЖК."},
                    code="planning_cross_project",
                )
        return super().validate(attrs)

    def get_planning_preview(self, obj: Apartment) -> dict | None:
        planning = obj.planning
        if planning is None:
            return None
        request = self.context.get("request")
        image_2d = None
        image_3d = None
        if planning.image_2d:
            url = planning.image_2d.url
            image_2d = request.build_absolute_uri(url) if request else url
        if planning.image_3d:
            url = planning.image_3d.url
            image_3d = request.build_absolute_uri(url) if request else url
        return {
            "id": planning.id,
            "code": planning.code,
            "name": planning.name,
            "rooms_count": planning.rooms_count,
            "area": str(planning.area) if planning.area is not None else None,
            "image_2d": image_2d,
            "image_3d": image_3d,
        }


class ApartmentStatusLogSerializer(serializers.ModelSerializer):
    """Read-only — writes happen inside services.apartments.change_status."""

    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ApartmentStatusLog
        fields = (
            "id",
            "apartment",
            "old_status",
            "new_status",
            "changed_by",
            "changed_by_name",
            "comment",
            "created_at",
        )
        read_only_fields = fields

    def get_changed_by_name(self, obj: ApartmentStatusLog) -> str | None:
        return obj.changed_by.full_name if obj.changed_by else None


class ChangeStatusInputSerializer(serializers.Serializer):
    """Payload for the `POST /apartments/:id/change-status/` action."""

    new_status = serializers.ChoiceField(choices=Apartment.Status.choices)
    comment = serializers.CharField(max_length=512, required=False, allow_blank=True)


# --- Pricing entities ----------------------------------------------------


class PaymentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = (
            "id",
            "project",
            "name",
            "down_payment_percent",
            "installment_months",
            "sort",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")


class DiscountRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountRule
        fields = (
            "id",
            "project",
            "area_start",
            "area_end",
            "payment_percent",
            "discount_percent",
            "is_duplex",
            "sort",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")

    def validate(self, attrs: dict) -> dict:
        # Model CheckConstraint enforces area_end >= area_start at DB level,
        # but reject early so clients get a clean 400 instead of a DB error.
        start = attrs.get("area_start", getattr(self.instance, "area_start", None))
        end = attrs.get("area_end", getattr(self.instance, "area_end", None))
        if start is not None and end is not None and end < start:
            raise serializers.ValidationError(
                {"area_end": "Верхняя граница должна быть ≥ нижней."},
            )
        return attrs


class CalculationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calculation
        fields = (
            "id",
            "apartment",
            "payment_percent",
            "discount_percent",
            "installment_months",
            "new_price_per_sqm",
            "new_total_price",
            "initial_fee",
            "monthly_payment",
            "is_active",
            "created_at",
            "modified_at",
        )
        read_only_fields = ("id", "created_at", "modified_at")


class PriceHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PriceHistory
        fields = (
            "id",
            "floor",
            "old_price",
            "new_price",
            "changed_by",
            "changed_by_name",
            "comment",
            "created_at",
        )
        read_only_fields = fields

    def get_changed_by_name(self, obj: PriceHistory) -> str | None:
        return obj.changed_by.full_name if obj.changed_by else None


# --- Input serializers for custom actions --------------------------------


class ChangeFloorPriceInputSerializer(serializers.Serializer):
    """Payload for `POST /floors/:id/change-price/`."""

    new_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0"),
    )
    comment = serializers.CharField(max_length=512, required=False, allow_blank=True)


class BookApartmentInputSerializer(serializers.Serializer):
    """Payload for `POST /apartments/:id/book/` (regular or VIP)."""

    duration_days = serializers.IntegerField(min_value=1, max_value=365)
    comment = serializers.CharField(max_length=512, required=False, allow_blank=True)
    vip = serializers.BooleanField(required=False, default=False)


class ReleaseApartmentInputSerializer(serializers.Serializer):
    """Payload for `POST /apartments/:id/release/`."""

    comment = serializers.CharField(max_length=512, required=False, allow_blank=True)


class DuplicateSectionInputSerializer(serializers.Serializer):
    """Payload for `POST /sections/:id/duplicate/`."""

    target_building_id = serializers.IntegerField(min_value=1)
