import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import BuyerProfile, DriverProfile, FarmerProfile, User, VendorProfile
from apps.marketplace.models import ProduceListing


# Local-development defaults only. They are never used when DEBUG is False.
_DEV_ADMIN_PASSWORD = "admin12345"
_DEV_USER_PASSWORD = "demo12345"


class Command(BaseCommand):
    help = "Seed demo data for AgriPay Logistics AI"

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-production",
            action="store_true",
            help=(
                "Permit seeding when DEBUG is False. Requires DEMO_ADMIN_PASSWORD "
                "and DEMO_USER_PASSWORD to be set; hardcoded defaults are refused."
            ),
        )

    def _resolve_passwords(self, allow_production: bool) -> tuple[str, str]:
        admin_pw = os.environ.get("DEMO_ADMIN_PASSWORD", "").strip()
        user_pw = os.environ.get("DEMO_USER_PASSWORD", "").strip()
        if settings.DEBUG:
            return admin_pw or _DEV_ADMIN_PASSWORD, user_pw or _DEV_USER_PASSWORD
        if not allow_production:
            raise CommandError(
                "seed_demo refuses to run with DEBUG=False. It creates a superuser and "
                "demo accounts. Re-run with --allow-production and set "
                "DEMO_ADMIN_PASSWORD / DEMO_USER_PASSWORD if this is intentional."
            )
        weak = {"", _DEV_ADMIN_PASSWORD, _DEV_USER_PASSWORD}
        if admin_pw in weak or user_pw in weak or min(len(admin_pw), len(user_pw)) < 12:
            raise CommandError(
                "DEMO_ADMIN_PASSWORD and DEMO_USER_PASSWORD must be set to unique values "
                "of at least 12 characters when seeding with DEBUG=False."
            )
        return admin_pw, user_pw

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
        admin_pw, user_pw = self._resolve_passwords(options["allow_production"])
        self._align_demo_personas()

        if User.objects.filter(username="admin").exists():
            self.stdout.write("Seed data already exists, skipping.")
            return

        admin = User.objects.create_superuser(
            "admin", "admin@agripay.africa", admin_pw, role=User.Role.ADMIN, country="KE"
        )
        farmer = User.objects.create_user(
            "james_farmer",
            "james@agripay.africa",
            user_pw,
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
            user_pw,
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
            user_pw,
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
            user_pw,
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
        if settings.DEBUG:
            self.stdout.write(f"Admin: admin / {admin_pw}")
            self.stdout.write(
                f"Demo users: james_farmer, mary_buyer, peter_driver, grace_vendor / {user_pw}"
            )
        else:
            self.stdout.write("Credentials taken from DEMO_ADMIN_PASSWORD / DEMO_USER_PASSWORD.")
