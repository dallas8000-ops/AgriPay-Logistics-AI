import csv
from decimal import Decimal

from django.http import HttpResponse

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.marketplace.models import Order

from .ledger_serializers import (
    MatchLedgerSerializer,
    ParseSmsSerializer,
    PaymentLedgerEntrySerializer,
)
from .models import Invoice, PaymentLedgerEntry
from .reconciliation import (
    build_personal_payment_instructions,
    build_personal_payment_instructions_for_invoice,
    create_ledger_entry,
    match_ledger_to_invoice,
    match_ledger_to_order,
    reconcile_personal_payment,
    reconciliation_summary,
    suggest_invoices_for_entry,
    suggest_orders_for_entry,
)
from .sms_parser import parse_mobile_money_sms


class PaymentLedgerViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentLedgerEntrySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.role in (User.Role.FARMER, User.Role.VENDOR):
            return PaymentLedgerEntry.objects.filter(owner=user)
        if user.role == User.Role.BUYER:
            return PaymentLedgerEntry.objects.filter(recorded_by=user)
        if user.role == User.Role.ADMIN:
            return PaymentLedgerEntry.objects.all()
        return PaymentLedgerEntry.objects.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        suggestions = {}
        invoice_suggestions = {}
        for entry in self.get_queryset()[:50]:
            if entry.status == PaymentLedgerEntry.Status.UNMATCHED and entry.amount:
                parsed = parse_mobile_money_sms(entry.raw_sms) if entry.raw_sms else None
                if parsed:
                    orders = suggest_orders_for_entry(entry.owner, parsed, entry.amount)
                    suggestions[str(entry.id)] = [o.id for o in orders]
                    invoices = suggest_invoices_for_entry(entry.owner, parsed, entry.amount)
                    invoice_suggestions[str(entry.id)] = [i.id for i in invoices]
        ctx["suggestions"] = suggestions
        ctx["invoice_suggestions"] = invoice_suggestions
        return ctx

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.role in (User.Role.FARMER, User.Role.VENDOR):
            owner = user
        else:
            return Response(
                {"detail": "Sellers record incoming payments. Buyers use buyer-claim."},
                status=403,
            )

        raw_sms = request.data.get("raw_sms", "")
        if not raw_sms and not request.data.get("amount"):
            return Response({"detail": "Paste an SMS or provide amount manually."}, status=400)

        entry = create_ledger_entry(
            owner=owner,
            recorded_by=user,
            source=request.data.get("source", PaymentLedgerEntry.Source.SMS_PASTE),
            raw_sms=raw_sms,
            notes=request.data.get("notes", ""),
        )
        if entry.status == PaymentLedgerEntry.Status.MATCHED:
            reconcile_personal_payment(entry)
        return Response(
            PaymentLedgerEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def parse_sms(self, request):
        ser = ParseSmsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        parsed = parse_mobile_money_sms(ser.validated_data["text"])
        suggestions = []
        if request.user.role in (User.Role.FARMER, User.Role.VENDOR):
            suggestions = [
                {"id": o.id, "reference": o.payment_reference, "amount": str(o.total_amount), "type": "order"}
                for o in suggest_orders_for_entry(request.user, parsed, parsed.amount)
            ]
            suggestions += [
                {"id": i.id, "reference": i.payment_reference, "amount": str(i.amount), "type": "invoice"}
                for i in suggest_invoices_for_entry(request.user, parsed, parsed.amount)
            ]
        return Response(
            {
                "amount": str(parsed.amount) if parsed.amount is not None else None,
                "currency": parsed.currency,
                "provider": parsed.provider,
                "txn_reference": parsed.txn_reference,
                "payer_phone": parsed.payer_phone,
                "order_reference": parsed.order_reference,
                "confidence": parsed.confidence,
                "fields": parsed.fields,
                "suggested_orders": suggestions,
            }
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        if request.user.role not in (User.Role.FARMER, User.Role.VENDOR, User.Role.ADMIN):
            return Response({"detail": "Seller account required."}, status=403)
        user = request.user
        if user.role == User.Role.ADMIN and request.query_params.get("user_id"):
            user = User.objects.get(pk=request.query_params["user_id"])
        return Response(reconciliation_summary(user))

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        if request.user.role not in (User.Role.FARMER, User.Role.VENDOR, User.Role.ADMIN):
            return Response({"detail": "Seller account required."}, status=403)
        qs = self.get_queryset().select_related("invoice", "order").order_by("-created_at")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="agripay-ledger.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "created_at",
                "amount",
                "currency",
                "provider",
                "status",
                "source",
                "order_reference",
                "invoice_reference",
                "payer_phone",
                "txn_reference",
                "raw_sms",
            ]
        )
        for entry in qs:
            order_ref = f"AGR-{entry.order_id}" if entry.order_id else ""
            inv_ref = entry.invoice.payment_reference if entry.invoice_id else ""
            writer.writerow(
                [
                    entry.created_at.isoformat(),
                    entry.amount or "",
                    entry.currency,
                    entry.provider,
                    entry.status,
                    entry.source,
                    order_ref,
                    inv_ref,
                    entry.payer_phone,
                    entry.txn_reference,
                    entry.raw_sms.replace("\n", " ").strip(),
                ]
            )
        return response

    @action(detail=True, methods=["post"])
    def match(self, request, pk=None):
        entry = self.get_object()
        ser = MatchLedgerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = Order.objects.get(pk=ser.validated_data["order_id"])
        try:
            match_ledger_to_order(entry, order, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        payment = reconcile_personal_payment(entry)
        return Response(
            {
                "entry": PaymentLedgerEntrySerializer(entry, context=self.get_serializer_context()).data,
                "payment_id": str(payment.id) if payment else None,
                "order_status": order.status,
            }
        )

    @action(detail=True, methods=["post"], url_path="match-invoice")
    def match_invoice(self, request, pk=None):
        entry = self.get_object()
        invoice_id = request.data.get("invoice_id")
        if not invoice_id:
            return Response({"detail": "invoice_id required"}, status=400)
        invoice = Invoice.objects.get(pk=invoice_id)
        try:
            match_ledger_to_invoice(entry, invoice, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        payment = reconcile_personal_payment(entry)
        return Response(
            {
                "entry": PaymentLedgerEntrySerializer(entry, context=self.get_serializer_context()).data,
                "payment_id": str(payment.id) if payment else None,
                "invoice_status": invoice.status,
            }
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        entry = self.get_object()
        if entry.owner_id != request.user.id:
            return Response({"detail": "Only the seller can confirm receipt."}, status=403)
        if not entry.order and not entry.invoice:
            return Response({"detail": "Match an order or invoice before confirming."}, status=400)
        payment = reconcile_personal_payment(entry)
        if not payment:
            return Response({"detail": "Could not reconcile payment."}, status=400)
        return Response({"status": "completed", "payment_id": str(payment.id)})


class PersonalCollectionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="instructions")
    def instructions(self, request):
        order_id = request.query_params.get("order_id")
        if not order_id:
            return Response({"detail": "order_id required"}, status=400)
        try:
            order = Order.objects.select_related("listing__seller").get(pk=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        if request.user != order.buyer and request.user.role != User.Role.ADMIN:
            return Response({"detail": "Not your order"}, status=403)
        order.collection_method = "personal_transfer"
        order.save(update_fields=["collection_method"])
        return Response(build_personal_payment_instructions(order))

    @action(detail=False, methods=["post"], url_path="buyer-claim")
    def buyer_claim(self, request):
        order_id = request.data.get("order_id")
        raw_sms = request.data.get("raw_sms", "")
        notes = request.data.get("notes", "Buyer reported payment sent")
        try:
            order = Order.objects.select_related("listing__seller").get(pk=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        if request.user != order.buyer:
            return Response({"detail": "Only the buyer can report payment"}, status=403)

        seller = order.listing.seller
        entry = create_ledger_entry(
            owner=seller,
            recorded_by=request.user,
            source=PaymentLedgerEntry.Source.BUYER_CLAIM,
            raw_sms=raw_sms,
            order=None,
            notes=notes,
        )
        parsed = parse_mobile_money_sms(raw_sms) if raw_sms else None
        if parsed and parsed.order_reference:
            from .reconciliation import _order_id_from_reference

            oid = _order_id_from_reference(parsed.order_reference)
            if oid == order.id:
                match_ledger_to_order(entry, order, request.user)

        return Response(
            {
                "entry": PaymentLedgerEntrySerializer(entry).data,
                "message": (
                    "Payment reported. The seller will verify against their SMS and confirm receipt."
                ),
            },
            status=status.HTTP_201_CREATED,
        )
