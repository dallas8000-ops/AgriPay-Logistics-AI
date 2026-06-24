#!/usr/bin/env python3
"""
E2E MTN MoMo sandbox requestToPay (after mtn-provision-sandbox.py).

Sandbox test payer MSISDN (MTN docs): 46733123450 (disbursement) / use approved sandbox numbers
from your momodeveloper product page. Default tries Uganda format 256772123456.

Requires: MTN_MOMO_* in backend/.env, Django running, DEBUG=True for simulated bypass off.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
API = os.environ.get("BURN_TEST_API", "http://127.0.0.1:8000")
TEST_PAYER = os.environ.get("MTN_TEST_PAYER", "256772123456")


def load_env_flag(key: str) -> bool:
    env_path = ROOT / "backend" / ".env"
    if not env_path.exists():
        return False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}=") and len(line.split("=", 1)[1].strip()) > 3:
            return True
    return bool(os.environ.get(key))


def main() -> int:
    print("=" * 72)
    print("E2E MTN MoMo sandbox requestToPay")
    print("=" * 72)

    if not all(load_env_flag(k) for k in ("MTN_MOMO_API_USER", "MTN_MOMO_API_KEY", "MTN_MOMO_SUBSCRIPTION_KEY")):
        print("ERROR: MTN credentials missing. Run configure-payment-keys.ps1 with subscription key.")
        return 1

    caps = requests.get(f"{API}/api/system/capabilities/", timeout=5).json()
    if caps.get("collection", {}).get("merchant_api", {}).get("providers", {}).get("mtn_momo") != "operational":
        print("ERROR: Restart Django after MTN provision — capabilities still show simulated.")
        return 1

    buyer = requests.post(f"{API}/api/auth/token/", json={"username": "mary_buyer", "password": "demo12345"})
    bh = {"Authorization": f"Bearer {buyer.json()['access']}", "Content-Type": "application/json"}

    farmer = requests.post(f"{API}/api/auth/token/", json={"username": "james_farmer", "password": "demo12345"})
    fh = {"Authorization": f"Bearer {farmer.json()['access']}", "Content-Type": "application/json"}

    listings = requests.get(f"{API}/api/marketplace/listings/", headers=bh).json()
    items = listings.get("results", [])
    if not items:
        created = requests.post(
            f"{API}/api/marketplace/listings/",
            headers=fh,
            json={
                "crop": "E2E Maize",
                "variety": "Sandbox",
                "quantity_kg": 100,
                "unit_price": "50",
                "location": "Kampala",
                "season": "dry",
                "country": "UG",
            },
            timeout=15,
        )
        if created.status_code not in (200, 201):
            print(f"ERROR: create listing HTTP {created.status_code}: {created.text}")
            return 1
        items = [created.json()]
        print(f"[OK] Created active listing id={items[0]['id']}")

    order = requests.post(
        f"{API}/api/marketplace/orders/",
        headers=bh,
        json={"listing": items[0]["id"], "quantity_kg": 5, "delivery_address": "MTN E2E test"},
    ).json()

    pay = requests.post(
        f"{API}/api/payments/",
        headers=bh,
        json={"order_id": order["id"], "provider": "mtn_momo", "phone_number": TEST_PAYER},
        timeout=30,
    )
    print(f"Payment initiate HTTP {pay.status_code}")
    if pay.status_code not in (200, 201):
        print(pay.text)
        return 1

    body = pay.json()
    checkout = body.get("checkout", {})
    payment_id = body.get("payment", {}).get("id")
    ref = checkout.get("reference")
    print(f"[OK] requestToPay sent — reference={ref}")
    print(f"     integration_mode={checkout.get('integration_mode')}")
    print(f"     message={checkout.get('message')}")

    if checkout.get("integration_mode") == "simulated":
        print("ERROR: still simulated — check MTN credentials and restart backend")
        return 1

    print("[..] Polling payment status (approve prompt on sandbox device if required)...")
    for i in range(15):
        time.sleep(3)
        st = requests.get(f"{API}/api/payments/{payment_id}/status/", headers=bh, timeout=15)
        if st.status_code != 200:
            continue
        data = st.json()
        status = data.get("status") or data.get("payment", {}).get("status")
        provider_status = data.get("provider_status", "")
        print(f"     poll {i + 1}: status={status} provider={provider_status}")
        if status == "completed":
            print("[OK] MTN sandbox payment completed end-to-end")
            return 0
        if status == "failed":
            print("ERROR: payment failed")
            return 1

    print("WARN: payment still processing — sandbox may need manual approval on test handset")
    return 1


if __name__ == "__main__":
    sys.exit(main())
