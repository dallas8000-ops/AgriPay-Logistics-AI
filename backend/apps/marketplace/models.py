from django.conf import settings
from django.db import models

from apps.accounts.models import User


class ProduceListing(models.Model):
    class Season(models.TextChoices):
        LONG_RAINS = "long_rains", "Long Rains"
        SHORT_RAINS = "short_rains", "Short Rains"
        DRY = "dry", "Dry Season"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"
        EXPIRED = "expired", "Expired"

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    crop = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="KES")
    location = models.CharField(max_length=255)
    country = models.CharField(max_length=2, choices=User.Country.choices)
    season = models.CharField(max_length=20, choices=Season.choices, default=Season.LONG_RAINS)
    harvest_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="produce/", blank=True, null=True)
    ai_suggested_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.crop} - {self.quantity_kg}kg @ {self.unit_price} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.currency and self.seller:
            self.currency = self.seller.currency
        super().save(*args, **kwargs)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        PAID = "paid", "Paid"
        ASSIGNED = "assigned", "Driver Assigned"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        DISPUTED = "disputed", "Disputed"

    listing = models.ForeignKey(ProduceListing, on_delete=models.PROTECT, related_name="orders")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchases")
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="KES")
    delivery_address = models.CharField(max_length=500)
    payment_reference = models.CharField(max_length=32, blank=True)
    collection_method = models.CharField(
        max_length=30,
        choices=[
            ("personal_transfer", "Personal mobile money"),
            ("integrated", "Merchant API"),
            ("stripe", "Stripe"),
        ],
        default="personal_transfer",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.payment_reference:
            self.payment_reference = f"AGR-{self.pk}"
            super().save(update_fields=["payment_reference"])

    def __str__(self):
        return f"Order #{self.pk} - {self.listing.crop}"
