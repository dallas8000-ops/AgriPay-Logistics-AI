from decimal import Decimal

from django.conf import settings

from .market_data.crops import get_crop_quote
from .market_data.fx import get_fx_for_country


# USD/kg fallback when no local wholesale quote exists for a country/crop pair.
CROP_BASE_PRICES = {
    "maize": Decimal("0.25"),
    "beans": Decimal("0.85"),
    "coffee": Decimal("2.50"),
    "tea": Decimal("1.80"),
    "bananas": Decimal("0.30"),
    "tomatoes": Decimal("0.45"),
    "potatoes": Decimal("0.35"),
    "avocado": Decimal("0.90"),
    "rice": Decimal("0.55"),
    "sorghum": Decimal("0.28"),
    "cassava": Decimal("0.15"),
    "onions": Decimal("0.40"),
}

SEASON_MULTIPLIERS = {
    "long_rains": Decimal("0.95"),
    "short_rains": Decimal("1.05"),
    "dry": Decimal("1.15"),
}

COUNTRY_FX = {
    "UG": Decimal("3700"),
    "KE": Decimal("130"),
    "TZ": Decimal("2500"),
    "RW": Decimal("1250"),
}


def estimate_price(crop: str, country: str, quantity_kg: float, season: str) -> dict:
    crop_key = crop.lower().strip()
    season_mult = SEASON_MULTIPLIERS.get(season, Decimal("1.0"))
    qty = Decimal(str(quantity_kg))
    currency = settings.SUPPORTED_COUNTRIES.get(country, {}).get("currency", "UGX")
    fx_info = get_fx_for_country(country)
    quote = get_crop_quote(crop_key, country)

    bulk_discount = Decimal("0.98") if qty >= 500 else Decimal("1.0")
    if qty >= 2000:
        bulk_discount = Decimal("0.95")

    market_block = None
    if quote:
        unit_price = quote["unit_price_local"] * season_mult
        method = "live_market"
        method_note = (
            f"Wholesale benchmark from {quote['market']} "
            f"(observed {quote['observed_date'] or 'n/a'}). "
            f"FX {fx_info['base']}/{fx_info['quote']} at {fx_info['rate']:.2f} "
            f"({'live' if fx_info['live'] else 'cached fallback'})."
        )
        market_block = {
            "name": quote["market"],
            "observed_date": quote["observed_date"],
            "day_change_pct": quote["day_change_pct"],
            "month_change_pct": quote["month_change_pct"],
            "source": quote["source"],
            "snapshot_updated_at": quote["snapshot_updated_at"],
        }
        confidence = Decimal("0.88")
    else:
        base_usd = CROP_BASE_PRICES.get(crop_key, Decimal("0.50"))
        fx_rate = Decimal(str(fx_info["rate"]))
        unit_price = base_usd * season_mult * fx_rate
        method = "fx_adjusted"
        method_note = (
            f"No wholesale quote for {crop_key} in {country} — USD baseline × live FX "
            f"({fx_info['rate']:.2f} {fx_info['quote']}). Verify locally before listing."
        )
        confidence = Decimal("0.72") if crop_key in CROP_BASE_PRICES else Decimal("0.58")

    final_unit = (unit_price * bulk_discount).quantize(Decimal("0.01"))
    total = (final_unit * qty).quantize(Decimal("0.01"))
    risk_score = _compute_risk(crop_key, season, qty)

    trend = ""
    if market_block and market_block.get("day_change_pct") is not None:
        pct = market_block["day_change_pct"]
        trend = f" Market moved {pct:+.1f}% day-on-day."

    return {
        "crop": crop,
        "country": country,
        "quantity_kg": float(qty),
        "season": season,
        "unit_price": float(final_unit),
        "total_estimate": float(total),
        "currency": currency,
        "confidence": float(confidence),
        "risk_score": risk_score,
        "method": method,
        "method_note": method_note,
        "market": market_block,
        "fx": {
            "rate": fx_info["rate"],
            "base": fx_info["base"],
            "quote": fx_info["quote"],
            "updated_at": fx_info.get("updated_at"),
            "live": fx_info.get("live", False),
        },
        "factors": {
            "season_adjustment": float(season_mult),
            "bulk_discount": float(bulk_discount),
            "market_demand": "high" if crop_key in ("tomatoes", "onions", "bananas") else "moderate",
        },
        "summary": (
            f"Estimated {crop} at {final_unit} {currency}/kg for {qty}kg in {season.replace('_', ' ')} season. "
            f"Risk level: {risk_score['level']}.{trend}"
        ),
    }


def _compute_risk(crop: str, season: str, quantity: Decimal) -> dict:
    score = 30
    if season == "dry":
        score += 20
    if crop in ("tomatoes", "bananas"):
        score += 15
    if quantity > 1000:
        score += 10
    level = "low" if score < 40 else "medium" if score < 60 else "high"
    return {"score": score, "level": level, "notes": "Perishability and season volatility considered."}


def buyer_reliability_score(buyer_profile) -> dict:
    base = float(buyer_profile.reliability_score)
    orders = buyer_profile.total_orders
    adjustment = min(orders * 0.5, 15)
    score = min(base + adjustment, 100)
    tier = "trusted" if score >= 85 else "standard" if score >= 70 else "new"
    return {
        "score": round(score, 1),
        "tier": tier,
        "total_orders": orders,
        "summary": f"Buyer reliability: {tier} ({score:.0f}/100). Based on order history and dispute rate.",
    }


def route_summary(pickup: str, dropoff: str, distance_km: float = None) -> dict:
    dist = distance_km or 45.0
    eta_hours = dist / 35
    return {
        "pickup": pickup,
        "dropoff": dropoff,
        "estimated_distance_km": dist,
        "estimated_hours": round(eta_hours, 1),
        "summary": (
            f"Route from {pickup} to {dropoff}: ~{dist:.0f}km, "
            f"ETA {eta_hours:.1f}h via primary highway (estimated)."
        ),
        "conditions": "Dry season — moderate traffic expected near markets.",
    }
