"""Transaction fee helpers (sender-pays rail cost model)."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings


def transaction_fee() -> Decimal:
    """Total per-transaction fee charged to the sender (rail cost + markup)."""
    if not getattr(settings, "TRANSACTION_FEE_ENABLED", True):
        return Decimal("0.00")
    flat = Decimal(str(getattr(settings, "TRANSACTION_FEE_FLAT", "0.99")))
    markup = Decimal(str(getattr(settings, "TRANSACTION_FEE_MARKUP", "0.00")))
    return (flat + markup).quantize(Decimal("0.01"))


def total_with_fee(amount: Decimal) -> Decimal:
    """Sender total = amount + transaction_fee()."""
    return (amount + transaction_fee()).quantize(Decimal("0.01"))


def fee_breakdown() -> dict:
    flat = Decimal(str(getattr(settings, "TRANSACTION_FEE_FLAT", "0.99")))
    markup = Decimal(str(getattr(settings, "TRANSACTION_FEE_MARKUP", "0.00")))
    return {
        "rail_fee": str(flat.quantize(Decimal("0.01"))),
        "platform_markup": str(markup.quantize(Decimal("0.01"))),
        "total_fee": str((flat + markup).quantize(Decimal("0.01"))),
    }
