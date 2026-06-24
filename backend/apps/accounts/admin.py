from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import BuyerProfile, DriverProfile, FarmerProfile, User, VendorProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "country", "is_verified", "is_staff")
    list_filter = ("role", "country", "is_verified")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("AgriPay", {"fields": ("role", "country", "phone", "preferred_language", "is_verified")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("AgriPay", {"fields": ("role", "country", "phone")}),
    )


admin.site.register(FarmerProfile)
admin.site.register(VendorProfile)
admin.site.register(BuyerProfile)
admin.site.register(DriverProfile)
