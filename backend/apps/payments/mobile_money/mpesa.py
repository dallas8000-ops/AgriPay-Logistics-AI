import base64
from datetime import datetime
from typing import Any

import requests
from django.conf import settings

from .utils import normalize_msisdn


class MPesaError(Exception):
    pass


class MPesaClient:
    """Safaricom Daraja M-Pesa (sandbox or production)."""

    SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
    PROD_BASE = "https://api.safaricom.co.ke"

    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.env = settings.MPESA_ENV or "sandbox"
        self.callback_url = settings.MPESA_CALLBACK_URL

    @property
    def base_url(self) -> str:
        return self.SANDBOX_BASE if self.env == "sandbox" else self.PROD_BASE

    def is_configured(self) -> bool:
        return bool(
            self.consumer_key and self.consumer_secret and self.passkey and self.shortcode and self.callback_url
        )

    def get_access_token(self) -> str:
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        response = requests.get(
            url,
            headers={"Authorization": f"Basic {auth}"},
            timeout=30,
        )
        if response.status_code != 200:
            raise MPesaError(f"M-Pesa token failed ({response.status_code}): {response.text}")
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise MPesaError("M-Pesa token response missing access_token")
        return token

    def _password(self) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        data = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(data.encode()).decode()
        return password, timestamp

    def stk_push(self, *, amount: int, phone: str, account_reference: str, description: str) -> dict[str, Any]:
        token = self.get_access_token()
        password, timestamp = self._password()
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": normalize_msisdn(phone, "254"),
            "PartyB": self.shortcode,
            "PhoneNumber": normalize_msisdn(phone, "254"),
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": description,
        }
        response = requests.post(url, json=body, headers=headers, timeout=30)
        if response.status_code != 200:
            raise MPesaError(f"M-Pesa STK push failed ({response.status_code}): {response.text}")
        return response.json()
