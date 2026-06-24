from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        FARMER = "farmer", "Farmer"
        VENDOR = "vendor", "Market Vendor"
        BUYER = "buyer", "Produce Buyer"
        DRIVER = "driver", "Truck Driver"
        ADMIN = "admin", "Platform Admin"

    class Country(models.TextChoices):
        UGANDA = "UG", "Uganda"
        KENYA = "KE", "Kenya"
        TANZANIA = "TZ", "Tanzania"
        RWANDA = "RW", "Rwanda"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FARMER)
    country = models.CharField(max_length=2, choices=Country.choices, default=Country.KENYA)
    phone = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=10, default="en")
    is_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def currency(self):
        from django.conf import settings

        return settings.SUPPORTED_COUNTRIES.get(self.country, {}).get("currency", "KES")


class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="farmer_profile")
    farm_name = models.CharField(max_length=200)
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    farm_size_acres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    primary_crops = models.JSONField(default=list)
    mobile_money_number = models.CharField(max_length=20, blank=True)
    mobile_money_provider = models.CharField(
        max_length=20,
        choices=[("mtn", "MTN"), ("airtel", "Airtel"), ("mpesa", "M-Pesa")],
        blank=True,
    )
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.farm_name


class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vendor_profile")
    stall_name = models.CharField(max_length=200)
    market_location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    mobile_money_number = models.CharField(max_length=20, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.stall_name


class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="buyer_profile")
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255)
    reliability_score = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
    total_orders = models.PositiveIntegerField(default=0)
    mobile_money_number = models.CharField(max_length=20, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name


class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver_profile")
    license_number = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=50)
    vehicle_plate = models.CharField(max_length=20)
    capacity_kg = models.PositiveIntegerField(default=1000)
    is_available = models.BooleanField(default=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    mobile_money_number = models.CharField(max_length=20, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.vehicle_plate}"
