import base64
import uuid
from typing import Any

import requests
from django.conf import settings


class MTNMoMoError(Exception):
    pass


class MTNMoMoClient:
    """MTN MoMo Collection API (sandbox or production)."""

    SANDBOX_BASE = "https://sandbox.momodeveloper.mtn.com"
    PROD_BASE = "https://proxy.momoapi.mtn.com"

    def __init__(self):
        self.api_user = settings.MTN_MOMO_API_USER
        self.api_key = settings.MTN_MOMO_API_KEY
        self.subscription_key = settings.MTN_MOMO_SUBSCRIPTION_KEY
        self.env = settings.MTN_MOMO_ENV or "sandbox"
        self.target_env = getattr(settings, "MTN_MOMO_TARGET_ENV", None) or self.env
        self.callback_url = settings.MTN_MOMO_CALLBACK_URL

    @property
    def base_url(self) -> str:
        return self.SANDBOX_BASE if self.env == "sandbox" else self.PROD_BASE

    def is_configured(self) -> bool:
        return bool(self.api_user and self.api_key and self.subscription_key)

    def _basic_auth(self) -> str:
        token = base64.b64encode(f"{self.api_user}:{self.api_key}".encode()).decode()
        return f"Basic {token}"

    def get_access_token(self) -> str:
        url = f"{self.base_url}/collection/token/"
        headers = {
            "Authorization": self._basic_auth(),
            "Ocp-Apim-Subscription-Key": self.subscription_key,
        }
        response = requests.post(url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise MTNMoMoError(f"MTN token request failed ({response.status_code}): {response.text}")
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise MTNMoMoError("MTN token response missing access_token")
        return token

    def _sandbox_amount_currency(self, amount: str, currency: str) -> tuple[str, str]:
        """MTN sandbox target env only accepts EUR."""
        if self.env == "sandbox":
            return "1", "EUR"
        return amount, currency

    def request_to_pay(
        self,
        *,
        reference_id: str,
        amount: str,
        currency: str,
        phone: str,
        external_id: str,
        payer_message: str,
        payee_note: str,
    ) -> dict[str, Any]:
        token = self.get_access_token()
        amount, currency = self._sandbox_amount_currency(amount, currency)
        url = f"{self.base_url}/collection/v1_0/requesttopay"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": self.target_env if self.target_env != "production" else "mtnuganda",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
        }
        if self.callback_url:
            headers["X-Callback-Url"] = self.callback_url

        body = {
            "amount": amount,
            "currency": currency,
            "externalId": external_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone,
            },
            "payerMessage": payer_message,
            "payeeNote": payee_note,
        }
        response = requests.post(url, json=body, headers=headers, timeout=30)
        if response.status_code not in (200, 202):
            raise MTNMoMoError(f"MTN requestToPay failed ({response.status_code}): {response.text}")
        return {"reference_id": reference_id, "status": "PENDING"}

    def get_transaction_status(self, reference_id: str) -> dict[str, Any]:
        token = self.get_access_token()
        url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": self.target_env if self.target_env != "production" else "mtnuganda",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
        }
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise MTNMoMoError(f"MTN status check failed ({response.status_code}): {response.text}")
        return response.json()

    @staticmethod
    def new_reference_id() -> str:
        return str(uuid.uuid4())
