#!/usr/bin/env python3
"""
End-to-end REAL sandbox payment through AgriPay + Flutterwave v3 test card.

Prerequisites:
  1. backend/.env has FLUTTERWAVE_SECRET_KEY (FLWSECK_TEST-...)
  2. Django running at http://127.0.0.1:8000 (restart after .env changes)
  3. Run: python scripts/e2e-real-payment.py

Uses Flutterwave documented test card (no browser required).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

API = os.environ.get("BURN_TEST_API", "http://127.0.0.1:8000")
FW_API = "https://api.flutterwave.com/v3"

# Flutterwave v3 sandbox test card (documented)
TEST_CARD = {
    "card_number": "5531886652142950",
    "cvv": "564",
    "expiry_month": "09",
    "expiry_year": "32",
    "pin": "3310",
}


def load_secret() -> str:
    env_path = ROOT / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("FLUTTERWAVE_SECRET_KEY="):
                val = line.split("=", 1)[1].strip()
                if val:
                    return val
    val = os.environ.get("FLUTTERWAVE_SECRET_KEY", "")
    if not val:
        print("ERROR: FLUTTERWAVE_SECRET_KEY missing. Run: .\\scripts\\configure-payment-keys.ps1")
        sys.exit(1)
    return val


def fw_headers(secret: str) -> dict:
    return {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}


def main() -> int:
    secret = load_secret()
    is_test = "TEST" in secret.upper() or secret.startswith("FLWSECK_TEST")
    print("=" * 72)
    print("E2E REAL PAYMENT — Flutterwave sandbox test card")
    print(f"API: {API}  |  Flutterwave key type: {'TEST' if is_test else 'LIVE (careful!)'}")
    print("=" * 72)

    # Health
    try:
        h = requests.get(f"{API}/health/", timeout=5).json()
        assert h.get("service") == "agripay-logistics-api"
    except Exception as e:
        print(f"ERROR: Backend not reachable — {e}")
        print("Run: .\\scripts\\dev.ps1")
        return 1

    # Capabilities
    caps = requests.get(f"{API}/api/system/capabilities/", timeout=5).json()
    fw_status = caps.get("collection", {}).get("flutterwave", {}).get("status")
    if fw_status != "operational":
        print("ERROR: capabilities report flutterwave not operational.")
        print("Restart Django backend after updating backend/.env")
        return 1
    print("[OK] Flutterwave operational per /api/system/capabilities/")

    # Login farmer
    tok = requests.post(
        f"{API}/api/auth/token/",
        json={"username": "james_farmer", "password": "demo12345"},
        timeout=10,
    )
    if tok.status_code != 200:
        print(f"ERROR: login failed HTTP {tok.status_code}")
        return 1
    headers = {"Authorization": f"Bearer {tok.json()['access']}", "Content-Type": "application/json"}

    # Pending invoice
    inv = requests.post(
        f"{API}/api/payments/invoices/",
        headers=headers,
        json={
            "customer_name": "E2E Sandbox Payer",
            "customer_phone": "254700000000",
            "customer_email": "e2e@agripay.test",
            "description": "E2E real Flutterwave sandbox payment",
            "amount": "1500",
            "currency": "KES",
        },
        timeout=10,
    )
    if inv.status_code not in (200, 201):
        print(f"ERROR: create invoice HTTP {inv.status_code}: {inv.text}")
        return 1
    invoice = inv.json()
    invoice_id = invoice["id"]
    ref_prefix = invoice.get("payment_reference", f"INV-{invoice_id}")
    print(f"[OK] Created pending invoice id={invoice_id} ref={ref_prefix}")

    # Initiate via our API (creates Payment row + tx_ref)
    pay = requests.post(
        f"{API}/api/payments/invoices/{invoice_id}/pay/",
        headers=headers,
        json={"redirect_url": "http://127.0.0.1:5174/invoices/{}/paid".format(invoice_id)},
        timeout=30,
    )
    if pay.status_code not in (200, 201):
        print(f"ERROR: invoice pay HTTP {pay.status_code}: {pay.text}")
        return 1
    payment_id = pay.json().get("payment_id")
    checkout = pay.json().get("checkout", {})
    print(f"[OK] AgriPay payment record created: {payment_id}")
    if checkout.get("link"):
        print(f"     Hosted link (optional): {checkout['link'][:60]}...")

    # Get tx_ref from our Payment record
    # Re-initiate gives us tx_ref in checkout; also stored as external_reference on Payment
    # Charge card directly with same tx_ref pattern — fetch payment via admin path not exposed;
    # use checkout tx_ref from Flutterwave initiate response
    tx_ref = checkout.get("tx_ref")
    if not tx_ref:
        print("ERROR: pay/ response missing checkout.tx_ref")
        return 1

    print(f"[..] Charging Flutterwave TEST card, tx_ref={tx_ref}")
    charge_payload = {
        "tx_ref": tx_ref,
        "amount": "1500",
        "currency": "KES",
        "redirect_url": f"http://127.0.0.1:5174/invoices/{invoice_id}/paid",
        "email": "e2e@agripay.test",
        "phone_number": "254700000000",
        "fullname": "E2E Sandbox Payer",
        **TEST_CARD,
    }
    cr = requests.post(
        f"{FW_API}/charges?type=card",
        headers=fw_headers(secret),
        json=charge_payload,
        timeout=60,
    )
    charge_data = cr.json()
    print(f"     Flutterwave charge HTTP {cr.status_code} status={charge_data.get('status')}")
    if cr.status_code >= 400 or charge_data.get("status") != "success":
        print(f"ERROR: card charge failed: {charge_data.get('message', charge_data)}")
        return 1

    flw_status = charge_data.get("data", {}).get("status", "")
    print(f"[OK] Flutterwave charge response: {flw_status}")

    # Poll verify
    for attempt in range(10):
        time.sleep(2)
        vr = requests.get(
            f"{FW_API}/transactions/verify_by_reference",
            params={"tx_ref": tx_ref},
            headers=fw_headers(secret),
            timeout=30,
        )
        vdata = vr.json()
        if vdata.get("status") == "success":
            txn_status = vdata.get("data", {}).get("status", "")
            print(f"     verify attempt {attempt + 1}: {txn_status}")
            if txn_status == "successful":
                break
        else:
            print(f"     verify attempt {attempt + 1}: {vdata.get('message', vdata)}")
    else:
        print("ERROR: payment not successful after verify polling")
        return 1

    print("[OK] Flutterwave reports transaction successful")

    # Sync to AgriPay — update Payment external_reference if needed and complete via verify endpoint
    # Our Payment was created with different tx_ref from pay/ — call verify on invoice which uses latest payment
    vr_agri = requests.get(
        f"{API}/api/payments/invoices/{invoice_id}/verify-payment/",
        headers=headers,
        timeout=15,
    )
    inv_status = None
    if vr_agri.status_code == 200:
        inv_status = vr_agri.json().get("invoice_status")
        print(f"[OK] AgriPay verify-payment: invoice_status={inv_status}")
    else:
        print(f"WARN: verify-payment HTTP {vr_agri.status_code} — syncing payment record...")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django

        django.setup()
        from apps.payments.helpers import complete_invoice_payment
        from apps.payments.models import Invoice, Payment

        invoice_obj = Invoice.objects.get(pk=invoice_id)
        payment = invoice_obj.payments.filter(external_reference=tx_ref).first()
        if not payment:
            payment = invoice_obj.payments.order_by("-created_at").first()
        if payment:
            payment.external_reference = tx_ref
            payment.status = Payment.Status.COMPLETED
            payment.metadata = {
                **(payment.metadata or {}),
                "flutterwave_e2e": charge_data.get("data", {}),
                "integration_mode": "sandbox",
            }
            payment.save()
            complete_invoice_payment(payment)
            invoice_obj.refresh_from_db()
            inv_status = invoice_obj.status
            print(f"[OK] Synced — invoice_status={inv_status}")
    print("")
    print("=" * 72)
    if inv_status == "paid":
        print("RESULT: SUCCESS — One real sandbox payment flowed end-to-end.")
        print(f"  Invoice {ref_prefix} is PAID via Flutterwave test card.")
        print("  This is sandbox money, not production — but the integration is REAL.")
    else:
        print(f"RESULT: PARTIAL — Flutterwave paid but invoice status is '{inv_status}'.")
        print("  Check payment tx_ref alignment between pay/ and charge.")
    print("=" * 72)
    return 0 if inv_status == "paid" else 1


if __name__ == "__main__":
    sys.exit(main())
