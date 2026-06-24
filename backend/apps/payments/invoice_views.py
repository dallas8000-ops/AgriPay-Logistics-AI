from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.payments.aggregator.flutterwave import FlutterwaveClient, FlutterwaveError

from .invoice_serializers import InvoicePaySerializer, InvoiceSerializer
from .models import Invoice, Payment
from .reconciliation import build_personal_payment_instructions_for_invoice


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.role in (User.Role.FARMER, User.Role.VENDOR):
            return Invoice.objects.filter(seller=user)
        if user.role == User.Role.ADMIN:
            return Invoice.objects.all()
        return Invoice.objects.none()

    @action(detail=True, methods=["get"], url_path="instructions")
    def instructions(self, request, pk=None):
        invoice = self.get_object()
        return Response(build_personal_payment_instructions_for_invoice(invoice))

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """Flutterwave checkout when configured; otherwise returns personal-transfer instructions."""
        invoice = self.get_object()
        if invoice.status != Invoice.Status.PENDING:
            return Response({"detail": "Invoice is not pending payment."}, status=400)

        ser = InvoicePaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        redirect_url = ser.validated_data.get("redirect_url") or (
            request.headers.get("Origin", "http://127.0.0.1:5174") + f"/invoices/{invoice.pk}/paid"
        )

        client = FlutterwaveClient()
        if not client.is_configured():
            return Response(
                {
                    "detail": (
                        "Flutterwave is not configured. Use personal-transfer instructions "
                        "or set FLUTTERWAVE_SECRET_KEY."
                    ),
                    "instructions": build_personal_payment_instructions_for_invoice(invoice),
                },
                status=503,
            )

        tx_ref = FlutterwaveClient.new_tx_ref(invoice.payment_reference)
        mode = "sandbox" if client.is_test_mode() else "live"
        payment = Payment.objects.create(
            invoice=invoice,
            payer=request.user if request.user.is_authenticated else None,
            amount=invoice.amount,
            currency=invoice.currency,
            provider=Payment.Provider.FLUTTERWAVE,
            status=Payment.Status.PROCESSING,
            external_reference=tx_ref,
            metadata={"integration_mode": mode, "invoice_id": invoice.pk},
        )

        try:
            checkout = client.initiate_standard_payment(
                tx_ref=tx_ref,
                amount=invoice.amount,
                currency=invoice.currency,
                customer_name=invoice.customer_name,
                customer_email=invoice.customer_email,
                customer_phone=invoice.customer_phone,
                title=f"Invoice {invoice.payment_reference}",
                description=invoice.description[:200],
                redirect_url=redirect_url,
            )
        except FlutterwaveError as exc:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            return Response({"detail": str(exc)}, status=502)

        payment.metadata = {**(payment.metadata or {}), **checkout}
        payment.save(update_fields=["metadata"])
        invoice.collection_method = Invoice.CollectionMethod.FLUTTERWAVE
        invoice.save(update_fields=["collection_method"])

        return Response(
            {
                "payment_id": str(payment.id),
                "checkout": checkout,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="verify-payment")
    def verify_payment(self, request, pk=None):
        invoice = self.get_object()
        payment = (
            invoice.payments.filter(provider=Payment.Provider.FLUTTERWAVE)
            .order_by("-created_at")
            .first()
        )
        if not payment:
            return Response({"detail": "No Flutterwave payment found."}, status=404)

        client = FlutterwaveClient()
        try:
            result = client.verify_transaction(payment.external_reference)
        except FlutterwaveError as exc:
            return Response({"detail": str(exc)}, status=502)

        if result.get("status") == "successful":
            from .helpers import complete_invoice_payment

            complete_invoice_payment(payment)

        return Response({"verification": result, "invoice_status": invoice.status})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.get_queryset().filter(status=Invoice.Status.PENDING)
        from django.db.models import Sum

        total = qs.aggregate(t=Sum("amount"))["t"] or 0
        return Response(
            {
                "pending_count": qs.count(),
                "pending_amount": str(total),
                "currency": request.user.currency,
            }
        )


class PublicInvoiceView(APIView):
    """Public pay page — no login required for pending INV- payment instructions."""

    permission_classes = [AllowAny]

    def get(self, request, payment_reference: str):
        try:
            invoice = Invoice.objects.select_related("seller").get(
                payment_reference__iexact=payment_reference.strip(),
            )
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Payment request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invoice.status != Invoice.Status.PENDING:
            return Response(
                {
                    "payment_reference": invoice.payment_reference,
                    "status": invoice.status,
                    "amount": str(invoice.amount),
                    "currency": invoice.currency,
                    "seller_name": invoice.seller.get_full_name() or invoice.seller.username,
                    "message": "This payment request is no longer pending.",
                    "instructions": [],
                }
            )

        payload = build_personal_payment_instructions_for_invoice(invoice)
        payload["status"] = invoice.status
        return Response(payload)
