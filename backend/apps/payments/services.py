import uuid

from django.conf import settings

import stripe


def get_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


class MobileMoneyService:
    """Sandbox structure for MTN MoMo and Airtel Money."""

    @staticmethod
    def initiate_mtn_payment(payment, phone: str) -> dict:
        reference = f"MTN-{payment.id.hex[:12].upper()}"
        payment.external_reference = reference
        payment.status = payment.Status.PROCESSING
        payment.phone_number = phone
        payment.save()
        return {
            "reference": reference,
            "status": "processing",
            "message": "USSD prompt sent to phone (sandbox simulation)",
            "sandbox": True,
            "provider": "mtn_momo",
        }

    @staticmethod
    def initiate_airtel_payment(payment, phone: str) -> dict:
        reference = f"AIRTEL-{payment.id.hex[:12].upper()}"
        payment.external_reference = reference
        payment.status = payment.Status.PROCESSING
        payment.phone_number = phone
        payment.save()
        return {
            "reference": reference,
            "status": "processing",
            "message": "Airtel Money request initiated (sandbox simulation)",
            "sandbox": True,
            "provider": "airtel_money",
        }

    @staticmethod
    def confirm_sandbox_payment(payment) -> dict:
        payment.status = payment.Status.COMPLETED
        payment.save()
        payment.order.status = payment.order.Status.PAID
        payment.order.save(update_fields=["status"])
        return {"status": "completed", "reference": payment.external_reference}


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
        payment.save()
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        }

    @staticmethod
    def _sandbox_intent(payment) -> dict:
        ref = f"pi_sandbox_{uuid.uuid4().hex[:16]}"
        payment.stripe_payment_intent_id = ref
        payment.external_reference = ref
        payment.status = payment.Status.PROCESSING
        payment.save()
        return {
            "client_secret": f"{ref}_secret_sandbox",
            "payment_intent_id": ref,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY or "pk_test_sandbox",
            "sandbox": True,
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
