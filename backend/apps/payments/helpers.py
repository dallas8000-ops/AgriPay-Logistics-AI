from apps.logistics.models import Delivery
from apps.marketplace.models import Order

from .models import Invoice, Payment


def complete_invoice_payment(payment: Payment) -> None:
    """Mark invoice paid after Flutterwave or personal-transfer reconciliation."""
    if payment.status != Payment.Status.COMPLETED:
        payment.status = Payment.Status.COMPLETED
        payment.save(update_fields=["status"])

    invoice = payment.invoice
    if invoice and invoice.status != Invoice.Status.PAID:
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status", "updated_at"])

    from apps.notifications.models import Notification, send_notification

    if invoice:
        send_notification(
            invoice.seller,
            "Invoice paid",
            f"{invoice.payment_reference} — {invoice.customer_name} paid {invoice.amount} {invoice.currency}.",
            channel=Notification.Channel.IN_APP,
            metadata={"invoice_id": invoice.pk},
        )


def complete_payment(payment: Payment) -> Delivery | None:
    """Mark payment and order paid, create delivery if needed, notify parties."""
    if payment.invoice_id:
        complete_invoice_payment(payment)
        return None

    if payment.status != Payment.Status.COMPLETED:
        payment.status = Payment.Status.COMPLETED
        payment.save(update_fields=["status"])

    # Subscription payments activate the paying organization.
    if (payment.metadata or {}).get("kind") == "subscription":
        _activate_subscription(payment)
        return None

    from apps.notifications.services import notify_payment_completed

    if not payment.order_id:
        return None

    if payment.order.status == Order.Status.PENDING:
        payment.order.status = Order.Status.PAID
        payment.order.save(update_fields=["status"])

    delivery, _ = Delivery.objects.get_or_create(
        order=payment.order,
        defaults={
            "pickup_location": payment.order.listing.location,
            "dropoff_location": payment.order.delivery_address,
        },
    )
    notify_payment_completed(payment)
    return delivery


def _activate_subscription(payment: Payment) -> None:
    """Activate the organization billed by this subscription payment."""
    import datetime

    from apps.accounts.models import Organization

    org_id = (payment.metadata or {}).get("organization_id")
    if not org_id:
        return
    try:
        org = Organization.objects.get(pk=org_id)
    except Organization.DoesNotExist:
        return
    org.billing_status = Organization.BillingStatus.ACTIVE
    org.last_paid_at = payment.created_at
    org.paid_through = datetime.date.today() + datetime.timedelta(days=30)
    org.save(update_fields=["billing_status", "last_paid_at", "paid_through"])
