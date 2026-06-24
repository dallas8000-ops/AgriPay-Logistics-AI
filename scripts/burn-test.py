#!/usr/bin/env python3
"""
AgriPay live burn test — exercises payment paths and reports LIVE vs BLOCKED vs SIMULATED.
Run with backend up: python scripts/burn-test.py
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

import requests

BASE = os.environ.get("BURN_TEST_API", "http://127.0.0.1:8000")
FRONTEND = os.environ.get("BURN_TEST_FRONTEND", "http://127.0.0.1:5174")

results: list[dict] = []


def record(phase: str, name: str, status: str, detail: str, extra: dict | None = None):
    row = {"phase": phase, "test": name, "status": status, "detail": detail}
    if extra:
        row.update(extra)
    results.append(row)
    icon = {"PASS": "+", "FAIL": "X", "SKIP": "-", "LIVE": "*", "BLOCKED": "!", "SIMULATED": "~"}.get(status, "?")
    print(f"  [{icon} {status:10}] {name}: {detail}")


def main() -> int:
    print("=" * 72)
    print("AGRIPAY LIVE BURN TEST")
    print(f"API: {BASE}  |  Frontend: {FRONTEND}")
    print("=" * 72)

    # --- Phase 0: Infrastructure ---
    print("\n## Phase 0 — Infrastructure")
    try:
        r = requests.get(f"{BASE}/health/", timeout=5)
        h = r.json()
        if h.get("service") == "agripay-logistics-api" and h.get("database") == "connected":
            record("infra", "backend_health", "PASS", f"service={h['service']}, db={h['database']}")
        else:
            record("infra", "backend_health", "FAIL", str(h))
    except Exception as e:
        record("infra", "backend_health", "FAIL", str(e))
        print_summary()
        return 1

    try:
        r = requests.get(FRONTEND, timeout=5)
        if "AgriPay" in r.text:
            record("infra", "frontend", "PASS", f"HTTP {r.status_code}, title contains AgriPay")
        else:
            record("infra", "frontend", "FAIL", "Wrong app or missing AgriPay title")
    except Exception as e:
        record("infra", "frontend", "FAIL", str(e))

    # --- Phase 1: Capabilities (what is actually configured) ---
    print("\n## Phase 1 — Deployment capabilities (source of truth)")
    try:
        caps = requests.get(f"{BASE}/api/system/capabilities/", timeout=5).json()
        record("caps", "product_mode", "PASS", caps.get("product_mode", "?"))
        record("caps", "product_name", "PASS", caps.get("product_name", "?"))

        for key in ("personal_transfer", "sms_reconciliation"):
            c = caps["collection"][key]
            record("caps", key, "LIVE" if c["status"] == "operational" else "BLOCKED", c["status"])

        fw = caps["collection"].get("flutterwave", {})
        fw_status = fw.get("status", "not_configured")
        record(
            "caps",
            "flutterwave",
            "LIVE" if fw_status == "operational" else "BLOCKED",
            fw.get("description", fw_status)[:80],
        )

        merchant = caps["collection"]["merchant_api"]
        record(
            "caps",
            "merchant_api",
            "LIVE" if merchant["status"] == "operational" else "BLOCKED",
            f"providers={merchant.get('providers', {})}",
        )

        stripe = caps["collection"]["stripe"]
        record(
            "caps",
            "stripe",
            "LIVE" if stripe["status"] == "operational" else "BLOCKED",
            stripe.get("description", "")[:60],
        )

        if caps.get("warnings"):
            for w in caps["warnings"]:
                record("caps", "warning", "BLOCKED", w[:100])
    except Exception as e:
        record("caps", "capabilities_endpoint", "FAIL", str(e))
        caps = {}

    flutterwave_live = caps.get("collection", {}).get("flutterwave", {}).get("status") == "operational"
    merchant_live = caps.get("collection", {}).get("merchant_api", {}).get("status") == "operational"

    # --- Phase 2: Auth ---
    print("\n## Phase 2 — Authentication")
    token = None
    try:
        r = requests.post(
            f"{BASE}/api/auth/token/",
            json={"username": "james_farmer", "password": "demo12345"},
            timeout=10,
        )
        if r.status_code != 200:
            record("auth", "login_farmer", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")
            print_summary()
            return 1
        token = r.json()["access"]
        record("auth", "login_farmer", "PASS", "james_farmer JWT obtained")
    except Exception as e:
        record("auth", "login_farmer", "FAIL", str(e))
        print_summary()
        return 1

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # --- Phase 3: Personal transfer path (always operational) ---
    print("\n## Phase 3 — Personal transfer + SMS reconciliation (core product)")
    invoice_id = None
    try:
        r = requests.post(
            f"{BASE}/api/payments/invoices/",
            headers=headers,
            json={
                "customer_name": "Burn Test Buyer",
                "customer_phone": "+256700999888",
                "description": "Burn test invoice — maize delivery",
                "amount": "50000",
                "currency": "KES",
            },
            timeout=10,
        )
        if r.status_code in (200, 201):
            inv = r.json()
            invoice_id = inv["id"]
            ref = inv.get("payment_reference", "?")
            record("personal", "create_invoice", "PASS", f"id={invoice_id}, ref={ref}")
        else:
            record("personal", "create_invoice", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        record("personal", "create_invoice", "FAIL", str(e))

    if invoice_id:
        try:
            r = requests.get(
                f"{BASE}/api/payments/invoices/{invoice_id}/instructions/",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                inst = r.json()
                record(
                    "personal",
                    "pay_instructions",
                    "LIVE",
                    f"payee={inst.get('payee_phone')} ref={inst.get('payment_reference')} "
                    f"mode={inst.get('collection_mode')}",
                )
            else:
                record("personal", "pay_instructions", "FAIL", f"HTTP {r.status_code}")
        except Exception as e:
            record("personal", "pay_instructions", "FAIL", str(e))

    sample_sms = (
        "MTN Mobile Money: You have received KES 50,000 from 256700999888. "
        f"Transaction ID: BURNTEST01. Ref INV-{invoice_id or 1}"
    )
    try:
        r = requests.post(
            f"{BASE}/api/payments/ledger/parse_sms/",
            headers=headers,
            json={"text": sample_sms},
            timeout=10,
        )
        if r.status_code == 200:
            p = r.json()
            record(
                "personal",
                "sms_parse",
                "PASS",
                f"amount={p.get('amount')} ref={p.get('order_reference')} "
                f"confidence={p.get('confidence')}",
            )
        else:
            record("personal", "sms_parse", "FAIL", f"HTTP {r.status_code}")
    except Exception as e:
        record("personal", "sms_parse", "FAIL", str(e))

    ledger_id = None
    try:
        r = requests.post(
            f"{BASE}/api/payments/ledger/",
            headers=headers,
            json={"raw_sms": sample_sms, "source": "sms_paste"},
            timeout=10,
        )
        if r.status_code in (200, 201):
            entry = r.json()
            ledger_id = entry["id"]
            record(
                "personal",
                "ledger_record",
                "PASS",
                f"entry={ledger_id} status={entry.get('status')} "
                f"invoice_match={entry.get('invoice')}",
            )
        else:
            record("personal", "ledger_record", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        record("personal", "ledger_record", "FAIL", str(e))

    if ledger_id and invoice_id:
        try:
            r = requests.get(f"{BASE}/api/payments/invoices/{invoice_id}/", headers=headers, timeout=10)
            inv_status_before = r.json().get("status") if r.status_code == 200 else "?"
            if inv_status_before == "paid":
                record("personal", "auto_reconcile", "PASS", "Invoice auto-marked paid from SMS match")
            elif ledger_id:
                r2 = requests.post(
                    f"{BASE}/api/payments/ledger/{ledger_id}/match-invoice/",
                    headers=headers,
                    json={"invoice_id": invoice_id},
                    timeout=10,
                )
                if r2.status_code == 200:
                    record("personal", "manual_match_invoice", "PASS", f"invoice_status={r2.json().get('invoice_status')}")
                else:
                    record("personal", "manual_match_invoice", "FAIL", f"HTTP {r2.status_code}")
        except Exception as e:
            record("personal", "reconcile", "FAIL", str(e))

    try:
        r = requests.get(f"{BASE}/api/payments/ledger/summary/", headers=headers, timeout=10)
        if r.status_code == 200:
            s = r.json()
            record(
                "personal",
                "ledger_summary",
                "PASS",
                f"pending_invoices={s.get('pending_invoices_count')} "
                f"unmatched_sms={s.get('unmatched_entries_count')}",
            )
        else:
            record("personal", "ledger_summary", "FAIL", f"HTTP {r.status_code}")
    except Exception as e:
        record("personal", "ledger_summary", "FAIL", str(e))

    # --- Phase 4: Flutterwave (only if keys configured) ---
    print("\n## Phase 4 — Flutterwave aggregator checkout")
    fw_invoice_id = None
    try:
        r = requests.post(
            f"{BASE}/api/payments/invoices/",
            headers=headers,
            json={
                "customer_name": "Flutterwave Burn Test",
                "customer_phone": "+256700111222",
                "description": "Separate pending invoice for aggregator test",
                "amount": "1000",
                "currency": "KES",
            },
            timeout=10,
        )
        if r.status_code in (200, 201):
            fw_invoice_id = r.json()["id"]
    except Exception:
        pass

    test_inv = fw_invoice_id or invoice_id
    if not test_inv:
        record("flutterwave", "pay_endpoint", "SKIP", "No invoice to test")
    elif not flutterwave_live:
        r = requests.post(
            f"{BASE}/api/payments/invoices/{test_inv}/pay/",
            headers=headers,
            json={"redirect_url": f"{FRONTEND}/invoices/{test_inv}/paid"},
            timeout=15,
        )
        if r.status_code == 503:
            record(
                "flutterwave",
                "pay_without_keys",
                "BLOCKED",
                "Correctly returns 503 — keys not configured (expected)",
            )
        elif r.status_code == 400 and "pending" in r.text.lower():
            record("flutterwave", "pay_without_keys", "SKIP", "Invoice not pending (already paid in prior step)")
        else:
            record("flutterwave", "pay_without_keys", "FAIL", f"Expected 503, got HTTP {r.status_code}: {r.text[:80]}")
    else:
        try:
            r = requests.post(
                f"{BASE}/api/payments/invoices/{test_inv}/pay/",
                headers=headers,
                json={"redirect_url": f"{FRONTEND}/invoices/{test_inv}/paid"},
                timeout=30,
            )
            if r.status_code in (200, 201):
                checkout = r.json().get("checkout", {})
                link = checkout.get("link", "")
                if link.startswith("https://"):
                    record("flutterwave", "initiate_checkout", "LIVE", f"checkout link returned ({link[:50]}…)")
                else:
                    record("flutterwave", "initiate_checkout", "FAIL", "No HTTPS checkout link in response")
            else:
                record("flutterwave", "initiate_checkout", "FAIL", f"HTTP {r.status_code}: {r.text[:150]}")
        except Exception as e:
            record("flutterwave", "initiate_checkout", "FAIL", str(e))

    # --- Phase 5: Direct merchant API ---
    print("\n## Phase 5 — Direct MTN/Airtel/M-Pesa merchant API")
    buyer_token = None
    try:
        br = requests.post(
            f"{BASE}/api/auth/token/",
            json={"username": "mary_buyer", "password": "demo12345"},
            timeout=10,
        )
        if br.status_code == 200:
            buyer_token = br.json()["access"]
            record("merchant", "login_buyer", "PASS", "mary_buyer JWT obtained")
    except Exception as e:
        record("merchant", "login_buyer", "FAIL", str(e))

    order_id = None
    if buyer_token:
        bh = {"Authorization": f"Bearer {buyer_token}", "Content-Type": "application/json"}
        try:
            listings = requests.get(f"{BASE}/api/marketplace/listings/", headers=bh, timeout=10).json()
            items = listings.get("results", listings if isinstance(listings, list) else [])
            if items:
                lid = items[0]["id"]
                r = requests.post(
                    f"{BASE}/api/marketplace/orders/",
                    headers=bh,
                    json={"listing": lid, "quantity_kg": 10, "delivery_address": "Burn test address"},
                    timeout=10,
                )
                if r.status_code in (200, 201):
                    order_id = r.json()["id"]
                    record("merchant", "create_order", "PASS", f"order_id={order_id}")
        except Exception as e:
            record("merchant", "create_order", "FAIL", str(e))

    if order_id and buyer_token:
        bh = {"Authorization": f"Bearer {buyer_token}", "Content-Type": "application/json"}
        r = requests.post(
            f"{BASE}/api/payments/",
            headers=bh,
            json={"order_id": order_id, "provider": "mtn_momo", "phone_number": "+256700123456"},
            timeout=15,
        )
        if not merchant_live:
            if r.status_code == 503:
                record("merchant", "mtn_checkout_no_keys", "BLOCKED", "Correctly blocked without MTN credentials")
            elif r.status_code in (200, 201):
                mode = r.json().get("checkout", {}).get("integration_mode", "?")
                if mode == "simulated":
                    record(
                        "merchant",
                        "mtn_checkout",
                        "SIMULATED",
                        "DEBUG mode allows simulated merchant flow — no real USSD sent",
                    )
                else:
                    record("merchant", "mtn_checkout", "LIVE", f"integration_mode={mode}")
            else:
                record("merchant", "mtn_checkout", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")
        else:
            if r.status_code in (200, 201):
                record("merchant", "mtn_checkout", "LIVE", "Merchant API call accepted — verify USSD on device")
            else:
                record("merchant", "mtn_checkout", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")

        r2 = requests.get(
            f"{BASE}/api/payments/collect/instructions/?order_id={order_id}",
            headers=bh,
            timeout=10,
        )
        if r2.status_code == 200:
            record(
                "merchant",
                "personal_instructions_for_order",
                "LIVE",
                f"ref={r2.json().get('payment_reference')} (honest default path)",
            )

    print_summary(caps)
    fails = sum(1 for x in results if x["status"] == "FAIL")
    return 1 if fails else 0


def print_summary(caps: dict | None = None):
    print("\n" + "=" * 72)
    print("BURN TEST SUMMARY")
    print("=" * 72)

    by_status = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    for st in ("PASS", "LIVE", "BLOCKED", "SIMULATED", "SKIP", "FAIL"):
        if st in by_status:
            print(f"  {st}: {by_status[st]}")

    print("\n--- VERDICT ---")
    fails = by_status.get("FAIL", 0)
    live_count = by_status.get("LIVE", 0)
    blocked = by_status.get("BLOCKED", 0)

    if fails:
        print("  RESULT: FAIL — fix failing checks above before showing clients.")
    else:
        print("  RESULT: INFRA + CORE PATHS OK")

    fw = (caps or {}).get("collection", {}).get("flutterwave", {}).get("status")
    merchant = (caps or {}).get("collection", {}).get("merchant_api", {}).get("status")
    mtn = (caps or {}).get("collection", {}).get("merchant_api", {}).get("providers", {}).get("mtn_momo")
    print("\n--- CAN YOU SHOW A CLIENT A REAL MONEY COLLECTION? ---")
    if fw == "operational":
        print("  YES — Flutterwave aggregator checkout is configured.")
    elif merchant == "operational" or mtn == "operational":
        print("  YES — direct merchant API (e.g. MTN MoMo sandbox) is live. Run scripts/e2e-mtn-momo.py to confirm.")
    else:
        print("  YES (personal only) — create invoice -> share pay instructions -> paste SMS -> reconcile.")
        print("  That is honest for small traders; it is NOT a live merchant API checkout.")

    print("\n--- NEXT ACTION ---")
    if merchant == "operational" or mtn == "operational":
        print("  Build complete for payments without Flutterwave. Aggregator keys are optional.")
    elif fw != "operational":
        print("  Optional: add FLUTTERWAVE_SECRET_KEY (test) for aggregator checkout.")
        print("  Or: add MTN_MOMO_* sandbox creds (scripts/configure-payment-keys.ps1).")
        print("  Until then: personal-transfer + SMS reconcile only.")
    print("=" * 72)

    out = os.path.join(os.path.dirname(__file__), "burn-test-results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"results": results, "caps": caps}, f, indent=2)
    print(f"\nFull JSON: {out}")


if __name__ == "__main__":
    sys.exit(main())
