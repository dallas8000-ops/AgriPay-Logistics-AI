import re
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.marketplace.models import Order

from .models import Invoice, Payment, PaymentLedgerEntry
from .sms_parser import ParsedSmsPayment, parse_mobile_money_sms


def seller_mobile_number(seller: User) -> tuple[str, str]:
    """Return (phone, provider) for a seller's personal collection number."""
    profile = None
    provider = ""
    if seller.role == User.Role.FARMER and hasattr(seller, "farmer_profile"):
        profile = seller.farmer_profile
        provider = profile.mobile_money_provider or "mtn"
    elif seller.role == User.Role.VENDOR and hasattr(seller, "vendor_profile"):
        profile = seller.vendor_profile
        provider = "mtn"
    if profile and profile.mobile_money_number:
        return profile.mobile_money_number, provider
    return seller.phone, provider


def order_payment_reference(order: Order) -> str:
    if order.payment_reference:
        return order.payment_reference
    return f"AGR-{order.pk}"


def build_personal_payment_instructions(order: Order) -> dict:
    seller = order.listing.seller
    phone, provider = seller_mobile_number(seller)
    reference = order_payment_reference(order)
    provider_labels = {
        "mtn": "MTN Mobile Money",
        "airtel": "Airtel Money",
        "mpesa": "M-Pesa",
    }
    return {
        "collection_mode": "personal_transfer",
        "requires_merchant_account": False,
        "seller_name": seller.get_full_name() or seller.username,
        "payee_phone": phone,
        "provider": provider,
        "provider_label": provider_labels.get(provider, "Mobile Money"),
        "amount": str(order.total_amount),
        "currency": order.currency,
        "payment_reference": reference,
        "instructions": [
            f"Open {provider_labels.get(provider, 'your mobile money app')} on your phone.",
            f"Send {order.currency} {order.total_amount} to {phone}.",
            f"Use reference / reason: {reference} (required for reconciliation).",
            "Paste the confirmation SMS on the Reconcile screen, or tap 'I have paid' so the seller can verify.",
        ],
    }


def _order_id_from_reference(reference: str) -> int | None:
    if not reference:
        return None
    match = re.search(r"(?:AGR|ORDER)[- ]?(\d+)", reference.upper())
    if match:
        return int(match.group(1))
    return None


def _invoice_id_from_reference(reference: str) -> int | None:
    if not reference:
        return None
    match = re.search(r"INV[- ]?(\d+)", reference.upper())
    if match:
        return int(match.group(1))
    return None


def invoice_payment_reference(invoice: Invoice) -> str:
    if invoice.payment_reference:
        return invoice.payment_reference
    return f"INV-{invoice.pk}"


def build_personal_payment_instructions_for_invoice(invoice: Invoice) -> dict:
    phone, provider = seller_mobile_number(invoice.seller)
    reference = invoice_payment_reference(invoice)
    provider_labels = {
        "mtn": "MTN Mobile Money",
        "airtel": "Airtel Money",
        "mpesa": "M-Pesa",
    }
    return {
        "collection_mode": "personal_transfer",
        "requires_merchant_account": False,
        "invoice_id": invoice.pk,
        "seller_name": invoice.seller.get_full_name() or invoice.seller.username,
        "payee_phone": phone,
        "provider": provider,
        "provider_label": provider_labels.get(provider, "Mobile Money"),
        "amount": str(invoice.amount),
        "currency": invoice.currency,
        "payment_reference": reference,
        "customer_name": invoice.customer_name,
        "description": invoice.description,
        "instructions": [
            f"Open {provider_labels.get(provider, 'your mobile money app')} on your phone.",
            f"Send {invoice.currency} {invoice.amount} to {phone}.",
            f"Use reference / reason: {reference} (required for reconciliation).",
            "Seller pastes the confirmation SMS on the Reconcile screen to mark this invoice paid.",
        ],
    }


