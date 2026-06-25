from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    """A paying client. Billing is PER USER: the org owner is charged
    (active member count x per-user fee) each month. More users means a larger
    bill, not a blocked invite -- revenue scales with usage.

    Local owners pay via Flutterwave (mobile money + card); international owners
    pay via Stripe. The Organization is the billing subject; the owner settles
    one combined bill for everyone in the org.
    """

    class BillingStatus(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"

    name = models.CharField(max_length=200)
    billing_status = models.CharField(
        max_length=20, choices=BillingStatus.choices, default=BillingStatus.TRIALING
    )
    is_active = models.BooleanField(default=True)
    billing_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text="External subscription/customer id (Flutterwave/Stripe).",
    )
    last_paid_at = models.DateTimeField(null=True, blank=True)
    paid_through = models.DateField(
        null=True, blank=True, help_text="Service is paid up to this date."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def billable_users(self) -> int:
        """Active member count -- the multiplier for the monthly bill."""
        return self.memberships.filter(is_active=True).count()

    def monthly_bill(self):
        """(active users x per-user fee) in BILLING_CURRENCY."""
        from decimal import Decimal

        from django.conf import settings

        fee = Decimal(str(settings.SUBSCRIPTION_FEE_PER_USER))
        return (fee * self.billable_users).quantize(Decimal("0.01"))


class OrganizationMembership(models.Model):
    """Links a user to the organization whose fee covers them."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="membership"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.get_role_display()})"


class SeatLimitExceeded(Exception):
    """Retained for backward compatibility. Per-user billing does not block
    new members, so this is no longer raised by add_member_to_organization."""


def add_member_to_organization(organization, user, role=OrganizationMembership.Role.MEMBER):
    """Attach a user to an organization.

    Under per-user billing there is no seat cap -- every active member simply
    increases the org's monthly bill. We still dedupe so a user is not added twice.
    """
    existing = OrganizationMembership.objects.filter(user=user).first()
    if existing:
        return existing
    return OrganizationMembership.objects.create(
        organization=organization, user=user, role=role
    )


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
    collection_tier = models.CharField(
        max_length=20,
        choices=[
            ("personal", "Personal number only (no merchant account)"),
            ("merchant", "Registered business / merchant account"),
        ],
        default="personal",
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
    collection_tier = models.CharField(
        max_length=20,
        choices=[
            ("personal", "Personal number only (no merchant account)"),
            ("merchant", "Registered business / merchant account"),
        ],
        default="personal",
    )
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
