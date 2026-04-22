"""Tests for Clients CRUD: Client + ClientContact + Requisite + lookups.

Pattern mirrors `apps.references.tests.test_crud` and
`apps.objects.tests.test_hierarchy`: permission gating per ViewSet, a few
happy-path creates, and the handful of serializer-validation rules.
"""
from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status

from apps.clients.models import Client, ClientContact, ClientStatus, Requisite
from apps.clients.tests.factories import (
    ClientContactFactory,
    ClientFactory,
    ClientGroupFactory,
    ClientStatusFactory,
    RequisiteFactory,
)
from apps.core.permission_tree import default_permissions
from apps.users.tests.factories import RoleFactory, StaffFactory


def _scoped(*keys: str) -> dict[str, bool]:
    perms = default_permissions(False)
    for k in keys:
        parts = k.split(".")
        for i in range(1, len(parts) + 1):
            perms[".".join(parts[:i])] = True
    return perms


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)
    return admin


# --- Client ---------------------------------------------------------------


@pytest.mark.django_db
class TestClientCRUD:
    url_list = reverse("client-list")

    def test_list_requires_permission(self, api_client):
        role = RoleFactory(code="no-perms")
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        assert api_client.get(self.url_list).status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_list(self, api_client):
        _superuser(api_client)
        ClientFactory.create_batch(3)
        resp = api_client.get(self.url_list)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 3

    def test_scoped_role_can_view(self, api_client):
        role = RoleFactory(code="c-v", permissions=_scoped("clients.view"))
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        assert api_client.get(self.url_list).status_code == status.HTTP_200_OK

    def test_create_phys(self, api_client):
        _superuser(api_client)
        payload = {
            "entity": "phys",
            "gender": "male",
            "full_name": "Иванов Иван Иванович",
            "phones": ["+998901234567"],
            "emails": ["ivanov@example.com"],
            "pin": "12345678901234",
            "birth_date": "1990-01-15",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        c = Client.objects.get(id=resp.data["id"])
        assert c.entity == "phys"
        assert c.phones == ["+998901234567"]

    def test_create_jur(self, api_client):
        _superuser(api_client)
        payload = {
            "entity": "jur",
            "full_name": "ООО «Ташкент-Строй»",
            "inn": "301234567",
            "oked": "41200",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_gender_rejected_for_jur(self, api_client):
        """Serializer enforces the phys/jur split softly."""
        _superuser(api_client)
        payload = {
            "entity": "jur",
            "full_name": "ООО X",
            "gender": "male",
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "gender" in resp.data

    def test_full_name_required(self, api_client):
        _superuser(api_client)
        resp = api_client.post(
            self.url_list, {"entity": "phys"}, format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_by_entity(self, api_client):
        _superuser(api_client)
        ClientFactory.create_batch(2, entity="phys")
        ClientFactory(entity="jur")
        resp = api_client.get(f"{self.url_list}?entity=jur")
        assert len(resp.data["results"]) == 1

    def test_search_by_inn(self, api_client):
        _superuser(api_client)
        ClientFactory(full_name="Иванов", inn="301234567")
        ClientFactory(full_name="Петров", inn="404055555")
        resp = api_client.get(f"{self.url_list}?search=3012")
        assert len(resp.data["results"]) == 1

    def test_manager_name_denormalised(self, api_client):
        _superuser(api_client)
        manager = StaffFactory(full_name="Анна Сидорова", password="x12345678")
        c = ClientFactory(manager=manager)
        resp = api_client.get(reverse("client-detail", args=[c.id]))
        assert resp.data["manager_name"] == "Анна Сидорова"


# --- ClientContact --------------------------------------------------------


@pytest.mark.django_db
class TestClientContactCRUD:
    url_list = reverse("client-contact-list")

    def test_create(self, api_client):
        _superuser(api_client)
        client = ClientFactory()
        payload = {
            "client": client.id,
            "full_name": "Директор Д.Д.",
            "role": "директор",
            "is_chief": True,
            "phones": ["+998905556677"],
            "passport": {
                "series": "AB",
                "number": "1234567",
                "issued_by": "ОВД Чиланзарского района",
                "issued_date": "2019-05-12",
            },
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        contact = ClientContact.objects.get(id=resp.data["id"])
        assert contact.passport["series"] == "AB"

    def test_scoped_permission(self, api_client):
        role = RoleFactory(
            code="contact-editor",
            permissions=_scoped("clients.contacts.view", "clients.contacts.create"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        client = ClientFactory()
        payload = {"client": client.id, "full_name": "X"}
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_filter_by_client(self, api_client):
        _superuser(api_client)
        a = ClientFactory()
        b = ClientFactory()
        ClientContactFactory.create_batch(2, client=a)
        ClientContactFactory(client=b)
        resp = api_client.get(f"{self.url_list}?client={a.id}")
        assert len(resp.data["results"]) == 2

    def test_cascade_delete_on_client(self, api_client):
        """ClientContact has on_delete=CASCADE, so deleting the client
        removes every contact under it."""
        client = ClientFactory()
        ClientContactFactory.create_batch(3, client=client)
        assert ClientContact.objects.filter(client=client).count() == 3
        client.delete()
        assert ClientContact.objects.filter(client_id=client.id).count() == 0


# --- Requisite ------------------------------------------------------------


@pytest.mark.django_db
class TestRequisiteCRUD:
    url_list = reverse("client-requisite-list")

    def test_create(self, api_client):
        _superuser(api_client)
        client = ClientFactory()
        payload = {
            "client": client.id,
            "type": "local",
            "bank_requisite": {
                "account": "2020...",
                "bank": "Hamkorbank",
                "mfo": "00449",
            },
        }
        resp = api_client.post(self.url_list, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        r = Requisite.objects.get(id=resp.data["id"])
        assert r.bank_requisite["mfo"] == "00449"

    def test_filter_by_type(self, api_client):
        _superuser(api_client)
        RequisiteFactory(type="local")
        RequisiteFactory(type="internal")
        RequisiteFactory(type="local")
        resp = api_client.get(f"{self.url_list}?type=local")
        assert len(resp.data["results"]) == 2


# --- ClientStatus / ClientGroup ------------------------------------------


@pytest.mark.django_db
class TestClientLookups:
    def test_status_crud(self, api_client):
        _superuser(api_client)
        payload = {"name": {"ru": "Лид", "uz": "Lid", "oz": "Лид"}, "color": "#888"}
        resp = api_client.post(reverse("client-status-list"), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert ClientStatus.objects.filter(id=resp.data["id"]).exists()

    def test_status_scoped_permission(self, api_client):
        role = RoleFactory(
            code="status-viewer",
            permissions=_scoped("clients.statuses.view"),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        ClientStatusFactory.create_batch(2)
        resp = api_client.get(reverse("client-status-list"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_group_create(self, api_client):
        _superuser(api_client)
        payload = {"name": {"ru": "VIP", "uz": "VIP", "oz": "VIP"}}
        resp = api_client.post(reverse("client-group-list"), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_client_links_status_and_groups(self, api_client):
        _superuser(api_client)
        st = ClientStatusFactory()
        g1 = ClientGroupFactory()
        g2 = ClientGroupFactory()
        payload = {
            "entity": "phys",
            "full_name": "Тест",
            "status": st.id,
            "groups": [g1.id, g2.id],
        }
        resp = api_client.post(reverse("client-list"), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        c = Client.objects.get(id=resp.data["id"])
        assert c.status == st
        assert set(c.groups.all()) == {g1, g2}
