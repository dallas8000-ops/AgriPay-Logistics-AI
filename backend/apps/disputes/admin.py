from django.contrib import admin

from .models import Dispute, DisputeMessage


class MessageInline(admin.TabularInline):
    model = DisputeMessage
    extra = 0


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "category", "status", "raised_by", "created_at")
    list_filter = ("status", "category")
    inlines = [MessageInline]
