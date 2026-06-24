"""Security regression tests for payment webhooks.

These tests encode the exploit that the webhook hardening closes: a forged
provider callback must not be able to mark a Payment COMPLETED (which would
release goods/funds for free).
"""

from __future__ import annotations

from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

import apps.payments.views  # noqa: F401  (ensures mock.patch can resolve the module)
from apps.payments.models import Payment


pytestmark = pytest.mark.django_db


def _make_payment(django_user_model, **overrides):
    user = django_user_model.objects.create_user(
        username=overrides.pop("username", "buyer1"),
        password="x",
    )
    defaults = dict(
        payer=user,
        amount="100.00",
        currency="UGX",
        provider=Payment.Provider.MTN_MOMO,
        external_reference="REF-TEST-1",
        status=Payment.Status.PENDING,
    )
    defaults.update(overrides)
    return Payment.objects.create(**defaults)


class TestMtnWebhookCannotBeForged:
    def test_body_status_alone_does_not_complete_payment(
        self, django_user_model, settings
    ):
        """A forged 'SUCCESSFUL' body must not complete the payment when MTN
        cannot be queried to confirm it."""
        settings.MTN_MOMO_API_USER = ""  # not configured -> cannot confirm
        payment = _make_payment(django_user_model)
        client = APIClient()

        resp = client.post(
            "/api/payments/webhook/mtn/",
            {"referenceId": payment.external_reference, "status": "SUCCESSFUL"},
            format="json",
        )

        payment.refresh_from_db()
        assert resp.status_code in (200, 403)
        assert payment.status != Payment.Status.COMPLETED

    @mock.patch("apps.payments.mobile_money.mtn.MTNMoMoClient.get_transaction_status")
    @mock.patch("apps.payments.mobile_money.mtn.MTNMoMoClient.is_configured", return_value=True)
    def test_completes_only_when_provider_confirms(
        self, _cfg, mock_status, django_user_model, settings
    ):
        settings.MTN_MOMO_WEBHOOK_IPS = ""  # allowlist not enforced for this test
        payment = _make_payment(django_user_model, username="buyer2")
        mock_status.return_value = {"status": "SUCCESSFUL"}
        client = APIClient()

        resp = client.post(
            "/api/payments/webhook/mtn/",
            {"referenceId": payment.external_reference, "status": "FAILED"},
            format="json",
        )

        payment.refresh_from_db()
        assert resp.status_code == 200
        # Body said FAILED but provider query said SUCCESSFUL -> trust provider.
        assert payment.status == Payment.Status.COMPLETED


class TestFlutterwaveSignature:
    def test_invalid_signature_rejected(self, django_user_model, settings):
        settings.FLUTTERWAVE_WEBHOOK_SECRET = "the-real-secret"
        payment = _make_payment(
            django_user_model, username="buyer3", provider=Payment.Provider.FLUTTERWAVE,
        )
        client = APIClient()

        resp = client.post(
            "/api/payments/webhook/flutterwave/",
            {"data": {"tx_ref": payment.external_reference, "status": "successful"}},
            format="json",
            HTTP_VERIF_HASH="wrong-secret",
        )

        payment.refresh_from_db()
        assert resp.status_code == 401
        assert payment.status != Payment.Status.COMPLETED


class TestMpesaIdempotency:
    def test_already_completed_payment_not_reprocessed(
        self, django_user_model, settings
    ):
        settings.MPESA_WEBHOOK_IPS = ""
        payment = _make_payment(
            django_user_model,
            username="buyer4",
            provider=Payment.Provider.MPESA,
            external_reference="CHECKOUT-1",
            status=Payment.Status.COMPLETED,
        )
        client = APIClient()

        with mock.patch("apps.payments.views.complete_payment") as done:
            resp = client.post(
                "/api/payments/webhook/mpesa/",
                {"Body": {"stkCallback": {"CheckoutRequestID": "CHECKOUT-1", "ResultCode": 0}}},
                format="json",
            )

        assert resp.status_code == 200
        done.assert_not_called()  # idempotent: no double fulfilment
