"""Parse East Africa mobile money SMS confirmation texts."""

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
    digits = re.sub(r"\D", "", value or "")
    return digits


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

  # M-Pesa Kenya / Tanzania patterns
    if "mpesa" in lower or "m-pesa" in lower or "confirmed" in lower and "ksh" in lower:
        provider = "mpesa"
        currency = "KES"
        amount_match = re.search(
            r"(?:confirmed\.?\s*)?(?:ksh|kes)[\s.]*([\d,]+(?:\.\d{1,2})?)",
            raw,
            re.I,
        ) or re.search(r"received\s+(?:ksh|kes)[\s.]*([\d,]+(?:\.\d{1,2})?)", raw, re.I)
        if amount_match:
            amount = _amount_from_match(amount_match.groups())
            confidence += 0.25
        txn_match = re.search(r"confirmation code\s+([A-Z0-9]{8,12})", raw, re.I)
        if txn_match:
            txn_reference = txn_match.group(1)
            confidence += 0.15
        phone_match = re.search(r"from\s+(\d{9,12})", raw, re.I)
        if phone_match:
            payer_phone = _normalize_phone(phone_match.group(1))
            confidence += 0.1

    # MTN MoMo Uganda / Rwanda
    elif "mtn" in lower or "mobile money" in lower or "momo" in lower:
        provider = "mtn_momo"
        if "ugx" in lower:
            currency = "UGX"
        elif "rwf" in lower or "frw" in lower:
            currency = "RWF"
        amount_match = re.search(
            r"(?:received|sent|deposited|withdrawn)\s+(?:ugx|rwf|frw)?[\s.]*([\d,]+(?:\.\d{1,2})?)",
            raw,
            re.I,
        ) or re.search(r"(UGX|RWF|FRW)[\s.]*([\d,]+(?:\.\d{1,2})?)", raw, re.I)
        if amount_match:
            groups = amount_match.groups()
            if groups[0] and groups[0].upper() in CURRENCY_ALIASES and len(groups) > 1:
                currency = CURRENCY_ALIASES[groups[0].upper()]
                amount = _amount_from_match((groups[1],))
            else:
                amount = _amount_from_match(groups)
            confidence += 0.25
        txn_match = re.search(r"(?:id|ref|reference|txn)[:\s#]*([A-Z0-9]{6,20})", raw, re.I)
        if txn_match:
            txn_reference = txn_match.group(1)
            confidence += 0.1
        phone_match = re.search(r"from\s+(\d{9,12})", raw, re.I)
        if phone_match:
            payer_phone = _normalize_phone(phone_match.group(1))

    # Airtel Money
    elif "airtel" in lower or "airtel money" in lower:
        provider = "airtel_money"
        amount_match = re.search(
            r"(?:received|sent)\s+(?:ugx|kes|tzs|rwf)?[\s.]*([\d,]+(?:\.\d{1,2})?)",
            raw,
            re.I,
        )
        if amount_match:
            amount = _amount_from_match(amount_match.groups())
            confidence += 0.2
        for code in ("UGX", "KES", "TZS", "RWF"):
            if code.lower() in lower:
                currency = code
        txn_match = re.search(r"(?:txn|transaction|ref)[:\s#]*([A-Z0-9]{6,20})", raw, re.I)
        if txn_match:
            txn_reference = txn_match.group(1)

    # Generic amount + currency fallback
    if amount is None:
        generic = re.search(
            r"\b(UGX|KES|TZS|RWF|KSH)[\s.]*([\d,]+(?:\.\d{1,2})?)",
            raw,
            re.I,
        )
        if generic:
            currency = CURRENCY_ALIASES.get(generic.group(1).upper(), generic.group(1).upper())
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
