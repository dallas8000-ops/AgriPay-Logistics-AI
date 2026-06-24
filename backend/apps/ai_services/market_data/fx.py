"""Live USD → local FX for supported East African currencies."""

from __future__ import annotations

import time
from decimal import Decimal

import requests
from django.conf import settings

_FX_CACHE: dict | None = None
_FX_CACHE_AT: float = 0.0
_FX_TTL_SECONDS = 3600

# Static fallback when FX API is unreachable (approximate mid-2026 levels).
_FALLBACK_RATES = {
    "UG": Decimal("3700"),
    "KE": Decimal("130"),
    "TZ": Decimal("2500"),
    "RW": Decimal("1250"),
}


def _country_currency(country: str) -> str:
    return settings.SUPPORTED_COUNTRIES.get(country, {}).get("currency", "UGX")


def fetch_live_fx_rates() -> dict:
    """Return USD rates for UGX, KES, TZS, RWF. Uses cache, then API, then static fallback."""
    global _FX_CACHE, _FX_CACHE_AT

    now = time.time()
    if _FX_CACHE and (now - _FX_CACHE_AT) < _FX_TTL_SECONDS:
        return _FX_CACHE

    url = getattr(
        settings,
        "MARKET_DATA_FX_URL",
        "https://open.er-api.com/v6/latest/USD",
    )
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        payload = response.json()
        rates = payload.get("rates") or {}
        currencies = {_country_currency(c): c for c in _FALLBACK_RATES}
        resolved: dict[str, Decimal] = {}
        for currency, country in currencies.items():
            if currency in rates:
                resolved[country] = Decimal(str(rates[currency]))
        if len(resolved) == len(currencies):
            _FX_CACHE = {
                "rates": resolved,
                "updated_at": payload.get("time_last_update_utc"),
                "source": "exchangerate-api",
                "live": True,
            }
            _FX_CACHE_AT = now
            return _FX_CACHE
    except (requests.RequestException, ValueError, TypeError):
        pass

    _FX_CACHE = {
        "rates": dict(_FALLBACK_RATES),
        "updated_at": None,
        "source": "static_fallback",
        "live": False,
    }
    _FX_CACHE_AT = now
    return _FX_CACHE


def get_fx_for_country(country: str) -> dict:
    """FX metadata for a supported country code."""
    bundle = fetch_live_fx_rates()
    rate = bundle["rates"].get(country, _FALLBACK_RATES.get(country, Decimal("130")))
    currency = _country_currency(country)
    return {
        "rate": float(rate),
        "base": "USD",
        "quote": currency,
        "updated_at": bundle.get("updated_at"),
        "source": bundle.get("source"),
        "live": bundle.get("live", False),
    }


def clear_fx_cache() -> None:
    global _FX_CACHE, _FX_CACHE_AT
    _FX_CACHE = None
    _FX_CACHE_AT = 0.0
