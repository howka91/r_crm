"""Tests for Phase 5.3 — docgen pipeline and generate-pdf endpoint.

Covers:
    * services.snapshot.build_context — keys and fallbacks
    * services.qr — PNG + data-URI shape
    * services.docgen — placeholder substitution, unknown-key handling,
      actual WeasyPrint PDF attachment.
    * POST /contracts/:id/generate-pdf/ — happy path, template-missing,
      unknown-placeholder, blocked-on-signed.
    * ContractTemplate CRUD — global vs per-project gate, placeholders
      validation.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.contracts.models import Contract, ContractTemplate
from apps.contracts.services import docgen as docgen_svc
from apps.contracts.services.qr import make_qr_data_uri, make_qr_png
from apps.contracts.services.snapshot import build_context
from apps.contracts.tests.factories import ContractFactory, ContractTemplateFactory
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


# --- snapshot -----------------------------------------------------------


@pytest.mark.django_db
class TestBuildContext:
    def test_root_keys_present(self):
        contract = ContractFactory()
        ctx = build_context(contract)
        # All documented roots appear.
        assert set(ctx) >= {
            "contract", "apartment", "project", "developer",
            "calculation", "signer", "client", "now", "today",
        }

    def test_client_reached_via_signer(self):
        contract = ContractFactory()
        ctx = build_context(contract)
        assert ctx["signer"] is contract.signer
        assert ctx["client"] is contract.signer.client

    def test_missing_calculation_yields_none(self):
        contract = ContractFactory()
        contract.calculation = None
        contract.save(update_fields=["calculation"])
        ctx = build_context(contract)
        assert ctx["calculation"] is None


# --- qr ------------------------------------------------------------------


class TestQR:
    def test_png_starts_with_signature(self):
        png = make_qr_png("hello")
        assert png[:4] == b"\x89PNG"

    def test_data_uri_shape(self):
        uri = make_qr_data_uri("hello")
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 100


# --- docgen service -----------------------------------------------------


@pytest.mark.django_db
class TestGeneratePdf:
    def _tpl(self, **kw) -> ContractTemplate:
        return ContractTemplateFactory(
            body=kw.pop(
                "body",
                "<html><body><p>Договор №{{contract_number}} от {{date}}.</p>"
                "<p>Клиент: {{client_name}}</p><p>Квартира: {{apt_number}}</p>"
                "</body></html>",
            ),
            placeholders=kw.pop(
                "placeholders",
                [
                    {"key": "contract_number", "path": "contract.contract_number", "label": "№"},
                    {"key": "date", "path": "contract.date", "label": "Дата"},
                    {"key": "client_name", "path": "client.full_name", "label": "ФИО"},
                    {"key": "apt_number", "path": "apartment.number", "label": "Кв."},
                ],
            ),
            **kw,
        )

    def test_happy_path_attaches_pdf(self):
        contract = ContractFactory(contract_number="ЯМ-00001")
        contract.template = self._tpl()
        contract.save(update_fields=["template"])

        result = docgen_svc.generate_pdf(contract)
        contract.refresh_from_db()

        # File attached, PDF magic bytes present.
        assert contract.file, "Expected Contract.file to be populated"
        with contract.file.open("rb") as f:
            assert f.read(4) == b"%PDF"
        assert result.pdf_size > 0
        # document snapshot persisted.
        assert contract.document["template_title"] == contract.template.title
        assert contract.document["values"]["contract_number"] == "ЯМ-00001"

    def test_template_not_set_raises(self):
        contract = ContractFactory(template=None)
        with pytest.raises(docgen_svc.TemplateNotSet):
            docgen_svc.generate_pdf(contract)

    def test_unknown_placeholder_strict_raises(self):
        contract = ContractFactory()
        contract.template = self._tpl(
            body="<p>{{contract_number}} / {{mystery_key}}</p>",
            placeholders=[
                {"key": "contract_number", "path": "contract.contract_number", "label": "№"},
            ],
        )
        contract.save(update_fields=["template"])
        with pytest.raises(docgen_svc.UnknownPlaceholder) as exc:
            docgen_svc.generate_pdf(contract)
        assert "mystery_key" in exc.value.unknown

    def test_unknown_placeholder_lenient_passes_through(self):
        contract = ContractFactory()
        contract.template = self._tpl(
            body="<p>{{contract_number}} / {{mystery_key}}</p>",
            placeholders=[
                {"key": "contract_number", "path": "contract.contract_number", "label": "№"},
            ],
        )
        contract.save(update_fields=["template"])
        result = docgen_svc.generate_pdf(contract, strict=False)
        assert result.pdf_size > 0

    def test_missing_path_resolves_to_empty(self):
        """Paths that don't exist on the tree should render as "", not crash."""
        contract = ContractFactory()
        contract.template = self._tpl(
            body="<p>[{{bogus}}]</p>",
            placeholders=[
                {"key": "bogus", "path": "contract.nonexistent.field", "label": "x"},
            ],
        )
        contract.save(update_fields=["template"])
        result = docgen_svc.generate_pdf(contract)
        assert result.filled["bogus"] == ""


