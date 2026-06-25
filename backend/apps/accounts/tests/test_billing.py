"""Tests for the billing model:
- Flat subscription fee per organization (does NOT scale with user count).
- Transaction fee paid by the sender (pass-through of rail cost; markup 0).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import (
    Organization,
    OrganizationMembership,
    add_member_to_organization,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


def _user(name):
    return User.objects.create_user(username=name, password="pw-12345678")


class TestPerUserSubscription:
    def test_bill_scales_with_users(self, settings):
        settings.SUBSCRIPTION_FEE_PER_USER = "20.00"
        org = Organization.objects.create(name="Acme")
        for i in range(8):
            add_member_to_organization(org, _user(f"u{i}"))
        assert org.billable_users == 8
        assert org.monthly_bill() == Decimal("160.00")

    def test_twenty_users_pay_four_hundred(self, settings):
        """The exact case that must never be a loss: 20 users x $20 = $400."""
        settings.SUBSCRIPTION_FEE_PER_USER = "20.00"
        org = Organization.objects.create(name="BigClient")
        for i in range(20):
            add_member_to_organization(org, _user(f"big{i}"))
        assert org.billable_users == 20
        assert org.monthly_bill() == Decimal("400.00")

    def test_summary_endpoint_reports_per_user(self, settings):
        settings.SUBSCRIPTION_FEE_PER_USER = "20.00"
        client = APIClient()
        client.post(
            "/api/auth/register/",
            {"username": "owner", "password": "pw-12345678", "organization_name": "Acme"},
            format="json",
        )
        token = client.post(
            "/api/auth/token/",
            {"username": "owner", "password": "pw-12345678"},
            format="json",
        ).data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = client.get("/api/auth/billing/")
        assert r.status_code == 200
        # Owner only so far -> 1 user x $20.
        assert r.data["per_user_fee"] == "20.00"
        assert r.data["billable_users"] == 1
        assert r.data["monthly_total"] == "20.00"


class TestTransactionFee:
    def test_passthrough_only_by_default(self, settings):
        from apps.payments.fees import fee_breakdown, total_with_fee, transaction_fee

        settings.TRANSACTION_FEE_ENABLED = True
        settings.TRANSACTION_FEE_FLAT = "0.99"
        settings.TRANSACTION_FEE_MARKUP = "0.00"

        assert transaction_fee() == Decimal("0.99")
        # Sender pays base + the rail fee; no platform margin.
        assert total_with_fee(Decimal("100.00")) == Decimal("100.99")
        bd = fee_breakdown()
        assert bd["rail_fee"] == "0.99"
        assert bd["platform_markup"] == "0.00"
        assert bd["total_fee"] == "0.99"

    def test_markup_adds_to_fee_when_set(self, settings):
        from apps.payments.fees import transaction_fee

        settings.TRANSACTION_FEE_ENABLED = True
        settings.TRANSACTION_FEE_FLAT = "0.99"
        settings.TRANSACTION_FEE_MARKUP = "0.50"
        assert transaction_fee() == Decimal("1.49")

    def test_disabled_means_no_fee(self, settings):
        from apps.payments.fees import total_with_fee, transaction_fee

        settings.TRANSACTION_FEE_ENABLED = False
        assert transaction_fee() == Decimal("0.00")
        assert total_with_fee(Decimal("100.00")) == Decimal("100.00")

    def test_fee_exposed_in_payment_config(self, settings):
        settings.TRANSACTION_FEE_ENABLED = True
        settings.TRANSACTION_FEE_FLAT = "0.99"
        settings.TRANSACTION_FEE_MARKUP = "0.00"
        client = APIClient()
        r = client.get("/api/payments/config/")
        assert r.status_code == 200
        assert r.data["transaction_fee"]["total_fee"] == "0.99"


class TestSubscriptionActivation:
    def test_completed_subscription_payment_activates_org(self, settings):
        from apps.payments.helpers import complete_payment
        from apps.payments.models import Payment

        org = Organization.objects.create(name="Acme")
        owner = _user("owner4")
        add_member_to_organization(org, owner, role=OrganizationMembership.Role.OWNER)

        payment = Payment.objects.create(
            payer=owner,
            amount=Decimal("20.00"),
            currency="USD",
            provider=Payment.Provider.FLUTTERWAVE,
            external_reference="sub-xyz",
            status=Payment.Status.PENDING,
            metadata={"kind": "subscription", "organization_id": org.pk},
        )
        complete_payment(payment)

        org.refresh_from_db()
        assert org.billing_status == Organization.BillingStatus.ACTIVE
        assert org.paid_through is not None