def suggest_invoices_for_entry(
    owner: User, parsed: ParsedSmsPayment, amount: Decimal | None
) -> list[Invoice]:
    qs = Invoice.objects.filter(seller=owner, status=Invoice.Status.PENDING)
    if parsed.order_reference:
        invoice_id = _invoice_id_from_reference(parsed.order_reference)
        if invoice_id:
            qs = qs.filter(pk=invoice_id)
    if amount is not None:
        qs = qs.filter(amount=amount)
    return list(qs.order_by("-created_at")[:5])


def suggest_orders_for_entry(owner: User, parsed: ParsedSmsPayment, amount: Decimal | None) -> list[Order]:
    qs = Order.objects.filter(listing__seller=owner, status=Order.Status.PENDING)
    if parsed.order_reference:
        order_id = _order_id_from_reference(parsed.order_reference)
        if order_id:
            qs = qs.filter(pk=order_id)
    if amount is not None:
        qs = qs.filter(total_amount=amount)
    return list(qs.order_by("-created_at")[:5])


def create_ledger_entry(
    *,
    owner: User,
    recorded_by: User,
    source: str,
    raw_sms: str = "",
    parsed: ParsedSmsPayment | None = None,
    order: Order | None = None,
    invoice: Invoice | None = None,
    notes: str = "",
) -> PaymentLedgerEntry:
    if parsed is None and raw_sms:
        parsed = parse_mobile_money_sms(raw_sms)

    entry = PaymentLedgerEntry(
        owner=owner,
        recorded_by=recorded_by,
        order=order,
        invoice=invoice,
        source=source,
        raw_sms=raw_sms,
        amount=parsed.amount if parsed else None,
        currency=parsed.currency if parsed else "",
        provider=parsed.provider if parsed else "",
        txn_reference=parsed.txn_reference if parsed else "",
        payer_phone=parsed.payer_phone if parsed else "",
        parse_confidence=parsed.confidence if parsed else 0,
        parsed_fields=parsed.fields if parsed else {},
        notes=notes,
        status=PaymentLedgerEntry.Status.UNMATCHED,
    )

    if order:
        entry.order = order
        entry.status = PaymentLedgerEntry.Status.MATCHED
    elif invoice:
        entry.invoice = invoice
        entry.status = PaymentLedgerEntry.Status.MATCHED
    elif parsed:
        order_suggestions = suggest_orders_for_entry(owner, parsed, parsed.amount)
        invoice_suggestions = suggest_invoices_for_entry(owner, parsed, parsed.amount)
        if len(order_suggestions) == 1 and not invoice_suggestions:
            entry.order = order_suggestions[0]
            entry.status = PaymentLedgerEntry.Status.MATCHED
        elif len(invoice_suggestions) == 1 and not order_suggestions:
            entry.invoice = invoice_suggestions[0]
            entry.status = PaymentLedgerEntry.Status.MATCHED

    entry.save()
    return entry


def match_ledger_to_order(entry: PaymentLedgerEntry, order: Order, user: User) -> PaymentLedgerEntry:
    if entry.owner_id != order.listing.seller_id:
        raise ValueError("Order does not belong to this seller.")
    if user.id not in (entry.owner_id, entry.recorded_by_id) and user.role != User.Role.ADMIN:
        raise ValueError("Not allowed to match this entry.")

    entry.order = order
    entry.status = PaymentLedgerEntry.Status.MATCHED
    entry.save(update_fields=["order", "status", "updated_at"])
    return entry


def match_ledger_to_invoice(
    entry: PaymentLedgerEntry, invoice: Invoice, user: User
) -> PaymentLedgerEntry:
    if entry.owner_id != invoice.seller_id:
        raise ValueError("Invoice does not belong to this seller.")
    if user.id not in (entry.owner_id, entry.recorded_by_id) and user.role != User.Role.ADMIN:
        raise ValueError("Not allowed to match this entry.")

    entry.invoice = invoice
    entry.order = None
    entry.status = PaymentLedgerEntry.Status.MATCHED
    entry.save(update_fields=["invoice", "order", "status", "updated_at"])
    return entry


