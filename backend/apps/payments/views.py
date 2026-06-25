from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.marketplace.models import Order

from .helpers import complete_payment
from .models import Payment
from .serializers import PaymentSerializer
from .services import MobileMoneyService, StripeService
from .webhook_security import already_processed, constant_time_equal, ip_allowed


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Payment.objects.filter(payer=self.request.user)

    def create(self, request, *args, **kwargs):
        order_id = request.data.get("order_id")
        provider = request.data.get("provider", Payment.Provider.MTN_MOMO)
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        if order.status != Order.Status.PENDING:
            return Response({"detail": "Order is not pending payment"}, status=400)

        payment = Payment.objects.create(
            order=order,
            payer=request.user,
            amount=order.total_amount,
            currency=order.currency,
            provider=provider,
        )
        phone = request.data.get("phone_number", request.user.phone)
        modes = MobileMoneyService.provider_modes()

        if provider == Payment.Provider.STRIPE:
            if not settings.STRIPE_SECRET_KEY:
                payment.delete()
                return Response(
                    {
                        "detail": (
                            "Stripe is not configured. Use personal transfer collection "
                            "or set STRIPE_SECRET_KEY."
                        )
                    },
                    status=503,
                )
        elif modes.get(provider) != "live" and not settings.DEBUG:
            payment.delete()
            return Response(
                {
                    "detail": (
                        "Merchant mobile money API is not configured for this provider. "
                        "Use GET /api/payments/collect/instructions/ for personal-number collection."
                    )
                },
                status=503,
            )

        try:
            if provider == Payment.Provider.MTN_MOMO:
                result = MobileMoneyService.initiate_mtn_payment(payment, phone)
            elif provider == Payment.Provider.AIRTEL_MONEY:
                result = MobileMoneyService.initiate_airtel_payment(payment, phone)
            elif provider == Payment.Provider.MPESA:
                result = MobileMoneyService.initiate_mpesa_payment(payment, phone)
            elif provider == Payment.Provider.STRIPE:
                result = StripeService.create_payment_intent(payment)
            else:
                return Response({"detail": "Unsupported payment provider"}, status=400)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=502)

        return Response(
            {"payment": PaymentSerializer(payment).data, "checkout": result},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        payment = self.get_object()
        if payment.provider == Payment.Provider.STRIPE:
            complete_payment(payment)
            return Response(PaymentSerializer(payment).data)

        mode = (payment.metadata or {}).get("integration_mode", "simulated")
        if mode != "simulated":
            return Response(
                {
                    "detail": (
                        "Live mobile money payments cannot be confirmed manually. "
                        "Poll /status/ or wait for the provider callback."
                    )
                },
                status=400,
            )
        MobileMoneyService.confirm_simulated_payment(payment)
        complete_payment(payment)
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        payment = self.get_object()
        if payment.provider == Payment.Provider.STRIPE:
            return Response(
                {
                    "status": payment.status,
                    "integration_mode": (payment.metadata or {}).get("integration_mode", "live"),
                }
            )
        try:
            payload = MobileMoneyService.sync_provider_status(payment)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=502)

        if payment.status == Payment.Status.COMPLETED:
            complete_payment(payment)

        return Response({**payload, "payment": PaymentSerializer(payment).data})

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def config(self, request):
        from .fees import fee_breakdown

        modes = MobileMoneyService.provider_modes()
        stripe_mode = "live" if settings.STRIPE_SECRET_KEY else "simulated"
        return Response(
            {
                "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
                "stripe_integration_mode": stripe_mode,
                "default_collection_mode": "personal_transfer",
                "personal_transfer_description": (
                    "Collect to your personal MTN/Airtel/M-Pesa number — no merchant account required. "
                    "Reconcile via SMS paste or buyer payment claims."
                ),
                "providers": [
                    {
                        "id": "mtn_momo",
                        "name": "MTN Mobile Money",
                        "countries": ["UG", "RW"],
                        "integration_mode": modes[Payment.Provider.MTN_MOMO],
                    },
                    {
                        "id": "airtel_money",
                        "name": "Airtel Money",
                        "countries": ["UG", "KE", "TZ", "RW"],
                        "integration_mode": modes[Payment.Provider.AIRTEL_MONEY],
                    },
                    {
                        "id": "mpesa",
                        "name": "M-Pesa",
                        "countries": ["KE", "TZ"],
                        "integration_mode": modes[Payment.Provider.MPESA],
                    },
                    {
                        "id": "stripe",
                        "name": "Stripe (International)",
                        "countries": ["UG", "KE", "TZ", "RW"],
                        "integration_mode": stripe_mode,
                    },
                ],
                "currencies": {code: c["currency"] for code, c in settings.SUPPORTED_COUNTRIES.items()},
                "transaction_fee": fee_breakdown(),
            }
        )


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = StripeService.handle_webhook(request.body, sig)
    except Exception as exc:
        return Response({"error": str(exc)}, status=400)
    if event and event["type"] == "payment_intent.succeeded":
        intent_id = event["data"]["object"]["id"]
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=intent_id)
            complete_payment(payment)
        except Payment.DoesNotExist:
            pass
    return Response({"received": True})


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mtn_momo_webhook(request):
    """MTN MoMo collection callback.

    MTN does not sign callbacks, so the request body is NOT trusted. We only use
    it to learn which reference changed, then re-confirm the real status by
    querying MTN's own transaction-status API before completing anything.
    """
    if not ip_allowed(request, "MTN_MOMO_WEBHOOK_IPS"):
        return Response({"error": "Forbidden"}, status=403)

    ref = request.headers.get("X-Reference-Id") or request.data.get("referenceId")
    if not ref:
        return Response({"received": True})

    payment = Payment.objects.filter(external_reference=ref).first()
    if not payment:
        payment = Payment.objects.filter(metadata__mtn_reference_id=ref).first()
    if not payment:
        return Response({"received": True})

    if already_processed(payment):
        return Response({"received": True})

    # Re-confirm against MTN rather than trusting request body status.
    from apps.payments.mobile_money.mtn import MTNMoMoClient

    client = MTNMoMoClient()
    if client.is_configured():
        try:
            result = client.get_transaction_status(ref)
            provider_status = (result or {}).get("status", "")
        except Exception:
            return Response({"received": True})
    else:
        # No credentials: cannot confirm, so do not complete. Fail closed.
        return Response({"received": True})

    MobileMoneyService._apply_provider_status(payment, provider_status)
    if payment.status == Payment.Status.COMPLETED:
        complete_payment(payment)
    return Response({"received": True})


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mpesa_webhook(request):
    """Daraja STK callback.

    Safaricom does not sign callbacks; the documented defense is to restrict to
    Safaricom's published source IPs (set MPESA_WEBHOOK_IPS) and treat the body
    as advisory. We additionally guard idempotency so a replayed callback cannot
    re-trigger fulfilment.
    """
    if not ip_allowed(request, "MPESA_WEBHOOK_IPS"):
        return Response({"error": "Forbidden"}, status=403)

    body = request.data.get("Body", {}).get("stkCallback", {})
    checkout_id = body.get("CheckoutRequestID")
    result_code = body.get("ResultCode")
    if not checkout_id:
        return Response({"received": True})

    try:
        payment = Payment.objects.get(external_reference=checkout_id)
    except Payment.DoesNotExist:
        return Response({"received": True})

    if already_processed(payment):
        return Response({"received": True})

    if result_code == 0:
        MobileMoneyService._apply_provider_status(payment, "SUCCESSFUL")
        complete_payment(payment)
    else:
        MobileMoneyService._apply_provider_status(payment, "FAILED")
    return Response({"received": True})


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def flutterwave_webhook(request):
    """Flutterwave payment callback — verifies verif-hash header when configured."""
    from apps.payments.aggregator.flutterwave import FlutterwaveClient

    client = FlutterwaveClient()
    signature = request.headers.get("verif-hash", "")
    if not client.webhook_valid(signature):
        return Response({"error": "Invalid signature"}, status=401)

    data = request.data.get("data", request.data)
    tx_ref = data.get("tx_ref") or data.get("txRef")
    status_value = (data.get("status") or "").lower()

    if not tx_ref:
        return Response({"received": True})

    payment = Payment.objects.filter(external_reference=tx_ref).first()
    if not payment:
        return Response({"received": True})

    if already_processed(payment):
        return Response({"received": True})

    if status_value == "successful":
        payment.status = Payment.Status.COMPLETED
        payment.metadata = {**(payment.metadata or {}), "flutterwave_webhook": data}
        payment.save()
        complete_payment(payment)
    elif status_value in ("failed", "cancelled"):
        payment.status = Payment.Status.FAILED
        payment.save()

    return Response({"received": True})
