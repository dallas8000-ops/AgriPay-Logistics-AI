"""Flutterwave aggregator — single sandbox integration for MoMo + card checkout."""

from __future__ import annotations

import uuid
from decimal import Decimal

import requests
from django.conf import settings


class FlutterwaveError(Exception):
    pass


class FlutterwaveClient:
    BASE_URL = "https://api.flutterwave.com/v3"

    def is_configured(self) -> bool:
        return bool(settings.FLUTTERWAVE_SECRET_KEY)

    def is_test_mode(self) -> bool:
        key = settings.FLUTTERWAVE_SECRET_KEY or ""
        return "TEST" in key.upper()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def initiate_standard_payment(
        self,
        *,
        tx_ref: str,
        amount: Decimal,
        currency: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        title: str,
        description: str,
        redirect_url: str,
    ) -> dict:
        if not self.is_configured():
            raise FlutterwaveError(
                "Flutterwave is not configured. Set FLUTTERWAVE_SECRET_KEY in backend/.env."
            )

        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "redirect_url": redirect_url,
            "customer": {
                "email": customer_email or f"noemail+{tx_ref}@agripay.local",
                "phonenumber": customer_phone,
                "name": customer_name or "Customer",
            },
            "customizations": {
                "title": title[:50],
                "description": description[:200],
            },
            "payment_options": settings.FLUTTERWAVE_PAYMENT_OPTIONS,
        }

        res = requests.post(
            f"{self.BASE_URL}/payments",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        data = res.json()
        if res.status_code >= 400 or data.get("status") != "success":
            raise FlutterwaveError(data.get("message", "Flutterwave payment initiation failed"))

        return {
            "link": data["data"]["link"],
            "flw_ref": data["data"].get("flw_ref", ""),
            "tx_ref": tx_ref,
            "integration_mode": "sandbox" if self.is_test_mode() else "live",
            "provider": "flutterwave",
            "message": "Complete payment on the Flutterwave checkout page (sandbox or live per your keys).",
        }

    def verify_transaction(self, tx_ref: str) -> dict:
        if not self.is_configured():
            raise FlutterwaveError("Flutterwave is not configured.")

        res = requests.get(
            f"{self.BASE_URL}/transactions/verify_by_reference",
            params={"tx_ref": tx_ref},
            headers=self._headers(),
            timeout=30,
        )
        data = res.json()
        if res.status_code >= 400 or data.get("status") != "success":
            raise FlutterwaveError(data.get("message", "Verification failed"))

        txn = data["data"]
        return {
            "status": txn.get("status", ""),
            "amount": txn.get("amount"),
            "currency": txn.get("currency"),
            "tx_ref": txn.get("tx_ref", tx_ref),
            "flw_ref": txn.get("id"),
            "payment_type": txn.get("payment_type", ""),
        }

    @staticmethod
    def new_tx_ref(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

    def webhook_valid(self, signature: str) -> bool:
        secret = settings.FLUTTERWAVE_WEBHOOK_SECRET
        if not secret:
            return settings.DEBUG
        return signature == secret
