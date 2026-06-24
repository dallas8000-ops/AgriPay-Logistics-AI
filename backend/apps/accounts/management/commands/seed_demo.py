from django.core.management.base import BaseCommand

from apps.accounts.models import BuyerProfile, DriverProfile, FarmerProfile, User, VendorProfile
from apps.marketplace.models import ProduceListing


class Command(BaseCommand):
    help = "Seed demo data for AgriPay Logistics AI"

    def handle(self, *args, **options):
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
            country="KE",
            phone="+254712345678",
            first_name="James",
            last_name="Kariuki",
        )
        FarmerProfile.objects.create(
            user=farmer,
            farm_name="Kariuki Family Farm",
            location="Nakuru, Kenya",
            primary_crops=["maize", "beans"],
            mobile_money_number="+254712345678",
            mobile_money_provider="mpesa",
            onboarding_complete=True,
        )
        buyer = User.objects.create_user(
            "mary_buyer",
            "mary@agripay.africa",
            "demo12345",
            role=User.Role.BUYER,
            country="UG",
            phone="+256700123456",
            first_name="Mary",
            last_name="Nabukeera",
        )
        BuyerProfile.objects.create(
            user=buyer,
            business_name="Kampala Fresh Markets Ltd",
            business_type="Wholesale",
            location="Kampala, Uganda",
            mobile_money_number="+256700123456",
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
            ("maize", 500, 45, "KE", "Nakuru"),
            ("coffee", 200, 850, "UG", "Mbale"),
            ("tomatoes", 150, 120, "TZ", "Arusha"),
            ("bananas", 300, 35, "RW", "Musanze"),
            ("beans", 400, 180, "KE", "Eldoret"),
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