# --- /generate-pdf/ endpoint --------------------------------------------


@pytest.mark.django_db
class TestGeneratePdfEndpoint:
    def test_happy_path(self, api_client):
        _superuser(api_client)
        contract = ContractFactory(contract_number="ЯМ-00010")
        contract.template = ContractTemplateFactory(
            body="<p>{{n}}</p>",
            placeholders=[
                {"key": "n", "path": "contract.contract_number", "label": "№"},
            ],
        )
        contract.save(update_fields=["template"])

        resp = api_client.post(
            reverse("contract-generate-pdf", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["pdf_size"] > 0
        assert resp.data["filled"]["n"] == "ЯМ-00010"

    def test_template_not_set_returns_400(self, api_client):
        _superuser(api_client)
        contract = ContractFactory(template=None)
        resp = api_client.post(
            reverse("contract-generate-pdf", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == "template_not_set"

    def test_unknown_placeholder_returns_400(self, api_client):
        _superuser(api_client)
        contract = ContractFactory()
        contract.template = ContractTemplateFactory(
            body="<p>{{missing}}</p>",
            placeholders=[],
        )
        contract.save(update_fields=["template"])
        resp = api_client.post(
            reverse("contract-generate-pdf", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == "unknown_placeholder"
        assert "missing" in resp.data["unknown"]

    def test_blocked_on_signed_contract(self, api_client):
        _superuser(api_client)
        contract = ContractFactory(is_signed=True)
        contract.template = ContractTemplateFactory()
        contract.save(update_fields=["template"])
        resp = api_client.post(
            reverse("contract-generate-pdf", args=[contract.id]),
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


# --- ContractTemplate CRUD with global-template gate --------------------


@pytest.mark.django_db
class TestContractTemplateGate:
    url_list = reverse("contract-template-list")

    def test_scoped_user_can_create_project_template(self, api_client):
        from apps.objects.tests.factories import ProjectFactory
        role = RoleFactory(
            code="tpl-creator-project",
            permissions=_scoped(
                "references.templates.view",
                "references.templates.create",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        project = ProjectFactory()
        resp = api_client.post(
            self.url_list,
            {
                "title": "Scoped template",
                "body": "<p>x</p>",
                "project": project.id,
                "placeholders": [],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_scoped_user_blocked_from_global_template(self, api_client):
        role = RoleFactory(
            code="tpl-creator-noglobal",
            permissions=_scoped(
                "references.templates.view",
                "references.templates.create",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        resp = api_client.post(
            self.url_list,
            {"title": "Global attempt", "body": "<p>x</p>", "placeholders": []},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["code"] == "global_template_forbidden"

    def test_manage_global_role_can_create_global(self, api_client):
        role = RoleFactory(
            code="tpl-creator-global",
            permissions=_scoped(
                "references.templates.view",
                "references.templates.create",
                "references.templates.manage_global",
            ),
        )
        api_client.force_authenticate(StaffFactory(role=role, password="x12345678"))
        resp = api_client.post(
            self.url_list,
            {"title": "Global", "body": "<p>x</p>", "placeholders": []},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["is_global"] is True

    def test_superuser_bypasses_global_gate(self, api_client):
        _superuser(api_client)
        resp = api_client.post(
            self.url_list,
            {"title": "Admin global", "body": "<p>x</p>", "placeholders": []},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_placeholder_validation_rejects_missing_path(self, api_client):
        _superuser(api_client)
        resp = api_client.post(
            self.url_list,
            {
                "title": "Broken",
                "body": "<p>{{x}}</p>",
                "placeholders": [{"key": "x", "label": "no path"}],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_placeholder_validation_rejects_duplicate_keys(self, api_client):
        _superuser(api_client)
        resp = api_client.post(
            self.url_list,
            {
                "title": "Dup",
                "body": "<p>{{x}}</p>",
                "placeholders": [
                    {"key": "x", "path": "contract.id", "label": "a"},
                    {"key": "x", "path": "contract.date", "label": "b"},
                ],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
