"""End-to-end tests for auth endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.users.tests.factories import StaffFactory


@pytest.mark.django_db
class TestLogin:
    def test_success_returns_access_refresh_and_user(self, api_client):
        staff = StaffFactory(email="a@example.com", password="secret-pass-1")
        resp = api_client.post(
            reverse("auth-login"),
            {"email": "a@example.com", "password": "secret-pass-1"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "access" in data and "refresh" in data
        assert data["user"]["id"] == str(staff.id)
        assert data["user"]["email"] == staff.email

    def test_wrong_password(self, api_client):
        StaffFactory(email="b@example.com", password="right-pass")
        resp = api_client.post(
            reverse("auth-login"),
            {"email": "b@example.com", "password": "wrong-pass"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_inactive_user_blocked(self, api_client):
        StaffFactory(email="c@example.com", password="x12345678", is_active=False)
        resp = api_client.post(
            reverse("auth-login"),
            {"email": "c@example.com", "password": "x12345678"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestMe:
    def test_requires_auth(self, api_client):
        resp = api_client.get(reverse("auth-me"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_current_user(self, api_client):
        staff = StaffFactory(email="me@example.com", password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(reverse("auth-me"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["email"] == "me@example.com"


@pytest.mark.django_db
class TestPermissionTree:
    def test_requires_auth(self, api_client):
        resp = api_client.get(reverse("permissions-tree"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_tree(self, api_client):
        staff = StaffFactory(password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(reverse("permissions-tree"))
        assert resp.status_code == status.HTTP_200_OK
        tree = resp.json()["tree"]
        assert isinstance(tree, list)
        # Every top-level node has a key and ru/uz/oz labels.
        for node in tree:
            assert "key" in node
            assert set(node["label"].keys()) == {"ru", "uz", "oz"}
