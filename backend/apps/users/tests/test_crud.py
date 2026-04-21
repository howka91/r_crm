"""Tests for Staff/Role ViewSets and permission enforcement."""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.permission_tree import default_permissions
from apps.users.tests.factories import RoleFactory, StaffFactory


@pytest.mark.django_db
class TestRoleCRUD:
    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(reverse("role-list"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_list(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        resp = api_client.get(reverse("role-list"))
        assert resp.status_code == status.HTTP_200_OK

    def test_role_with_view_permission_can_list(self, api_client):
        perms = default_permissions(False)
        perms["administration"] = True
        perms["administration.roles"] = True
        perms["administration.roles.view"] = True
        role = RoleFactory(code="roles-reader", permissions=perms)
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(reverse("role-list"))
        assert resp.status_code == status.HTTP_200_OK

    def test_parent_off_disables_child_permission(self, api_client):
        # Leaf is True but parent is False → access denied.
        perms = default_permissions(False)
        perms["administration"] = False           # ← kill switch
        perms["administration.roles"] = True
        perms["administration.roles.view"] = True
        role = RoleFactory(code="broken-parent", permissions=perms)
        staff = StaffFactory(role=role, password="x12345678")
        api_client.force_authenticate(staff)
        resp = api_client.get(reverse("role-list"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_role_save_fills_missing_keys_with_false(self, api_client):
        # Role.save() auto-fills the permissions dict with default False.
        role = RoleFactory(code="partial", permissions={"clients": True})
        assert "contracts" in role.permissions
        assert role.permissions["contracts"] is False
        assert role.permissions["clients"] is True


@pytest.mark.django_db
class TestStaffCRUD:
    def _admin_auth(self, api_client):
        admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
        api_client.force_authenticate(admin)
        return admin

    def test_create_staff(self, api_client):
        self._admin_auth(api_client)
        role = RoleFactory(code="sales")
        resp = api_client.post(
            reverse("staff-list"),
            {
                "email": "new@example.com",
                "full_name": "Новый Юзер",
                "phone_number": "+998901234567",
                "language": "ru",
                "role_id": role.id,
                "password": "newpassword123",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json()["email"] == "new@example.com"
        assert resp.json()["role"]["code"] == "sales"

    def test_phone_regex_validation(self, api_client):
        self._admin_auth(api_client)
        resp = api_client.post(
            reverse("staff-list"),
            {
                "email": "bad@example.com",
                "full_name": "x",
                "phone_number": "123",  # invalid
                "password": "newpassword123",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone_number" in resp.json()

    def test_list_hides_passwords(self, api_client):
        self._admin_auth(api_client)
        StaffFactory(email="visible@example.com")
        resp = api_client.get(reverse("staff-list"))
        assert resp.status_code == status.HTTP_200_OK
        for row in resp.json().get("results", resp.json()):
            assert "password" not in row
