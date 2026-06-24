from django.db import models

from apps.accounts.models import User
from apps.marketplace.models import Order


class Delivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending Assignment"
        ASSIGNED = "assigned", "Driver Assigned"
        PICKED_UP = "picked_up", "Picked Up"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="delivery")
    driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
        limit_choices_to={"role": User.Role.DRIVER},
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    pickup_location = models.CharField(max_length=500)
    dropoff_location = models.CharField(max_length=500)
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    route_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "deliveries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Delivery for Order #{self.order_id}"


class DeliveryTrackingEvent(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="tracking_events")
    status = models.CharField(max_length=50)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]


class ProofOfDelivery(models.Model):
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE, related_name="proof")
    photo = models.ImageField(upload_to="pod/", blank=True, null=True)
    recipient_name = models.CharField(max_length=200)
    recipient_phone = models.CharField(max_length=20, blank=True)
    signature_data = models.TextField(blank=True)
    otp_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "proofs of delivery"

    def __str__(self):
        return f"POD for Delivery #{self.delivery_id}"
