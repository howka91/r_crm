"""Tests for the Contract.action state machine in
:mod:`apps.contracts.services.transitions`.
"""
from __future__ import annotations

import pytest

from apps.contracts.models import Contract
from apps.contracts.services.transitions import (
    TransitionError,
    approve,
    request_edit,
    send_to_wait,
    sign,
)
from apps.contracts.tests.factories import ContractFactory
from apps.users.tests.factories import StaffFactory


# --- send_to_wait --------------------------------------------------------


@pytest.mark.django_db
class TestSendToWait:
    def test_request_to_wait_mints_number(self):
        actor = StaffFactory()
        c = ContractFactory(contract_number="")
        c.project.contract_number_prefix = "ЯМ"
        c.project.save(update_fields=["contract_number_prefix"])
        assert c.action == Contract.Action.REQUEST

        result = send_to_wait(c, actor)
        assert result.new_action == Contract.Action.WAIT
        assert result.previous_action == Contract.Action.REQUEST
        assert result.minted_number == "ЯМ-00001"

        c.refresh_from_db()
        assert c.action == Contract.Action.WAIT
        assert c.contract_number == "ЯМ-00001"

    def test_resubmit_from_edit_does_not_remint(self):
        """After an edit cycle, re-submit keeps the original number."""
        actor = StaffFactory()
        c = ContractFactory(contract_number="")
        c.project.contract_number_prefix = "C"
        c.project.save(update_fields=["contract_number_prefix"])

        # First send: mints.
        send_to_wait(c, actor)
        c.refresh_from_db()
        first_number = c.contract_number
        assert first_number == "C-00001"

        # Go into edit, then back to wait.
        request_edit(c, actor)
        c.refresh_from_db()
        assert c.action == Contract.Action.EDIT

        result = send_to_wait(c, actor)
        assert result.minted_number is None  # nothing new minted
        c.refresh_from_db()
        assert c.contract_number == first_number
        assert c.action == Contract.Action.WAIT

    def test_illegal_from_approve(self):
        c = ContractFactory()
        c.action = Contract.Action.APPROVE
        c.save(update_fields=["action"])
        with pytest.raises(TransitionError) as exc:
            send_to_wait(c, StaffFactory())
        assert exc.value.current == Contract.Action.APPROVE
        assert exc.value.target == Contract.Action.WAIT


# --- approve -------------------------------------------------------------


@pytest.mark.django_db
class TestApprove:
    def test_wait_to_approve(self):
        c = ContractFactory()
        c.action = Contract.Action.WAIT
        c.save(update_fields=["action"])
        result = approve(c, StaffFactory())
        assert result.new_action == Contract.Action.APPROVE
        c.refresh_from_db()
        assert c.action == Contract.Action.APPROVE
        assert c.is_signed is False  # approve ≠ sign

    def test_illegal_from_request(self):
        c = ContractFactory()  # defaults to REQUEST
        with pytest.raises(TransitionError):
            approve(c, StaffFactory())


# --- sign ----------------------------------------------------------------


@pytest.mark.django_db
class TestSign:
    def test_approve_to_sign_in_flips_is_signed(self):
        c = ContractFactory()
        c.action = Contract.Action.APPROVE
        c.save(update_fields=["action"])
        result = sign(c, StaffFactory())
        assert result.new_action == Contract.Action.SIGN_IN
        c.refresh_from_db()
        assert c.action == Contract.Action.SIGN_IN
        assert c.is_signed is True

    def test_signed_is_terminal(self):
        c = ContractFactory()
        c.action = Contract.Action.APPROVE
        c.save(update_fields=["action"])
        sign(c, StaffFactory())
        c.refresh_from_db()
        # No further transitions legal.
        with pytest.raises(TransitionError):
            sign(c, StaffFactory())
        with pytest.raises(TransitionError):
            approve(c, StaffFactory())


# --- request_edit --------------------------------------------------------


@pytest.mark.django_db
class TestRequestEdit:
    def test_wait_to_edit_snapshots_document(self):
        actor = StaffFactory(full_name="Rev-Manager")
        c = ContractFactory(document={"price": "750000000", "signer": "X"})
        c.action = Contract.Action.WAIT
        c.save(update_fields=["action"])

        result = request_edit(c, actor, reason="Update signer data")
        assert result.new_action == Contract.Action.EDIT
        c.refresh_from_db()
        assert c.action == Contract.Action.EDIT
        assert len(c.old) == 1
        snap = c.old[0]
        assert snap["document"] == {"price": "750000000", "signer": "X"}
        assert snap["reason"] == "Update signer data"
        assert snap["actor_id"] == str(actor.id)
        assert "snapshot_at" in snap

    def test_repeated_edits_append_to_old(self):
        c = ContractFactory(document={"v": 1})
        c.action = Contract.Action.WAIT
        c.save(update_fields=["action"])
        actor = StaffFactory()
        request_edit(c, actor, reason="first")
        # simulate a cycle back to wait + document change
        c.refresh_from_db()
        c.action = Contract.Action.WAIT
        c.document = {"v": 2}
        c.save(update_fields=["action", "document"])
        request_edit(c, actor, reason="second")
        c.refresh_from_db()
        assert len(c.old) == 2
        assert c.old[0]["document"] == {"v": 1}
        assert c.old[1]["document"] == {"v": 2}

    def test_illegal_from_request(self):
        c = ContractFactory()  # REQUEST
        with pytest.raises(TransitionError):
            request_edit(c, StaffFactory())
