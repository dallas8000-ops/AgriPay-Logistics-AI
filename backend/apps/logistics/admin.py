from django.contrib import admin

from .models import Delivery, DeliveryTrackingEvent, ProofOfDelivery


class TrackingInline(admin.TabularInline):
    model = DeliveryTrackingEvent
    extra = 0


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "driver", "status", "created_at")
    list_filter = ("status",)
    inlines = [TrackingInline]


admin.site.register(ProofOfDelivery)
