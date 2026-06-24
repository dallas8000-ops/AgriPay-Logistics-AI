from django.core.management.base import BaseCommand

from apps.ai_services.market_data.crops import reload_snapshot
from apps.ai_services.market_data.fx import clear_fx_cache, fetch_live_fx_rates


class Command(BaseCommand):
    help = "Refresh live FX cache and reload multinational crop market snapshot."

    def handle(self, *args, **options):
        clear_fx_cache()
        fx = fetch_live_fx_rates()
        snapshot = reload_snapshot()

        self.stdout.write(
            self.style.SUCCESS(
                f"FX: {fx.get('source')} "
                f"({'live' if fx.get('live') else 'fallback'}) "
                f"updated {fx.get('updated_at') or 'n/a'}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Crop snapshot: {snapshot.get('source')} updated {snapshot.get('updated_at')}"
            )
        )
        for code in snapshot.get("countries", {}):
            crops = list(snapshot["countries"][code].get("crops", {}).keys())
            self.stdout.write(f"  {code}: {len(crops)} crops — {', '.join(crops[:5])}{'…' if len(crops) > 5 else ''}")
