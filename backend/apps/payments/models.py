import uuid

from django.db import models

from apps.accounts.models import User
from apps.marketplace.models import Order


class Payment(models.Model):
    class Provider(models.TextChoices):
        MTN_MOMO = "mtn_momo", "MTN Mobile Money"
        AIRTEL_MONEY = "airtel_money", "Airtel Money"
        MPESA = "mpesa", "M-Pesa"
        STRIPE = "stripe", "Stripe"
        FLUTTERWAVE = "flutterwave", "Flutterwave"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payments", null=True, blank=True
    )
    invoice = models.ForeignKey(
        "Invoice", on_delete=models.CASCADE, related_name="payments", null=True, blank=True
    )
    payer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payments", null=True, blank=True
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="KES")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    phone_number = models.CharField(max_length=20, blank=True)
    external_reference = models.CharField(max_length=200, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} - {self.amount} {self.currency} ({self.status})"


class PaymentLedgerEntry(models.Model):
    """Tracks real-world mobile money received on a personal number (SMS / notebook replacement)."""

    class Source(models.TextChoices):
        SMS_PASTE = "sms_paste", "SMS pasted"
        MANUAL = "manual", "Manual entry"
        BUYER_CLAIM = "buyer_claim", "Buyer reported payment"
        API = "api", "Provider API"

    class Status(models.TextChoices):
        UNMATCHED = "unmatched", "Unmatched"
        MATCHED = "matched", "Matched to order"
        DISPUTED = "disputed", "Disputed"

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_ledger_entries"
    )
    recorded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recorded_ledger_entries"
    )
    order = models.ForeignKey(
        "marketplace.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    source = models.CharField(max_length=20, choices=Source.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNMATCHED)
    raw_sms = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    provider = models.CharField(max_length=20, blank=True)
    txn_reference = models.CharField(max_length=64, blank=True)
    payer_phone = models.CharField(max_length=20, blank=True)
    parse_confidence = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    parsed_fields = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ledger {self.pk} - {self.amount} {self.currency} ({self.status})"


class Invoice(models.Model):
    """Generic payment request — works for any SME or agri sale without a marketplace listing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    class CollectionMethod(models.TextChoices):
        PERSONAL_TRANSFER = "personal_transfer", "Personal mobile money"
        FLUTTERWAVE = "flutterwave", "Flutterwave checkout"
        STRIPE = "stripe", "Stripe"

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="KES")
    payment_reference = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    collection_method = models.CharField(
        max_length=30,
        choices=CollectionMethod.choices,
        default=CollectionMethod.PERSONAL_TRANSFER,
    )
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.payment_reference:
            self.payment_reference = f"INV-{self.pk}"
            super().save(update_fields=["payment_reference"])

    def __str__(self):
        return f"Invoice {self.payment_reference} - {self.amount} {self.currency}"
