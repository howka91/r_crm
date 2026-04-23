"""Tests for the per-project contract-number minting service."""
from __future__ import annotations

import pytest

from apps.contracts.services.numbering import mint_contract_number
from apps.objects.models import Project
from apps.objects.tests.factories import ProjectFactory


@pytest.mark.django_db
class TestMintContractNumber:
    def test_first_number_starts_at_00001(self):
        project = ProjectFactory(contract_number_prefix="ЯМ")
        number = mint_contract_number(project)
        assert number == "ЯМ-00001"
        project.refresh_from_db()
        assert project.contract_number_index == 1

    def test_sequential_mints_in_same_project(self):
        project = ProjectFactory(contract_number_prefix="ЯМ")
        assert mint_contract_number(project) == "ЯМ-00001"
        assert mint_contract_number(project) == "ЯМ-00002"
        assert mint_contract_number(project) == "ЯМ-00003"
        project.refresh_from_db()
        assert project.contract_number_index == 3

    def test_counters_are_scoped_per_project(self):
        a = ProjectFactory(contract_number_prefix="A")
        b = ProjectFactory(contract_number_prefix="B")
        assert mint_contract_number(a) == "A-00001"
        assert mint_contract_number(b) == "B-00001"
        assert mint_contract_number(a) == "A-00002"
        assert mint_contract_number(b) == "B-00002"

    def test_empty_prefix_emits_plain_zero_padded_number(self):
        project = ProjectFactory(contract_number_prefix="")
        assert mint_contract_number(project) == "00001"
        assert mint_contract_number(project) == "00002"

    def test_mint_preserves_other_project_fields(self):
        project = ProjectFactory(
            contract_number_prefix="X",
            address="ул. Тестовая, 1",
        )
        mint_contract_number(project)
        project.refresh_from_db()
        assert project.address == "ул. Тестовая, 1"
        assert project.contract_number_index == 1

    def test_existing_index_continues_from_there(self):
        project = ProjectFactory(contract_number_prefix="X")
        Project.objects.filter(pk=project.pk).update(contract_number_index=42)
        project.refresh_from_db()
        assert mint_contract_number(project) == "X-00043"
