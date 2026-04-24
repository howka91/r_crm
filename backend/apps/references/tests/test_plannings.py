"""Tests for the Planning catalog (references.Planning) — CRUD, permission
gates, image upload via multipart, per-project code uniqueness, and the
SET_NULL behaviour on Apartment when a referenced Planning is deleted.

The shape of these tests mirrors `apps.references.tests.test_crud` and
`apps.contracts.tests.test_docgen#TestContractTemplateUploadImage` —
both for permission harness (`_scoped_role` + superuser helper) and for
the minimal-PNG constant used to exercise ImageField storage.
"""
from __future__ import annotations

import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse
from PIL import Image
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import Apartment
from apps.objects.tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    FloorFactory,
    ProjectFactory,
    SectionFactory,
)
from apps.references.models import Planning
from apps.references.tests.factories import PlanningFactory
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped_role(base: str, action: str = "view") -> dict[str, bool]:
    perms = default_permissions(False)
    parts = f"{base}.{action}".split(".")
    for i in range(1, len(parts) + 1):
        perms[".".join(parts[:i])] = True
    return perms


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)


def _png(width: int = 4, height: int = 4, color: str = "#CCCCCC") -> bytes:
    """Generate a real PNG that passes ImageField validation.

    The hand-crafted 1×1 constant used by `contracts/upload-image` tests
    passes FileField but not ImageField — Pillow's validator checks the
    full PNG grammar. Use Pillow to synthesize a tiny but valid image.
    """
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


_PNG_BYTES = _png()


@pytest.mark.django_db
class TestPlanningCRUD:
    url_list = reverse("planning-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_list(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        PlanningFactory.create_batch(3, project=project)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 3

    def test_scoped_role_can_view(self, api_client):
        role = RoleFactory(
            code="plan-viewer",
            permissions=_scoped_role("references.plannings"),
        )
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create(self, api_client):
        role = RoleFactory(
            code="plan-viewer",
            permissions=_scoped_role("references.plannings"),
        )
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        project = ProjectFactory()
        payload = {
            "project": project.id,
            "name": {"ru": "A", "uz": "A", "oz": "А"},
            "code": "X-01",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_by_project(self, api_client):
        _superuser(api_client)
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        PlanningFactory.create_batch(2, project=p1)
        PlanningFactory.create_batch(3, project=p2)
        resp = api_client.get(f"{self.url_list}?project={p1.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2


@pytest.mark.django_db
class TestPlanningImageUpload:
    """Verify that `image_2d` and `image_3d` are accepted via multipart
    and stored under `references/plannings/{2d,3d}/YYYY/MM/`."""

    url_list = reverse("planning-list")

    def test_create_with_both_images(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        payload = {
            "project": project.id,
            "code": "3K-A",
            "name": '{"ru": "3-ком. А", "uz": "3-xon. A", "oz": "3-хон. А"}',
            "rooms_count": 3,
            "area": "72.50",
            "image_2d": SimpleUploadedFile("2d.png", _PNG_BYTES, "image/png"),
            "image_3d": SimpleUploadedFile("3d.png", _PNG_BYTES, "image/png"),
        }
        resp = api_client.post(self.url_list, payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        # Use `all_objects` — `Planning.objects` is a SoftDeleteManager and
        # the test runs inside a transaction, so any oddness in the save
        # shouldn't mask the row from the assertion.
        planning = Planning.all_objects.get(pk=resp.data["id"])
        # Storage path obeys the upload_to template.
        assert "references/plannings/2d/" in planning.image_2d.name
        assert "references/plannings/3d/" in planning.image_3d.name
        assert planning.image_2d.size == len(_PNG_BYTES)

    def test_create_without_images_allowed(self, api_client):
        """Images are optional — a manager may register a layout before
        the architect hands over the renders."""
        _superuser(api_client)
        project = ProjectFactory()
        payload = {
            "project": project.id,
            "code": "T-01",
            "name": '{"ru": "A", "uz": "A", "oz": "А"}',
        }
        resp = api_client.post(self.url_list, payload, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data


@pytest.mark.django_db
class TestPlanningCodeUniqueness:
    """`code` is unique within a project, but empty codes don't collide
    with each other (partial unique index)."""

    def test_same_code_same_project_rejected(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        PlanningFactory(project=project, code="3K-A")
        url = reverse("planning-list")
        payload = {
            "project": project.id,
            "code": "3K-A",
            "name": {"ru": "x", "uz": "x", "oz": "x"},
        }
        resp = api_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "code" in resp.data

    def test_same_code_different_project_ok(self):
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        PlanningFactory(project=p1, code="3K-A")
        # No clash — partial index is scoped by project.
        PlanningFactory(project=p2, code="3K-A")
        assert Planning.objects.filter(code="3K-A").count() == 2

    def test_empty_code_duplicates_allowed(self):
        project = ProjectFactory()
        PlanningFactory(project=project, code="")
        # Partial index condition is `code__gt=""`, so empty codes slip
        # through — two plannings without a code in the same ЖК is fine.
        with transaction.atomic():
            PlanningFactory(project=project, code="")
        assert Planning.objects.filter(project=project, code="").count() == 2


@pytest.mark.django_db
class TestPlanningAffectsApartments:
    """Relationship sanity — SET_NULL on delete, scoped picker queries."""

    def test_delete_planning_nulls_apartment_reference(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        building = BuildingFactory(project=project)
        section = SectionFactory(building=building)
        floor = FloorFactory(section=section)
        planning = PlanningFactory(project=project)
        apt = ApartmentFactory(floor=floor, planning=planning)

        url = reverse("planning-detail", args=[planning.id])
        resp = api_client.delete(url)
        assert resp.status_code in (
            status.HTTP_204_NO_CONTENT,
            status.HTTP_200_OK,
        )

        apt.refresh_from_db()
        assert apt.planning_id is None


@pytest.mark.django_db
class TestPlanningProjectProtect:
    """Cannot delete a Project that owns plannings — PROTECT on the FK
    kicks in and `ProtectedDestroyMixin` returns 409."""

    def test_cannot_delete_project_with_plannings(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        PlanningFactory(project=project)
        resp = api_client.delete(reverse("project-detail", args=[project.id]))
        assert resp.status_code == status.HTTP_409_CONFLICT
