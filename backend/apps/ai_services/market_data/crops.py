"""Multinational wholesale crop benchmarks (RATIN-aligned snapshot)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

_SNAPSHOT_PATH = Path(__file__).resolve().parent / "snapshots" / "multinational_crops.json"
_snapshot_cache: dict | None = None


def load_snapshot() -> dict:
    global _snapshot_cache
    if _snapshot_cache is None:
        with _SNAPSHOT_PATH.open(encoding="utf-8") as handle:
            _snapshot_cache = json.load(handle)
    return _snapshot_cache


def reload_snapshot() -> dict:
    global _snapshot_cache
    _snapshot_cache = None
    return load_snapshot()


def list_supported_countries() -> list[str]:
    return list(load_snapshot().get("countries", {}).keys())


def list_crops_for_country(country: str) -> list[str]:
    country_data = load_snapshot().get("countries", {}).get(country, {})
    return sorted(country_data.get("crops", {}).keys())


def get_crop_quote(crop: str, country: str) -> dict | None:
    """Local wholesale price quote for crop in country, if snapshot has it."""
    crop_key = crop.lower().strip()
    country_data = load_snapshot().get("countries", {}).get(country, {})
    crop_data = country_data.get("crops", {}).get(crop_key)
    if not crop_data:
        return None

    snapshot = load_snapshot()
    return {
        "unit_price_local": Decimal(str(crop_data["wholesale_per_kg"])),
        "currency": crop_data.get("currency", ""),
        "market": crop_data.get("market", country_data.get("default_market", "")),
        "observed_date": crop_data.get("observed"),
        "day_change_pct": crop_data.get("day_change_pct"),
        "month_change_pct": crop_data.get("month_change_pct"),
        "source": snapshot.get("source", "multinational_snapshot"),
        "attribution": snapshot.get("attribution"),
        "snapshot_updated_at": snapshot.get("updated_at"),
    }


def market_overview() -> dict:
    snapshot = load_snapshot()
    countries = {}
    for code, data in snapshot.get("countries", {}).items():
        countries[code] = {
            "default_market": data.get("default_market"),
            "crops": list_crops_for_country(code),
        }
    return {
        "source": snapshot.get("source"),
        "updated_at": snapshot.get("updated_at"),
        "attribution": snapshot.get("attribution"),
        "countries": countries,
    }