def reconcile_personal_payment(entry: PaymentLedgerEntry) -> Payment | None:
    """When a ledger entry is matched, mark order or invoice paid without merchant API."""
    if entry.status != PaymentLedgerEntry.Status.MATCHED:
        return None
    if entry.invoice:
        return _reconcile_invoice_from_ledger(entry)
    if entry.order:
        return _reconcile_order_from_ledger(entry)
    return None


def _reconcile_order_from_ledger(entry: PaymentLedgerEntry) -> Payment | None:
    order = entry.order
    if not order or order.status != Order.Status.PENDING:
        return None

    payment, _ = Payment.objects.get_or_create(
        order=order,
        payer=order.buyer,
        defaults={
            "amount": order.total_amount,
            "currency": order.currency,
            "provider": entry.provider or Payment.Provider.MTN_MOMO,
            "status": Payment.Status.COMPLETED,
            "phone_number": entry.payer_phone,
            "external_reference": entry.txn_reference or f"LEDGER-{entry.pk}",
            "metadata": {
                "collection_mode": "personal_transfer",
                "ledger_entry_id": str(entry.pk),
                "reconciled_at": timezone.now().isoformat(),
            },
        },
    )
    if payment.status != Payment.Status.COMPLETED:
        payment.status = Payment.Status.COMPLETED
        payment.metadata = {
            **(payment.metadata or {}),
            "collection_mode": "personal_transfer",
            "ledger_entry_id": str(entry.pk),
        }
        payment.save()

    from .helpers import complete_payment

    complete_payment(payment)
    return payment


def _reconcile_invoice_from_ledger(entry: PaymentLedgerEntry) -> Payment | None:
    invoice = entry.invoice
    if not invoice or invoice.status != Invoice.Status.PENDING:
        return None

    payment, _ = Payment.objects.get_or_create(
        invoice=invoice,
        defaults={
            "amount": invoice.amount,
            "currency": invoice.currency,
            "provider": entry.provider or Payment.Provider.MTN_MOMO,
            "status": Payment.Status.COMPLETED,
            "phone_number": entry.payer_phone,
            "external_reference": entry.txn_reference or f"LEDGER-{entry.pk}",
            "metadata": {
                "collection_mode": "personal_transfer",
                "ledger_entry_id": str(entry.pk),
                "reconciled_at": timezone.now().isoformat(),
            },
        },
    )
    if payment.status != Payment.Status.COMPLETED:
        payment.status = Payment.Status.COMPLETED
        payment.save()

    from .helpers import complete_invoice_payment

    complete_invoice_payment(payment)
    return payment


def reconciliation_summary(user: User) -> dict:
    """Notebook replacement: expected vs recorded collections."""
    pending_orders = Order.objects.filter(
        listing__seller=user,
        status=Order.Status.PENDING,
    )
    pending_invoices = Invoice.objects.filter(seller=user, status=Invoice.Status.PENDING)
    expected_orders = pending_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    expected_invoices = pending_invoices.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    expected_total = expected_orders + expected_invoices

    entries = PaymentLedgerEntry.objects.filter(owner=user)
    unmatched = entries.filter(status=PaymentLedgerEntry.Status.UNMATCHED)
    matched = entries.filter(status=PaymentLedgerEntry.Status.MATCHED)
    recorded_total = matched.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return {
        "pending_orders_count": pending_orders.count(),
        "pending_invoices_count": pending_invoices.count(),
        "expected_collections": str(expected_total),
        "recorded_collections": str(recorded_total),
        "unmatched_entries_count": unmatched.count(),
        "matched_entries_count": matched.count(),
        "collection_mode": "personal_transfer",
        "message": (
            "Track payments sent to your personal mobile money number — "
            "no merchant account required. Paste SMS confirmations to match orders and invoices."
        ),
    }
