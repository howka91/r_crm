"""End-to-end tests for auth endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.users.tests.factories import StaffFactory


@pytest.mark.django_db
class TestLogin:
    def test_success_returns_access_refresh_and_user(self, api_client):
        staff = StaffFactory(login="a-user", password="secret-pass-1")
        resp = api_client.post(
            reverse("auth-login"),
            {"login": "a-user", "password": "secret-pass-1"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "access" in data and "refresh" in data
        assert data["user"]["id"] == str(staff.id)
        assert data["user"]["login"] == staff.login

    def test_wrong_password(self, api_client):
        StaffFactory(login="b-user", password="right-pass")
        resp = api_client.post(
            reverse("auth-login"),
            {"login": "b-user", "password": "wrong-pass"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_inactive_user_blocked(self, api_client):
        StaffFactory(login="c-user", password="x12345678", is_active=False)
        resp = api_client.post(
            reverse("auth-login"),
            {"login": "c-user", "password": "x12345678"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_short_password_admin_login(self, api_client):
        """Dev convenience: password="1" is accepted end-to-end (no min_length
        on the auth path itself)."""
        StaffFactory(login="admin", password="1")
        resp = api_client.post(
            reverse("auth-login"),
            {"login": "admin", "password": "1"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMe:
    def test_requires_auth(self, api_client):
        resp = api_client.get(reverse("auth-me"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_current_user(self, api_client):
        staff = StaffFactory(login="me-user", password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(reverse("auth-me"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["login"] == "me-user"


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
