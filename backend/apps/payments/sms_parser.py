"""Parse East Africa mobile money SMS confirmation texts.

Regex-based extraction — handles common formats, not every provider variant.
Long-tail SMS drift will miss; treat confidence scores as hints, not guarantees.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass
class ParsedSmsPayment:
    amount: Decimal | None
    currency: str
    provider: str
    txn_reference: str
    payer_phone: str
    payee_phone: str
    order_reference: str
    received_at: datetime | None
    confidence: float
    raw_text: str
    fields: dict[str, Any]


CURRENCY_ALIASES = {
    "UGX": "UGX",
    "KES": "KES",
    "KSH": "KES",
    "KSH.": "KES",
    "TZS": "TZS",
    "RWF": "RWF",
    "FRW": "RWF",
}

ORDER_REF_PATTERN = re.compile(r"\b(AGR|ORDER|INV)[- ]?(\d+)\b", re.I)

# Real-world samples used in tests — formats drift by country and OS version.
MPESA_MARKERS = ("mpesa", "m-pesa", "m pesa")
MTN_MARKERS = ("mtn", "momo", "mobile money")
AIRTEL_MARKERS = ("airtel", "airtel money")


def _amount_from_match(groups: tuple) -> Decimal | None:
    for g in groups:
        if not g:
            continue
        try:
            return Decimal(str(g).replace(",", ""))
        except (InvalidOperation, ValueError):
            continue
    return None


def _normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _is_mpesa_sms(lower: str) -> bool:
    if any(m in lower for m in MPESA_MARKERS):
        return True
    # Safaricom: "ABCD1234 Confirmed. Ksh500.00 received from..."
    if "confirmed" in lower and ("ksh" in lower or "kes" in lower):
        return True
    return False


def _is_mtn_sms(lower: str) -> bool:
    return any(m in lower for m in MTN_MARKERS) or "y'ello" in lower or "yello" in lower


def _is_airtel_sms(lower: str) -> bool:
    return any(m in lower for m in AIRTEL_MARKERS)


def _parse_mpesa(raw: str, lower: str) -> tuple[str, str, Decimal | None, str, str, float]:
    provider = "mpesa"
    currency = "KES" if "ksh" in lower or "kes" in lower else ""
    if "tzs" in lower:
        currency = "TZS"
    amount: Decimal | None = None
    txn_reference = ""
    payer_phone = ""
    confidence = 0.35

    amount_patterns = [
        r"(?:confirmed\.?\s*)?(?:ksh|kes)[\s.]*([\d,]+(?:\.\d{1,2})?)",
        r"(?:ksh|kes)[\s.]*([\d,]+(?:\.\d{1,2})?)\s+received",
        r"received\s+(?:ksh|kes)[\s.]*([\d,]+(?:\.\d{1,2})?)",
        r"you have received\s+(?:ksh|kes)\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:tzs)\s*([\d,]+(?:\.\d{1,2})?)\s+received",
    ]
    for pattern in amount_patterns:
        amount_match = re.search(pattern, raw, re.I)
        if amount_match:
            amount = _amount_from_match(amount_match.groups())
            confidence += 0.25
            break

    txn_match = re.search(
        r"(?:confirmation code|transaction id|receipt no\.?)\s+([A-Z0-9]{6,12})",
        raw,
        re.I,
    ) or re.search(r"^([A-Z0-9]{6,10})\s+confirmed", raw, re.I)
    if txn_match:
        txn_reference = txn_match.group(1)
        confidence += 0.15

    phone_match = re.search(
        r"from\s+(?:\d{9,12}|[A-Z\s]+?\s+)(\d{9,12})",
        raw,
        re.I,
    ) or re.search(r"from\s+(\d{9,12})", raw, re.I)
    if phone_match:
        payer_phone = _normalize_phone(phone_match.group(1))
        confidence += 0.1

    return provider, currency, amount, txn_reference, payer_phone, confidence


def _parse_mtn(raw: str, lower: str) -> tuple[str, str, Decimal | None, str, str, float]:
    provider = "mtn_momo"
    currency = ""
    if "ugx" in lower:
        currency = "UGX"
    elif "rwf" in lower or "frw" in lower:
        currency = "RWF"
    elif "tzs" in lower:
        currency = "TZS"
    amount: Decimal | None = None
    txn_reference = ""
    payer_phone = ""
    confidence = 0.35

    amount_patterns = [
        r"(?:received|sent|deposited|credited)\s+(?:ugx|rwf|frw|tzs)[\s.]*([\d,]+(?:\.\d{1,2})?)",
        r"(?:ugx|rwf|frw|tzs)[\s.]*([\d,]+(?:\.\d{1,2})?)\s+(?:has been )?received",
        r"you have received\s+(?:ugx|rwf|frw|tzs)[\s.]*([\d,]+(?:\.\d{1,2})?)",
        r"(UGX|RWF|FRW|TZS)[\s.]*([\d,]+(?:\.\d{1,2})?)",
    ]
    for pattern in amount_patterns:
        amount_match = re.search(pattern, raw, re.I)
        if amount_match:
            groups = amount_match.groups()
            if groups[0] and groups[0].upper() in CURRENCY_ALIASES and len(groups) > 1:
                currency = CURRENCY_ALIASES[groups[0].upper()]
                amount = _amount_from_match((groups[1],))
            else:
                amount = _amount_from_match(groups)
            confidence += 0.25
            break

    txn_match = re.search(
        r"(?:transaction id|financial transaction id|txn|trans id|ref(?:erence)?)"
        r"[:\s#]*([A-Z0-9]{6,20})",
        raw,
        re.I,
    )
    if txn_match:
        txn_reference = txn_match.group(1)
        confidence += 0.1

    phone_match = re.search(r"from\s+(\d{9,12})", raw, re.I)
    if phone_match:
        payer_phone = _normalize_phone(phone_match.group(1))
        confidence += 0.1

    return provider, currency, amount, txn_reference, payer_phone, confidence


def _parse_airtel(raw: str, lower: str) -> tuple[str, str, Decimal | None, str, str, float]:
    provider = "airtel_money"
    currency = ""
    amount: Decimal | None = None
    txn_reference = ""
    payer_phone = ""
    confidence = 0.35

    for code in ("UGX", "KES", "TZS", "RWF"):
        if code.lower() in lower:
            currency = code
            break

    amount_patterns = [
        r"(?:received|sent|credited)\s+(?:ugx|kes|tzs|rwf)?[\s.]*([\d,]+(?:\.\d{1,2})?)",
        r"(?:ugx|kes|tzs|rwf)\s*([\d,]+(?:\.\d{1,2})?)\s+has been received",
        r"you have received\s+(?:ugx|kes|tzs|rwf)[\s.]*([\d,]+(?:\.\d{1,2})?)",
    ]
    for pattern in amount_patterns:
        amount_match = re.search(pattern, raw, re.I)
        if amount_match:
            amount = _amount_from_match(amount_match.groups())
            confidence += 0.2
            break

    txn_match = re.search(
        r"(?:txn|transaction|financial transaction|ref(?:erence)?)[:\s#]*([A-Z0-9]{6,20})",
        raw,
        re.I,
    )
    if txn_match:
        txn_reference = txn_match.group(1)
        confidence += 0.1

    phone_match = re.search(r"from\s+(\d{9,12})", raw, re.I)
    if phone_match:
        payer_phone = _normalize_phone(phone_match.group(1))
        confidence += 0.1

    return provider, currency, amount, txn_reference, payer_phone, confidence


def parse_mobile_money_sms(text: str) -> ParsedSmsPayment:
    raw = (text or "").strip()
    lower = raw.lower()
    provider = "unknown"
    currency = ""
    amount: Decimal | None = None
    txn_reference = ""
    payer_phone = ""
    payee_phone = ""
    confidence = 0.35

    if _is_mpesa_sms(lower):
        provider, currency, amount, txn_reference, payer_phone, confidence = _parse_mpesa(raw, lower)
    elif _is_mtn_sms(lower):
        provider, currency, amount, txn_reference, payer_phone, confidence = _parse_mtn(raw, lower)
    elif _is_airtel_sms(lower):
        provider, currency, amount, txn_reference, payer_phone, confidence = _parse_airtel(raw, lower)

    if amount is None:
        generic = re.search(
            r"\b(UGX|KES|TZS|RWF|KSH)[\s.]*([\d,]+(?:\.\d{1,2})?)",
            raw,
            re.I,
        )
        if generic:
            currency = currency or CURRENCY_ALIASES.get(
                generic.group(1).upper(), generic.group(1).upper()
            )
            amount = _amount_from_match((generic.group(2),))
            confidence += 0.1

    order_ref = ""
    order_match = ORDER_REF_PATTERN.search(raw)
    if order_match:
        order_ref = f"{order_match.group(1).upper()}-{order_match.group(2)}"
        confidence += 0.2

    if amount is not None:
        confidence = min(confidence + 0.1, 0.95)

    return ParsedSmsPayment(
        amount=amount,
        currency=currency,
        provider=provider,
        txn_reference=txn_reference,
        payer_phone=payer_phone,
        payee_phone=payee_phone,
        order_reference=order_ref,
        received_at=None,
        confidence=round(confidence, 2),
        raw_text=raw,
        fields={
            "provider_guess": provider,
            "has_amount": amount is not None,
            "has_reference": bool(txn_reference),
            "has_order_reference": bool(order_ref),
        },
    )
