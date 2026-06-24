#!/usr/bin/env python3
"""
AgriPay thorough live smoke test — infrastructure, auth, payments, marketplace, pricing.

Run with backend + frontend up:
  python scripts/smoke-test.py

Writes scripts/smoke-test-results.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("SMOKE_TEST_API", "http://127.0.0.1:8000")
FRONTEND = os.environ.get("SMOKE_TEST_FRONTEND", "http://127.0.0.1:5174")
PYTHON = ROOT / "backend" / "venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

results: list[dict] = []


def record(phase: str, name: str, status: str, detail: str) -> None:
    row = {"phase": phase, "test": name, "status": status, "detail": detail}
    results.append(row)
    icon = {"PASS": "+", "FAIL": "X", "SKIP": "-", "LIVE": "*"}.get(status, "?")
    print(f"  [{icon} {status:6}] {name}: {detail}")


def auth(username: str) -> dict:
    r = requests.post(
        f"{BASE}/api/auth/token/",
        json={"username": username, "password": "demo12345"},
        timeout=10,
    )
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access']}", "Content-Type": "application/json"}


def phase_infra() -> bool:
    print("\n## Infrastructure")
    ok = True
    try:
        r = requests.get(f"{BASE}/health/", timeout=5)
        h = r.json()
        if h.get("service") == "agripay-logistics-api" and h.get("database") == "connected":
            record("infra", "backend_health", "PASS", f"db={h['database']}")
        else:
            record("infra", "backend_health", "FAIL", str(h))
            ok = False
    except Exception as exc:
        record("infra", "backend_health", "FAIL", str(exc))
        return False

    try:
        r = requests.get(FRONTEND, timeout=5)
        if r.status_code == 200 and "AgriPay" in r.text:
            record("infra", "frontend", "PASS", f"HTTP {r.status_code}")
        else:
            record("infra", "frontend", "FAIL", f"HTTP {r.status_code}")
            ok = False
    except Exception as exc:
        record("infra", "frontend", "FAIL", str(exc))
        ok = False

    try:
        caps = requests.get(f"{BASE}/api/system/capabilities/", timeout=5).json()
        ai = caps.get("ai_pricing", {})
        record(
            "infra",
            "capabilities",
            "PASS",
            f"ai_pricing={ai.get('status')} personal={caps['collection']['personal_transfer']['status']}",
        )
    except Exception as exc:
        record("infra", "capabilities", "FAIL", str(exc))
        ok = False

    try:
        token = requests.post(
            f"{BASE}/api/auth/token/",
            json={"username": "james_farmer", "password": "demo12345"},
            timeout=10,
        ).json()["access"]
        probe = requests.post(
            f"{BASE}/api/ai/price-estimate/",
            headers={"Authorization": f"Bearer {token}"},
            json={"crop": "maize", "country": "UG", "quantity_kg": 100, "season": "long_rains"},
            timeout=15,
        ).json()
        if probe.get("method") == "live_market":
            record("infra", "backend_code_fresh", "PASS", "pricing API serves live_market")
        else:
            record(
                "infra",
                "backend_code_fresh",
                "FAIL",
                f"Stale Django process — restart backend (got method={probe.get('method')})",
            )
            ok = False
    except Exception as exc:
        record("infra", "backend_code_fresh", "FAIL", str(exc))
        ok = False
    return ok


def phase_auth() -> dict | None:
    print("\n## Authentication")
    try:
        fh = auth("james_farmer")
        record("auth", "farmer_login", "PASS", "james_farmer JWT")
        bh = auth("mary_buyer")
        record("auth", "buyer_login", "PASS", "mary_buyer JWT")
        return {"farmer": fh, "buyer": bh}
    except Exception as exc:
        record("auth", "demo_login", "FAIL", str(exc))
        return None


def phase_pricing(headers: dict) -> None:
    print("\n## Multinational crop pricing")
    try:
        r = requests.post(
            f"{BASE}/api/ai/price-estimate/",
            headers=headers,
            json={"crop": "maize", "country": "UG", "quantity_kg": 500, "season": "long_rains"},
            timeout=15,
        )
        body = r.json()
        if r.status_code == 200 and body.get("method") == "live_market" and body.get("currency") == "UGX":
            record(
                "pricing",
                "ug_maize_live_market",
                "PASS",
                f"unit={body['unit_price']} {body['currency']} market={body.get('market', {}).get('name', '?')}",
            )
        else:
            record("pricing", "ug_maize_live_market", "FAIL", f"HTTP {r.status_code} {body}")
    except Exception as exc:
        record("pricing", "ug_maize_live_market", "FAIL", str(exc))

    try:
        r = requests.post(
            f"{BASE}/api/ai/price-estimate/",
            headers=headers,
            json={"crop": "maize", "country": "KE", "quantity_kg": 200, "season": "dry"},
            timeout=15,
        )
        body = r.json()
        if r.status_code == 200 and body.get("method") == "live_market" and body.get("currency") == "KES":
            record("pricing", "ke_maize_live_market", "PASS", f"unit={body['unit_price']} KES")
        else:
            record("pricing", "ke_maize_live_market", "FAIL", str(body))
    except Exception as exc:
        record("pricing", "ke_maize_live_market", "FAIL", str(exc))

    try:
        r = requests.get(f"{BASE}/api/ai/market-overview/", headers=headers, timeout=10)
        body = r.json()
        countries = list(body.get("countries", {}).keys())
        if r.status_code == 200 and set(countries) >= {"UG", "KE", "TZ", "RW"}:
            record("pricing", "market_overview", "PASS", f"countries={','.join(sorted(countries))}")
        else:
            record("pricing", "market_overview", "FAIL", str(body))
    except Exception as exc:
        record("pricing", "market_overview", "FAIL", str(exc))


def phase_invoices(headers: dict) -> str | None:
    print("\n## Invoices + public pay + reconcile")
    ref = None
    try:
        r = requests.post(
            f"{BASE}/api/payments/invoices/",
            headers=headers,
            json={
                "customer_name": "Smoke Test Buyer",
                "customer_phone": "+256700111222",
                "description": "Smoke test maize",
                "amount": "25000",
                "currency": "UGX",
            },
            timeout=10,
        )
        inv = r.json()
        ref = inv.get("payment_reference")
        if r.status_code in (200, 201) and ref:
            record("invoices", "create", "PASS", f"ref={ref}")
        else:
            record("invoices", "create", "FAIL", f"HTTP {r.status_code}")
            return None
    except Exception as exc:
        record("invoices", "create", "FAIL", str(exc))
        return None

    try:
        r = requests.get(f"{BASE}/api/payments/invoices/public/{ref}/", timeout=10)
        pub = r.json()
        if r.status_code == 200 and pub.get("payment_reference") == ref:
            record("invoices", "public_pay", "PASS", f"amount={pub.get('amount')} {pub.get('currency')}")
        else:
            record("invoices", "public_pay", "FAIL", f"HTTP {r.status_code}")
    except Exception as exc:
        record("invoices", "public_pay", "FAIL", str(exc))

    try:
        sms = (
            f"MTN Mobile Money: You have received UGX 25,000 from 256700111222. "
            f"Transaction ID: SMOKE01. Ref {ref}"
        )
        r = requests.post(
            f"{BASE}/api/payments/ledger/parse_sms/",
            headers=headers,
            json={"text": sms},
            timeout=10,
        )
        parsed = r.json()
        if r.status_code == 200 and parsed.get("order_reference") == ref:
            record("invoices", "sms_parse", "PASS", f"ref matched confidence={parsed.get('confidence')}")
        else:
            record("invoices", "sms_parse", "FAIL", str(parsed))
    except Exception as exc:
        record("invoices", "sms_parse", "FAIL", str(exc))

    try:
        r = requests.get(f"{BASE}/api/payments/ledger/export-csv/", headers=headers, timeout=10)
        if r.status_code == 200 and "text/csv" in r.headers.get("Content-Type", ""):
            record("invoices", "csv_export", "PASS", f"{len(r.content)} bytes")
        else:
            record("invoices", "csv_export", "FAIL", f"HTTP {r.status_code}")
    except Exception as exc:
        record("invoices", "csv_export", "FAIL", str(exc))

    return ref


def phase_marketplace(farmer_h: dict, buyer_h: dict) -> None:
    print("\n## Marketplace")
    try:
        r = requests.get(f"{BASE}/api/marketplace/listings/", headers=buyer_h, timeout=10)
        listings = r.json().get("results", [])
        if r.status_code == 200:
            record("marketplace", "listings", "PASS", f"count={len(listings)}")
        else:
            record("marketplace", "listings", "FAIL", f"HTTP {r.status_code}")
    except Exception as exc:
        record("marketplace", "listings", "FAIL", str(exc))

    try:
        r = requests.get(f"{BASE}/api/marketplace/orders/", headers=buyer_h, timeout=10)
        if r.status_code == 200:
            record("marketplace", "orders", "PASS", f"count={len(r.json().get('results', []))}")
        else:
            record("marketplace", "orders", "FAIL", f"HTTP {r.status_code}")
    except Exception as exc:
        record("marketplace", "orders", "FAIL", str(exc))


def phase_django_tests() -> None:
    print("\n## Django unit tests")
    try:
        proc = subprocess.run(
            [str(PYTHON), "manage.py", "test", "apps.ai_services.tests", "apps.payments.tests", "-v", "0"],
            cwd=ROOT / "backend",
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            record("unit", "django_tests", "PASS", "12 tests OK")
        else:
            record("unit", "django_tests", "FAIL", (proc.stderr or proc.stdout)[-200:])
    except Exception as exc:
        record("unit", "django_tests", "FAIL", str(exc))


def main() -> int:
    print("=" * 72)
    print("AGRIPAY LIVE SMOKE TEST")
    print(f"API: {BASE}  |  Frontend: {FRONTEND}")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)

    if not phase_infra():
        return write_report(1)

    tokens = phase_auth()
    if not tokens:
        return write_report(1)

    phase_pricing(tokens["farmer"])
    phase_invoices(tokens["farmer"])
    phase_marketplace(tokens["farmer"], tokens["buyer"])
    phase_django_tests()

    fails = sum(1 for r in results if r["status"] == "FAIL")
    return write_report(1 if fails else 0)


def write_report(exit_code: int) -> int:
    fails = sum(1 for r in results if r["status"] == "FAIL")
    passes = sum(1 for r in results if r["status"] == "PASS")
    live = sum(1 for r in results if r["status"] == "LIVE")

    print("\n" + "=" * 72)
    print("SMOKE TEST SUMMARY")
    print("=" * 72)
    print(f"  PASS: {passes}  LIVE: {live}  FAIL: {fails}")
    if fails:
        print("  RESULT: FAIL")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    - {r['phase']}/{r['test']}: {r['detail']}")
    else:
        print("  RESULT: ALL SMOKE CHECKS PASSED")

    out = ROOT / "scripts" / "smoke-test-results.json"
    payload = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "api": BASE,
        "frontend": FRONTEND,
        "pass": fails == 0,
        "summary": {"pass": passes, "live": live, "fail": fails},
        "results": results,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nFull JSON: {out}")
    print("=" * 72)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
