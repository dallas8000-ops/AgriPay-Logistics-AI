import re


def normalize_msisdn(phone: str, default_country_code: str = "256") -> str:
    """Strip formatting; ensure MSISDN includes country code without +."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0"):
        digits = default_country_code + digits[1:]
    if len(digits) <= 9 and not digits.startswith(default_country_code):
        digits = default_country_code + digits
    return digits


COUNTRY_DIAL_CODES = {
    "UG": "256",
    "KE": "254",
    "TZ": "255",
    "RW": "250",
}
