from django.contrib import admin

from .models import Invoice, Payment, PaymentLedgerEntry


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "invoice", "provider", "amount", "currency", "status", "created_at")
    list_filter = ("provider", "status")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("payment_reference", "seller", "customer_name", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency")


@admin.register(PaymentLedgerEntry)
class PaymentLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "amount", "currency", "status", "order", "invoice", "created_at")
    list_filter = ("status", "source")
