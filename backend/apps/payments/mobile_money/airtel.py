from typing import Any

import requests
from django.conf import settings

from .utils import normalize_msisdn


class AirtelMoneyError(Exception):
    pass


class AirtelMoneyClient:
    """Airtel Africa Open API (UAT/sandbox)."""

    UAT_BASE = "https://openapiuat.airtel.africa"
    PROD_BASE = "https://openapi.airtel.africa"

    def __init__(self):
        self.client_id = settings.AIRTEL_MONEY_CLIENT_ID
        self.client_secret = settings.AIRTEL_MONEY_CLIENT_SECRET
        self.env = settings.AIRTEL_MONEY_ENV or "sandbox"
        self.country = settings.AIRTEL_MONEY_COUNTRY or "UG"
        self.currency = settings.AIRTEL_MONEY_CURRENCY or "UGX"

    @property
    def base_url(self) -> str:
        return self.UAT_BASE if self.env == "sandbox" else self.PROD_BASE

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_access_token(self) -> str:
        url = f"{self.base_url}/auth/oauth2/token"
        response = requests.post(
            url,
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            headers={"Content-Type": "application/json", "Accept": "*/*"},
            timeout=30,
        )
        if response.status_code != 200:
            raise AirtelMoneyError(f"Airtel token failed ({response.status_code}): {response.text}")
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise AirtelMoneyError("Airtel token response missing access_token")
        return token

    def collect_payment(self, *, transaction_id: str, amount: float, phone: str, reference: str) -> dict[str, Any]:
        token = self.get_access_token()
        msisdn = normalize_msisdn(phone, "256")
        url = f"{self.base_url}/merchant/v1/payments/"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Country": self.country,
            "X-Currency": self.currency,
        }
        body = {
            "reference": reference,
            "subscriber": {
                "country": self.country,
                "currency": self.currency,
                "msisdn": msisdn,
            },
            "transaction": {
                "amount": amount,
                "country": self.country,
                "currency": self.currency,
                "id": transaction_id,
            },
        }
        response = requests.post(url, json=body, headers=headers, timeout=30)
        if response.status_code not in (200, 201):
            raise AirtelMoneyError(f"Airtel collect failed ({response.status_code}): {response.text}")
        return response.json()

    def get_transaction_status(self, transaction_id: str) -> dict[str, Any]:
        token = self.get_access_token()
        url = f"{self.base_url}/standard/v1/payments/{transaction_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "*/*",
            "X-Country": self.country,
            "X-Currency": self.currency,
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise AirtelMoneyError(f"Airtel status failed ({response.status_code}): {response.text}")
        return response.json()
