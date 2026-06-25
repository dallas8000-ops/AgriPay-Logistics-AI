"""Configure Stripe SDK from environment (lazy — must not block Django boot)."""
from __future__ import annotations

import os

import stripe


def stripe_api_key() -> str:
    return (os.environ.get("STRIPE_SECRET_KEY") or "").strip()


def get_stripe():
    key = stripe_api_key()
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not set")
    stripe.api_key = key
    return stripe
