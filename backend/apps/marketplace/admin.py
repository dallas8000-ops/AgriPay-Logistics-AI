from django.contrib import admin

from .models import Order, ProduceListing


@admin.register(ProduceListing)
class ProduceListingAdmin(admin.ModelAdmin):
    list_display = ("crop", "seller", "quantity_kg", "unit_price", "country", "status")
    list_filter = ("status", "country", "crop", "season")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "buyer", "total_amount", "status", "created_at")
    list_filter = ("status",)
