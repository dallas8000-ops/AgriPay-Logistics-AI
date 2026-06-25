from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_vendor_collection_tier"),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("billing_status", models.CharField(
                    choices=[
                        ("trialing", "Trialing"),
                        ("active", "Active"),
                        ("past_due", "Past due"),
                        ("canceled", "Canceled"),
                    ],
                    default="trialing",
                    max_length=20,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("billing_reference", models.CharField(
                    blank=True,
                    help_text="External subscription/customer id (Flutterwave/Stripe).",
                    max_length=120,
                )),
                ("last_paid_at", models.DateTimeField(blank=True, null=True)),
                ("paid_through", models.DateField(
                    blank=True,
                    help_text="Service is paid up to this date.",
                    null=True,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="memberships",
                    to="accounts.organization",
                )),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="membership",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("role", models.CharField(
                    choices=[
                        ("owner", "Owner"),
                        ("admin", "Admin"),
                        ("member", "Member"),
                    ],
                    default="member",
                    max_length=20,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
