from apps.notifications.models import Notification, send_notification


def notify_user(user, title, body, *, sms=False, whatsapp=False, metadata=None):
    """Send in-app notification plus optional SMS/WhatsApp sandbox mirrors."""
    meta = metadata or {}
    send_notification(user, title, body, channel=Notification.Channel.IN_APP, metadata=meta)
    if sms and user.phone:
        send_notification(
            user,
            title,
            body[:160],
            channel=Notification.Channel.SMS,
            metadata={**meta, "phone": user.phone},
        )
    if whatsapp and user.phone:
        send_notification(
            user,
            title,
            body,
            channel=Notification.Channel.WHATSAPP,
            metadata={**meta, "phone": user.phone},
        )


def notify_order_placed(order):
    seller = order.listing.seller
    crop = order.listing.crop
    msg = f"New order for {order.quantity_kg}kg {crop}. Total: {order.total_amount} {order.currency}."
    notify_user(
        seller,
        "New Order Received",
        msg,
        sms=True,
        whatsapp=True,
        metadata={"order_id": order.id, "type": "order_placed"},
    )
    notify_user(
        order.buyer,
        "Order Confirmed",
        f"Your order for {crop} is pending payment.",
        metadata={"order_id": order.id, "type": "order_pending"},
    )


def notify_payment_completed(payment):
    order = payment.order
    notify_user(
        order.buyer,
        "Payment Successful",
        f"Payment of {payment.amount} {payment.currency} confirmed via {payment.get_provider_display()}.",
        sms=True,
        metadata={"order_id": order.id, "payment_id": str(payment.id), "type": "payment_completed"},
    )
    notify_user(
        order.listing.seller,
        "Payment Received",
        f"Buyer paid for {order.listing.crop}. Assign a driver for delivery.",
        sms=True,
        whatsapp=True,
        metadata={"order_id": order.id, "type": "payment_received"},
    )


def notify_driver_assigned(delivery, driver):
    order = delivery.order
    notify_user(
        driver,
        "New Delivery Job",
        f"Pickup: {delivery.pickup_location} → {delivery.dropoff_location}",
        sms=True,
        whatsapp=True,
        metadata={"delivery_id": delivery.id, "type": "driver_assigned"},
    )
    notify_user(
        order.buyer,
        "Driver Assigned",
        f"{driver.username} is assigned to deliver your {order.listing.crop}.",
        metadata={"delivery_id": delivery.id, "type": "driver_assigned"},
    )


def notify_delivery_status(delivery, status_label):
    order = delivery.order
    notify_user(
        order.buyer,
        f"Delivery Update: {status_label}",
        f"Your {order.listing.crop} order is now {status_label.replace('_', ' ')}.",
        sms=True,
        metadata={"delivery_id": delivery.id, "status": status_label},
    )


def notify_delivery_completed(delivery):
    order = delivery.order
    notify_user(
        order.buyer,
        "Delivered!",
        f"Your {order.listing.crop} order has been delivered with proof-of-delivery.",
        sms=True,
        whatsapp=True,
        metadata={"delivery_id": delivery.id, "type": "delivered"},
    )
    notify_user(
        order.listing.seller,
        "Delivery Complete",
        f"Order #{order.id} delivered successfully.",
        metadata={"order_id": order.id, "type": "delivered"},
    )
    if hasattr(order.buyer, "buyer_profile"):
        profile = order.buyer.buyer_profile
        profile.total_orders += 1
        profile.save(update_fields=["total_orders"])


def notify_dispute_raised(dispute):
    from apps.accounts.models import User

    msg = f"Dispute #{dispute.id} ({dispute.category}) on order #{dispute.order_id}."
    notify_user(
        dispute.raised_by,
        "Dispute Submitted",
        "We received your dispute and will review it shortly.",
        metadata={"dispute_id": dispute.id},
    )
    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        notify_user(admin, "New Dispute", msg, metadata={"dispute_id": dispute.id})
