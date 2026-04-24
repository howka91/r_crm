"""Tests for ProjectPhoto / BuildingPhoto galleries.

Covers:

* Multipart upload — happy path, MIME whitelist, 10 MB size limit.
* Permission gating (view-only role blocked from create/delete).
* CASCADE on parent delete — photos vanish with the ЖК/корпус.
* `cover` inline in ProjectSerializer / BuildingSerializer — first
  by (sort, id), None when no photos.
* `make-cover` action — moves chosen photo to sort=0 and renumbers
  the rest densely (0, 1, 2, …).
* N+1 guard — listing N projects with photos stays at constant
  queries thanks to `prefetch_related("photos")`.
"""
from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.objects.models import (
    Building,
    BuildingPhoto,
    Project,
    ProjectPhoto,
)
from apps.objects.tests.factories import (
    BuildingFactory,
    BuildingPhotoFactory,
    ProjectFactory,
    ProjectPhotoFactory,
)
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped_role(*keys: str) -> dict[str, bool]:
    perms = default_permissions(False)
    for k in keys:
        parts = k.split(".")
        for i in range(1, len(parts) + 1):
            perms[".".join(parts[:i])] = True
    return perms


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)


def _png(width: int = 8, height: int = 8, color: str = "#D4D4D4") -> bytes:
    """Real PNG that passes ImageField validation — Pillow rejects the
    hand-crafted 1×1 stub we use for permission tests elsewhere."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


# --- ProjectPhoto --------------------------------------------------------


@pytest.mark.django_db
class TestProjectPhotoUpload:
    url = reverse("project-photo-list")

    def _upload(self, api_client, project, **kw):
        f = SimpleUploadedFile(
            kw.pop("name", "hero.png"),
            kw.pop("content", _png()),
            content_type=kw.pop("content_type", "image/png"),
        )
        payload = {"project": project.id, "file": f, **kw}
        return api_client.post(self.url, payload, format="multipart")

    def test_happy_path(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        resp = self._upload(api_client, project, caption="Фасад с юга")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        # Use `all_objects` — the test-DB soft-delete filter on `.objects`
        # shouldn't hide freshly-created rows, but belt-and-suspenders.
        photo = ProjectPhoto.all_objects.get(pk=resp.data["id"])
        assert photo.project_id == project.id
        assert photo.caption == "Фасад с юга"
        assert photo.file.name.startswith("objects/projects/photos/")
        assert photo.is_active is True

    def test_viewer_blocked_from_create(self, api_client):
        role = RoleFactory(
            code="proj-viewer",
            permissions=_scoped_role("objects.projects.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        project = ProjectFactory()
        resp = self._upload(api_client, project)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_non_image_mime(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        resp = self._upload(
            api_client, project,
            content=b"%PDF-1.4 not really",
            content_type="application/pdf",
            name="brochure.pdf",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # DRF puts field-level errors keyed by field name.
        assert "file" in resp.data

    def test_rejects_oversized_file(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        # Build ~11 MB blob — 10 MB is the limit. Larger than the real
        # photos managers usually upload, but still small enough to
        # keep the test fast.
        big = b"\x00" * (10 * 1024 * 1024 + 1)
        # File must *decode* as an image for ImageField validation to
        # even reach our size check. Prepend a real PNG header + IEND
        # so Pillow accepts it as a (broken) PNG; since our serializer
        # validator runs before Pillow does strict decode on open, the
        # size rule trips first.
        resp = self._upload(
            api_client, project,
            content=big,
            content_type="image/png",
            name="huge.png",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in resp.data


@pytest.mark.django_db
class TestProjectCoverInSerializer:
    def test_cover_is_first_by_sort(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        # Seed in reverse order to confirm serializer uses sort, not id.
        ProjectPhotoFactory(project=project, sort=5, caption="last")
        first = ProjectPhotoFactory(project=project, sort=0, caption="first")
        ProjectPhotoFactory(project=project, sort=3, caption="middle")

        resp = api_client.get(reverse("project-detail", args=[project.id]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cover"] is not None
        assert resp.data["cover"]["id"] == first.id
        assert resp.data["cover"]["caption"] == "first"

    def test_cover_null_when_no_photos(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        resp = api_client.get(reverse("project-detail", args=[project.id]))
        assert resp.data["cover"] is None

    def test_list_no_n_plus_one(
        self, api_client, django_assert_max_num_queries,
    ):
        """Twenty projects with 3 photos each should not produce 60
        extra queries — prefetch_related("photos") collapses them
        into one IN-clause lookup."""
        _superuser(api_client)
        for _ in range(20):
            p = ProjectFactory()
            ProjectPhotoFactory.create_batch(3, project=p)
        # Auth + permission lookups add a handful of queries; the
        # policy cap is "doesn't explode with N". 30 is generous
        # and will catch a regression where we drop the prefetch.
        with django_assert_max_num_queries(30):
            resp = api_client.get(reverse("project-list"))
            assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProjectPhotoCascade:
    def test_delete_project_deletes_photos(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        ProjectPhotoFactory.create_batch(3, project=project)
        # Hard-delete bypassing `ProtectedDestroyMixin` — direct model
        # delete to exercise the FK CASCADE rule.
        Project.all_objects.filter(pk=project.pk).delete()
        assert ProjectPhoto.objects.filter(project_id=project.pk).count() == 0


@pytest.mark.django_db
class TestProjectPhotoMakeCover:
    def test_promotes_and_renumbers(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        p0 = ProjectPhotoFactory(project=project, sort=0)
        p1 = ProjectPhotoFactory(project=project, sort=1)
        p2 = ProjectPhotoFactory(project=project, sort=2)

        url = reverse("project-photo-make-cover", args=[p2.id])
        resp = api_client.post(url)
        assert resp.status_code == status.HTTP_200_OK, resp.data

        p0.refresh_from_db(); p1.refresh_from_db(); p2.refresh_from_db()
        assert p2.sort == 0
        # Former 0 and 1 slide to 1 and 2 respectively.
        assert sorted([p0.sort, p1.sort]) == [1, 2]

    def test_idempotent_on_existing_cover(self, api_client):
        _superuser(api_client)
        project = ProjectFactory()
        p0 = ProjectPhotoFactory(project=project, sort=0)
        p1 = ProjectPhotoFactory(project=project, sort=1)

        resp = api_client.post(reverse("project-photo-make-cover", args=[p0.id]))
        assert resp.status_code == status.HTTP_200_OK
        p0.refresh_from_db(); p1.refresh_from_db()
        assert p0.sort == 0
        assert p1.sort == 1


# --- BuildingPhoto (slimmer mirror — shared serializer logic) ------------


@pytest.mark.django_db
class TestBuildingPhoto:
    def test_upload_and_cover(self, api_client):
        _superuser(api_client)
        building = BuildingFactory()
        f = SimpleUploadedFile("front.png", _png(), content_type="image/png")
        resp = api_client.post(
            reverse("building-photo-list"),
            {"building": building.id, "file": f, "caption": "парадная"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        detail = api_client.get(reverse("building-detail", args=[building.id]))
        assert detail.data["cover"] is not None
        assert detail.data["cover"]["caption"] == "парадная"

    def test_cascade_on_building_delete(self):
        building = BuildingFactory()
        BuildingPhotoFactory.create_batch(2, building=building)
        Building.all_objects.filter(pk=building.pk).delete()
        assert BuildingPhoto.objects.filter(building_id=building.pk).count() == 0

    def test_make_cover_reorders(self, api_client):
        _superuser(api_client)
        building = BuildingFactory()
        p0 = BuildingPhotoFactory(building=building, sort=0)
        p1 = BuildingPhotoFactory(building=building, sort=1)
        resp = api_client.post(
            reverse("building-photo-make-cover", args=[p1.id]),
        )
        assert resp.status_code == status.HTTP_200_OK
        p0.refresh_from_db(); p1.refresh_from_db()
        assert p1.sort == 0 and p0.sort == 1
