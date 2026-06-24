from django.core.management.base import BaseCommand

from apps.accounts.models import BuyerProfile, DriverProfile, FarmerProfile, User, VendorProfile
from apps.marketplace.models import ProduceListing


class Command(BaseCommand):
    help = "Seed demo data for AgriPay Logistics AI"

    def _align_demo_personas(self) -> None:
        """Keep primary demo accounts Uganda/UGX for portfolio consistency."""
        try:
            james = User.objects.get(username="james_farmer")
            james.country = "UG"
            james.phone = "+256772123456"
            james.first_name = "James"
            james.last_name = "Okello"
            james.save(update_fields=["country", "phone", "first_name", "last_name"])
            farmer = getattr(james, "farmer_profile", None)
            if farmer:
                farmer.farm_name = "Okello Family Farm"
                farmer.location = "Mbale, Uganda"
                farmer.mobile_money_number = "+256772123456"
                farmer.mobile_money_provider = "mtn"
                farmer.save(
                    update_fields=[
                        "farm_name",
                        "location",
                        "mobile_money_number",
                        "mobile_money_provider",
                    ]
                )
        except User.DoesNotExist:
            pass
        try:
            mary = User.objects.get(username="mary_buyer")
            mary.country = "UG"
            mary.phone = "+256701234567"
            mary.first_name = "Mary"
            mary.last_name = "Nambi"
            mary.save(update_fields=["country", "phone", "first_name", "last_name"])
            profile = getattr(mary, "buyer_profile", None)
            if profile:
                profile.business_name = "Kampala Fresh Markets Ltd"
                profile.location = "Kampala, Uganda"
                profile.mobile_money_number = "+256701234567"
                profile.save(update_fields=["business_name", "location", "mobile_money_number"])
        except User.DoesNotExist:
            pass

    def handle(self, *args, **options):
        self._align_demo_personas()

        if User.objects.filter(username="admin").exists():
            self.stdout.write("Seed data already exists, skipping.")
            return

        admin = User.objects.create_superuser(
            "admin", "admin@agripay.africa", "admin12345", role=User.Role.ADMIN, country="KE"
        )
        farmer = User.objects.create_user(
            "james_farmer",
            "james@agripay.africa",
            "demo12345",
            role=User.Role.FARMER,
            country="UG",
            phone="+256772123456",
            first_name="James",
            last_name="Okello",
        )
        FarmerProfile.objects.create(
            user=farmer,
            farm_name="Okello Family Farm",
            location="Mbale, Uganda",
            primary_crops=["maize", "beans"],
            mobile_money_number="+256772123456",
            mobile_money_provider="mtn",
            onboarding_complete=True,
        )
        buyer = User.objects.create_user(
            "mary_buyer",
            "mary@agripay.africa",
            "demo12345",
            role=User.Role.BUYER,
            country="UG",
            phone="+256701234567",
            first_name="Mary",
            last_name="Nambi",
        )
        BuyerProfile.objects.create(
            user=buyer,
            business_name="Kampala Fresh Markets Ltd",
            business_type="Wholesale",
            location="Kampala, Uganda",
            mobile_money_number="+256701234567",
            onboarding_complete=True,
        )
        driver = User.objects.create_user(
            "peter_driver",
            "peter@agripay.africa",
            "demo12345",
            role=User.Role.DRIVER,
            country="TZ",
            phone="+255754321098",
            first_name="Peter",
            last_name="Mwangi",
        )
        DriverProfile.objects.create(
            user=driver,
            license_number="TZ-DL-998877",
            vehicle_type="Isuzu Truck",
            vehicle_plate="T 123 ABC",
            capacity_kg=5000,
            mobile_money_number="+255754321098",
            onboarding_complete=True,
        )
        vendor = User.objects.create_user(
            "grace_vendor",
            "grace@agripay.africa",
            "demo12345",
            role=User.Role.VENDOR,
            country="RW",
            phone="+250788123456",
            first_name="Grace",
            last_name="Uwimana",
        )
        VendorProfile.objects.create(
            user=vendor,
            stall_name="Grace's Produce Corner",
            market_location="Kigali City Market",
            mobile_money_number="+250788123456",
            onboarding_complete=True,
        )

        crops = [
            ("maize", 500, 1800, "UG", "Mbale"),
            ("coffee", 200, 8500, "UG", "Kapchorwa"),
            ("tomatoes", 150, 120, "TZ", "Arusha"),
            ("bananas", 300, 35, "RW", "Musanze"),
            ("beans", 400, 6500, "UG", "Masaka"),
        ]
        sellers = [farmer, vendor]
        for i, (crop, qty, price, country, loc) in enumerate(crops):
            ProduceListing.objects.create(
                seller=sellers[i % 2],
                crop=crop,
                quantity_kg=qty,
                unit_price=price,
                currency={"KE": "KES", "UG": "UGX", "TZ": "TZS", "RW": "RWF"}[country],
                location=loc,
                country=country,
                description=f"Fresh {crop} from East Africa farms.",
            )

        from apps.notifications.models import Notification, send_notification

        send_notification(
            buyer,
            "Welcome to AgriPay",
            "Browse fresh produce from farmers across East Africa.",
        )
        send_notification(
            farmer,
            "Welcome to AgriPay",
            "List your harvest and connect with buyers instantly.",
            channel=Notification.Channel.WHATSAPP,
        )
        send_notification(
            driver,
            "Driver Account Ready",
            "You'll receive SMS alerts when new delivery jobs are assigned.",
            channel=Notification.Channel.SMS,
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Admin: admin / admin12345")
        self.stdout.write("Demo users: james_farmer, mary_buyer, peter_driver, grace_vendor / demo12345")
