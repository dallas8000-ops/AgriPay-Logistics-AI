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
        if provider == Payment.Provider.MTN_MOMO:
            result = MobileMoneyService.initiate_mtn_payment(payment, phone)
        elif provider == Payment.Provider.AIRTEL_MONEY:
            result = MobileMoneyService.initiate_airtel_payment(payment, phone)
        elif provider == Payment.Provider.STRIPE:
            result = StripeService.create_payment_intent(payment)
        elif provider == Payment.Provider.MPESA:
            result = MobileMoneyService.initiate_mtn_payment(payment, phone)
        else:
            result = MobileMoneyService.initiate_mtn_payment(payment, phone)
        return Response(
            {"payment": PaymentSerializer(payment).data, "checkout": result},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        payment = self.get_object()
        if payment.provider == Payment.Provider.STRIPE:
            complete_payment(payment)
        else:
            MobileMoneyService.confirm_sandbox_payment(payment)
            complete_payment(payment)
        return Response(PaymentSerializer(payment).data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def config(self, request):
        return Response(
            {
                "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
                "providers": [
                    {"id": "mtn_momo", "name": "MTN Mobile Money", "countries": ["UG", "RW"]},
                    {"id": "airtel_money", "name": "Airtel Money", "countries": ["UG", "KE", "TZ", "RW"]},
                    {"id": "mpesa", "name": "M-Pesa", "countries": ["KE", "TZ"]},
                    {"id": "stripe", "name": "Stripe (International)", "countries": ["UG", "KE", "TZ", "RW"]},
                ],
                "currencies": {code: c["currency"] for code, c in settings.SUPPORTED_COUNTRIES.items()},
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
