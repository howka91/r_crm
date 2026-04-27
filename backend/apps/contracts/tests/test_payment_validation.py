"""Tests for cross-field validation in PaymentSerializer."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.contracts.models import Payment
from apps.contracts.tests.factories import PaymentFactory, PaymentScheduleFactory
from apps.users.tests.factories import StaffFactory


def _superuser(api_client):
    admin = StaffFactory(is_superuser=True, is_staff=True, password="x12345678")
    api_client.force_authenticate(admin)
    return admin


@pytest.mark.django_db
class TestPaymentBarterValidation:
    url_list = reverse("payment-list")

    def _payload(self, schedule, **overrides):
        data = {
            "schedule": schedule.id,
            "amount": "10000.00",
            "payment_type": Payment.Type.CASH,
            "paid_at": "2026-04-27",
            "comment": "",
        }
        data.update(overrides)
        return data

    def test_barter_without_comment_400(self, api_client):
        _superuser(api_client)
        sch = PaymentScheduleFactory()
        resp = api_client.post(
            self.url_list,
            self._payload(sch, payment_type=Payment.Type.BARTER, comment=""),
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "comment" in resp.data

    def test_barter_with_whitespace_only_comment_400(self, api_client):
        _superuser(api_client)
        sch = PaymentScheduleFactory()
        resp = api_client.post(
            self.url_list,
            self._payload(sch, payment_type=Payment.Type.BARTER, comment="   \n\t  "),
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "comment" in resp.data

    def test_barter_with_comment_201(self, api_client):
        _superuser(api_client)
        sch = PaymentScheduleFactory()
        resp = api_client.post(
            self.url_list,
            self._payload(
                sch,
                payment_type=Payment.Type.BARTER,
                comment="2 кондиционера + холодильник",
            ),
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_cash_without_comment_201(self, api_client):
        _superuser(api_client)
        sch = PaymentScheduleFactory()
        resp = api_client.post(
            self.url_list,
            self._payload(sch, payment_type=Payment.Type.CASH, comment=""),
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_bank_without_comment_201(self, api_client):
        _superuser(api_client)
        sch = PaymentScheduleFactory()
        resp = api_client.post(
            self.url_list,
            self._payload(sch, payment_type=Payment.Type.BANK, comment=""),
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

    def test_patch_clearing_comment_on_barter_400(self, api_client):
        """Existing barter payment can't have its comment blanked via PATCH."""
        _superuser(api_client)
        payment = PaymentFactory(
            payment_type=Payment.Type.BARTER, comment="мебель",
            amount=Decimal("10000.00"),
        )
        url = reverse("payment-detail", args=[payment.id])
        resp = api_client.patch(url, {"comment": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "comment" in resp.data
