"""Single source of truth for what the deployment actually supports."""

from django.conf import settings

from apps.payments.aggregator.flutterwave import FlutterwaveClient
from apps.payments.mobile_money import MobileMoneyService
from apps.payments.models import Payment


def _status_label(mode: str) -> str:
    if mode == "live":
        return "operational"
    if mode == "simulated":
        return "simulated"
    return "not_configured"


def build_capabilities() -> dict:
    modes = MobileMoneyService.provider_modes()
    stripe_live = bool(settings.STRIPE_SECRET_KEY)
    sms_gateway = bool(getattr(settings, "SMS_GATEWAY_URL", ""))
    whatsapp_gateway = bool(getattr(settings, "WHATSAPP_GATEWAY_URL", ""))
    product_mode = getattr(settings, "PRODUCT_MODE", "agri")
    flutterwave_live = FlutterwaveClient().is_configured()

    merchant_any_live = any(m == "live" for m in modes.values())
    warnings: list[str] = []

    if not flutterwave_live:
        warnings.append(
            "Flutterwave aggregator is not configured — online checkout links are unavailable. "
            "Set FLUTTERWAVE_SECRET_KEY for sandbox/live, or use personal-transfer + SMS reconciliation."
        )
    if not merchant_any_live:
        warnings.append(
            "Direct merchant mobile money APIs are not configured — provider API checkout is disabled in production."
        )
    if not stripe_live:
        warnings.append("Stripe card payments are not configured — card checkout is unavailable.")
    if not sms_gateway:
        warnings.append("SMS alerts are in-app records only — no SMS gateway is configured.")
    if not whatsapp_gateway:
        warnings.append("WhatsApp alerts are in-app records only — no WhatsApp gateway is configured.")

    return {
        "product_mode": product_mode,
        "product_name": (
            "Collections & Reconciliation"
            if product_mode == "sme_payments"
            else "AgriPay Logistics"
        ),
        "tagline": (
            "Unified mobile money ledger for East African SMEs — paste SMS, match payments, export-ready records."
            if product_mode == "sme_payments"
            else "For farmers and traders: collect on your personal MoMo number, reconcile SMS, optional marketplace."
        ),
        "invoices": {
            "status": "operational",
            "description": "Generic payment requests with INV- references — works for any sale, not only produce orders.",
        },
        "collection": {
            "personal_transfer": {
                "status": "operational",
                "description": (
                    "Buyers send to your personal MTN/Airtel/M-Pesa number with a payment reference. "
                    "No merchant account or provider API required."
                ),
            },
            "sms_reconciliation": {
                "status": "operational",
                "description": (
                    "You manually paste confirmation SMS text — we do not read your phone inbox. "
                    "Parser extracts amount and reference to match pending orders."
                ),
            },
            "merchant_api": {
                "status": "operational" if merchant_any_live else "not_configured",
                "providers": {
                    "mtn_momo": _status_label(modes[Payment.Provider.MTN_MOMO]),
                    "airtel_money": _status_label(modes[Payment.Provider.AIRTEL_MONEY]),
                    "mpesa": _status_label(modes[Payment.Provider.MPESA]),
                },
                "description": (
                    "Direct MTN/Airtel/M-Pesa merchant APIs when credentials are set."
                    if merchant_any_live
                    else "Requires provider sandbox/production credentials in backend/.env."
                ),
            },
            "stripe": {
                "status": "operational" if stripe_live else "not_configured",
                "description": (
                    "Card payments via Stripe PaymentIntents."
                    if stripe_live
                    else "Set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY to enable."
                ),
            },
            "flutterwave": {
                "status": "operational" if flutterwave_live else "not_configured",
                "description": (
                    "Aggregator checkout — MTN, Airtel, M-Pesa, and card via Flutterwave sandbox or live keys."
                    if flutterwave_live
                    else "Set FLUTTERWAVE_SECRET_KEY from dashboard.flutterwave.com (use test keys for sandbox)."
                ),
            },
        },
        "notifications": {
            "in_app": {"status": "operational"},
            "sms": {
                "status": "operational" if sms_gateway else "not_configured",
                "description": "Logged in-app only until SMS_GATEWAY_URL is configured.",
            },
            "whatsapp": {
                "status": "operational" if whatsapp_gateway else "not_configured",
                "description": "Logged in-app only until WHATSAPP_GATEWAY_URL is configured.",
            },
        },
        "ai_pricing": {
            "status": "rule_based",
            "description": (
                "Crop price hints use static tables and season multipliers — not live market data or machine learning."
            ),
            "available": product_mode == "agri",
        },
        "marketplace": {
            "status": "operational",
            "vertical": "agriculture",
            "available": product_mode == "agri",
            "description": "Produce listings and orders — optional for agri GTM; invoices work for any payment request.",
        },
        "logistics": {
            "status": "operational",
            "available": product_mode == "agri",
            "description": "Driver assignment and delivery tracking — manual status updates, not live GPS hardware integration.",
        },
        "warnings": warnings,
    }
