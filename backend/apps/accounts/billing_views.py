"""Subscription billing endpoints.

Model: the organization owner is billed (active member count x per-user fee)
each month. Local owners settle via Flutterwave (mobile money + card);
international owners via Stripe. The Organization is the billing subject.

These endpoints reuse the existing, already-hardened Payment + webhook flow so
that subscription collections inherit the same signature verification and
idempotency as marketplace payments.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OrganizationMembership


def _owner_membership(user):
    membership = getattr(user, "membership", None)
    if membership is None:
        return None
    if membership.role not in (
        OrganizationMembership.Role.OWNER,
        OrganizationMembership.Role.ADMIN,
    ):
        return None
    return membership


class BillingSummaryView(APIView):
    """Show the org's current monthly bill: users x per-user fee."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership = getattr(request.user, "membership", None)
        if membership is None:
            return Response({"detail": "You are not part of an organization."}, status=404)
        org = membership.organization
        fee = Decimal(str(settings.SUBSCRIPTION_FEE_PER_USER))
        return Response(
            {
                "organization": org.name,
                "billing_status": org.billing_status,
                "per_user_fee": str(fee),
                "currency": settings.BILLING_CURRENCY,
                "billable_users": org.billable_users,
                "monthly_total": str(org.monthly_bill()),
                "paid_through": org.paid_through,
                "your_role": membership.role,
                "can_pay": membership.role
                in (OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN),
            }
        )


class BillingChargeView(APIView):
    """Initiate payment of the current monthly bill.

    processor=flutterwave (default, local mobile money + card) or stripe
    (international card). Only an owner/admin can pay for the org. Reuses the
    Payment model so the existing webhook flow confirms and records it.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        membership = _owner_membership(request.user)
        if membership is None:
            return Response(
                {"detail": "Only an owner or admin can pay the organization bill."},
                status=403,
            )
        org = membership.organization
        amount = org.monthly_bill()
        if amount <= 0:
            return Response({"detail": "Nothing to bill (no active users)."}, status=400)

        processor = (request.data.get("processor") or "flutterwave").lower()
        currency = settings.BILLING_CURRENCY

        from apps.payments.models import Payment

        payment = Payment.objects.create(
            payer=request.user,
            amount=amount,
            currency=currency,
            provider=(
                Payment.Provider.STRIPE
                if processor == "stripe"
                else Payment.Provider.FLUTTERWAVE
            ),
            metadata={"kind": "subscription", "organization_id": org.pk},
        )

        if processor == "stripe":
            from apps.payments.services import StripeService

            result = StripeService.create_payment_intent(payment)
            return Response(
                {"processor": "stripe", "payment_id": payment.pk, **result}
            )

        from apps.payments.aggregator.flutterwave import FlutterwaveClient

        client = FlutterwaveClient()
        tx_ref = FlutterwaveClient.new_tx_ref("sub")
        payment.external_reference = tx_ref
        payment.save(update_fields=["external_reference"])

        if not client.is_configured():
            return Response(
                {
                    "processor": "flutterwave",
                    "payment_id": payment.pk,
                    "integration_mode": "simulated",
                    "detail": (
                        "Flutterwave not configured. Set FLUTTERWAVE_SECRET_KEY to "
                        "collect real subscription payments."
                    ),
                    "amount": str(amount),
                    "currency": currency,
                },
                status=200,
            )

        result = client.initiate_standard_payment(
            tx_ref=tx_ref,
            amount=amount,
            currency=currency,
            customer_name=request.user.get_full_name() or request.user.username,
            customer_email=request.user.email,
            customer_phone=getattr(request.user, "phone", ""),
            title="AgriPay subscription",
            description=f"{org.billable_users} users x {settings.SUBSCRIPTION_FEE_PER_USER} {currency}",
            redirect_url=settings.BILLING_REDIRECT_URL,
        )
        return Response({"processor": "flutterwave", "payment_id": payment.pk, **result})
