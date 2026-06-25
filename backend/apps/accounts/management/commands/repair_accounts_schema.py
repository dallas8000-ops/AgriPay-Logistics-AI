"""
One-time repair when django_migrations is out of sync with the real schema.

Symptom: migrate fails with ``relation "accounts_farmerprofile" does not exist``
while ``accounts.0001_initial`` is already recorded — usually because 0001 was
faked, the Postgres volume was partially reset, or DATABASE_URL pointed at a
different database than the one that was originally migrated.

This command does NOT patch migrations. It aligns the database with 0001, then
you run ``migrate`` normally.

Usage (Railway shell or one-off):

    python manage.py repair_accounts_schema --dry-run
    python manage.py repair_accounts_schema
    python manage.py migrate --noinput
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

_PROFILE_MODELS = ("BuyerProfile", "DriverProfile", "FarmerProfile", "VendorProfile")


class Command(BaseCommand):
    help = "Repair accounts tables when 0001_initial is recorded but profile tables are missing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report mismatch only; do not change the database.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        connection = connections["default"]
        tables = set(connection.introspection.table_names())

        recorder = MigrationRecorder(connection)
        applied = {name for app, name in recorder.applied_migrations() if app == "accounts"}

        if "0001_initial" not in applied:
            self.stdout.write("accounts.0001_initial is not recorded — run migrate normally.")
            return

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        state = loader.project_state([("accounts", "0001_initial")])
        apps = state.apps

        user = apps.get_model("accounts", "User")
        if user._meta.db_table not in tables:
            raise CommandError(
                "accounts_user is missing but 0001_initial is recorded. "
                "This database needs a full accounts reset or a DBA review — "
                "do not fake-repair here."
            )

        missing = []
        for model_name in _PROFILE_MODELS:
            model = apps.get_model("accounts", model_name)
            if model._meta.db_table not in tables:
                missing.append(model)

        if not missing:
            self.stdout.write(self.style.SUCCESS("accounts profile tables match 0001_initial."))
            return

        names = [m._meta.db_table for m in missing]
        self.stdout.write(
            self.style.WARNING(
                "Schema drift: django_migrations has accounts.0001_initial but missing: "
                + ", ".join(names)
            )
        )

        later = sorted(n for n in applied if n != "0001_initial")
        if later:
            self.stdout.write(f"Will unrecord later accounts migrations: {', '.join(later)}")

        if dry_run:
            self.stdout.write("Dry run — no changes made.")
            return

        for migration_name in later:
            recorder.record_unapplied("accounts", migration_name)

        with connection.schema_editor() as schema_editor:
            for model in missing:
                schema_editor.create_model(model)
                self.stdout.write(f"Created {model._meta.db_table}")

        self.stdout.write(
            self.style.SUCCESS(
                "Repair complete. Run: python manage.py migrate --noinput"
            )
        )
