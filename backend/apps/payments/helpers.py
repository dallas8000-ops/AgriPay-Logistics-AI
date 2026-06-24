from apps.logistics.models import Delivery
from apps.marketplace.models import Order

from .models import Payment
from .services import MobileMoneyService


def complete_payment(payment: Payment) -> Delivery:
    """Mark payment and order paid, create delivery if needed, notify parties."""
    from apps.notifications.services import notify_payment_completed

    if payment.status != Payment.Status.COMPLETED:
        payment.status = Payment.Status.COMPLETED
        payment.save(update_fields=["status"])

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
