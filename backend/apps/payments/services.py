import uuid

from django.conf import settings

import stripe

from .mobile_money import MobileMoneyService

__all__ = ["MobileMoneyService", "StripeService", "get_stripe"]


def get_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


class StripeService:
    @staticmethod
    def create_payment_intent(payment) -> dict:
        stripe_client = get_stripe()
        if not settings.STRIPE_SECRET_KEY:
            return StripeService._sandbox_intent(payment)
        intent = stripe_client.PaymentIntent.create(
            amount=int(payment.amount * 100),
            currency=payment.currency.lower(),
            metadata={"order_id": str(payment.order_id), "payment_id": str(payment.id)},
            automatic_payment_methods={"enabled": True},
        )
        payment.stripe_payment_intent_id = intent.id
        payment.external_reference = intent.id
        payment.status = payment.Status.PROCESSING
        payment.metadata = {
            **(payment.metadata or {}),
            "integration_mode": "live",
        }
        payment.save()
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "integration_mode": "live",
        }

    @staticmethod
    def _sandbox_intent(payment) -> dict:
        ref = f"pi_sandbox_{uuid.uuid4().hex[:16]}"
        payment.stripe_payment_intent_id = ref
        payment.external_reference = ref
        payment.status = payment.Status.PROCESSING
        payment.metadata = {
            **(payment.metadata or {}),
            "integration_mode": "simulated",
        }
        payment.save()
        return {
            "client_secret": f"{ref}_secret_sandbox",
            "payment_intent_id": ref,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY or "pk_test_sandbox",
            "integration_mode": "simulated",
            "requires_manual_confirm": True,
        }

    @staticmethod
    def handle_webhook(payload, sig_header):
        stripe_client = get_stripe()
        if not settings.STRIPE_WEBHOOK_SECRET:
            return None
        event = stripe_client.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
