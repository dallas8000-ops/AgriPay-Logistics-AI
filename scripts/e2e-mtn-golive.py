#!/usr/bin/env python3
"""
MTN MoMo sandbox GO-LIVE evidence runner.

Unlike e2e-mtn-momo.py (which proves one happy-path payment), this runs the
SAME requestToPay flow against MTN's reserved sandbox test MSISDNs to force
each terminal state — SUCCESSFUL, PENDING/timeout, and FAILED/REJECTED — and
asserts the integration maps each one correctly.

It writes a timestamped evidence log (text + JSON) under scripts/golive-evidence/
that you can attach to your MTN go-live submission.

WHY THIS MATTERS:
  In sandbox, ANY non-reserved number returns SUCCESSFUL. To demonstrate that
  your code handles failure and pending correctly, you must use MTN's specific
  test numbers. Those live behind the login wall at:
      https://momodeveloper.mtn.com/api-documentation/testing/
  Copy them into TEST_NUMBERS below before running.

PREREQUISITES:
  1. Run mtn-provision-sandbox.py first (creates API user/key in .env)
  2. Django running with the MTN credentials loaded (restart after provision)
  3. Demo users james_farmer / mary_buyer seeded (your existing fixtures)

USAGE:
  python e2e-mtn-golive.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
EVIDENCE_DIR = SCRIPTS / "golive-evidence"
API = os.environ.get("BURN_TEST_API", "http://127.0.0.1:8000")

# ---------------------------------------------------------------------------
# RequestToPay sandbox MSISDNs (Documentation > Sandbox Use Cases):
#   RequestToPayPayerFailed    -> 46733123450  -> app: failed
#   RequestToPayPayerRejected  -> 46733123451  -> app: failed (REJECTED)
#   RequestToPayPayerExpired   -> 46733123452  -> app: failed (EXPIRED)
#   RequestToPayPayerOngoing   -> 46733123453  -> app: processing
#   RequestToPayPayerDelayed   -> 46733123454  -> app: processing
# Any other MSISDN in sandbox returns SUCCESSFUL — use 256772123456 for success.
# Override via MTN_TEST_SUCCESS / MTN_TEST_PENDING / MTN_TEST_FAILED env vars.
# ---------------------------------------------------------------------------
TEST_NUMBERS: dict[str, str] = {
    "success": os.environ.get("MTN_TEST_SUCCESS", "256772123456"),
    "pending": os.environ.get("MTN_TEST_PENDING", "46733123453"),  # RequestToPayPayerOngoing
    "failed": os.environ.get("MTN_TEST_FAILED", "46733123450"),    # RequestToPayPayerFailed
}

# Expected terminal payment.status (your app's normalized status) per case.
# sync_provider_status maps MTN SUCCESSFUL->completed, FAILED->failed,
# PENDING->processing (stays processing until it resolves or times out).
EXPECTED_APP_STATUS: dict[str, set[str]] = {
    "success": {"completed"},
    "pending": {"processing"},          # never resolves in the poll window — that's the point
    "failed":  {"failed"},
}

POLL_ATTEMPTS = 12
POLL_INTERVAL_SECONDS = 3


@dataclass
class CaseResult:
    case: str
    msisdn: str
    skipped: bool = False
    skip_reason: str = ""
    initiate_http: int | None = None
    integration_mode: str = ""
    reference: str = ""
    polls: list[dict] = field(default_factory=list)
    final_app_status: str = ""
    final_provider_status: str = ""
    expected: list[str] = field(default_factory=list)
    passed: bool = False
    error: str = ""


# ------------------------------- helpers ----------------------------------- #

def env_has(key: str) -> bool:
    env_path = ROOT / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}=") and len(line.split("=", 1)[1].strip()) > 3:
                return True
    return len(os.environ.get(key, "")) > 3


def auth_header(username: str, password: str = "demo12345") -> dict:
    r = requests.post(f"{API}/api/auth/token/", json={"username": username, "password": password}, timeout=15)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access']}", "Content-Type": "application/json"}


def ensure_listing(buyer_h: dict, farmer_h: dict) -> dict:
    listings = requests.get(f"{API}/api/marketplace/listings/", headers=buyer_h, timeout=15).json()
    items = listings.get("results", listings if isinstance(listings, list) else [])
    if items:
        return items[0]
    created = requests.post(
        f"{API}/api/marketplace/listings/",
        headers=farmer_h,
        json={
            "crop": "Golive Maize", "variety": "Sandbox", "quantity_kg": 500,
            "unit_price": "50", "location": "Kampala", "season": "dry", "country": "UG",
        },
        timeout=15,
    )
    created.raise_for_status()
    return created.json()


def run_case(case: str, msisdn: str, buyer_h: dict, listing: dict) -> CaseResult:
    res = CaseResult(case=case, msisdn=msisdn, expected=sorted(EXPECTED_APP_STATUS[case]))

    if not msisdn:
        res.skipped = True
        res.skip_reason = (
            f"No test number set for '{case}'. Paste MTN's reserved {case.upper()} "
            "MSISDN from momodeveloper.mtn.com/api-documentation/testing/ into TEST_NUMBERS."
        )
        return res

    try:
        order = requests.post(
            f"{API}/api/marketplace/orders/",
            headers=buyer_h,
            json={"listing": listing["id"], "quantity_kg": 2, "delivery_address": f"MTN golive {case}"},
            timeout=15,
        ).json()

        pay = requests.post(
            f"{API}/api/payments/",
            headers=buyer_h,
            json={"order_id": order["id"], "provider": "mtn_momo", "phone_number": msisdn},
            timeout=30,
        )
        res.initiate_http = pay.status_code
        if pay.status_code not in (200, 201):
            res.error = f"initiate failed: {pay.text[:300]}"
            return res

        body = pay.json()
        checkout = body.get("checkout", {})
        payment_id = body.get("payment", {}).get("id")
        res.integration_mode = checkout.get("integration_mode", "")
        res.reference = checkout.get("reference", "")

        if res.integration_mode == "simulated":
            res.error = "Still simulated — MTN credentials not loaded. Restart Django after provisioning."
            return res

        # Poll status to a terminal/expected state.
        for i in range(POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL_SECONDS)
            st = requests.get(f"{API}/api/payments/{payment_id}/status/", headers=buyer_h, timeout=15)
            if st.status_code != 200:
                res.polls.append({"attempt": i + 1, "http": st.status_code, "body": st.text[:160]})
                continue
            data = st.json()
            app_status = data.get("status") or data.get("payment", {}).get("status", "")
            provider_status = data.get("provider_status", "")
            res.polls.append({"attempt": i + 1, "app_status": app_status, "provider_status": provider_status})
            res.final_app_status = app_status
            res.final_provider_status = provider_status
            # Stop early on a resolved terminal state for success/failed.
            if case in ("success", "failed") and app_status in EXPECTED_APP_STATUS[case]:
                break
            if app_status in ("completed", "failed") and case != "pending":
                break

        res.passed = res.final_app_status in EXPECTED_APP_STATUS[case]
    except Exception as exc:
        res.error = f"{type(exc).__name__}: {exc}"
    return res


def write_evidence(results: list[CaseResult]) -> Path:
    EVIDENCE_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = EVIDENCE_DIR / f"mtn-golive-{stamp}.json"
    txt_path = EVIDENCE_DIR / f"mtn-golive-{stamp}.txt"

    json_path.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")

    lines = [
        "MTN MoMo Sandbox — Go-Live Test Evidence",
        f"Generated (UTC): {stamp}",
        f"API base: {API}",
        "Environment: sandbox (X-Target-Environment=sandbox, currency forced to EUR)",
        "=" * 64,
        "",
    ]
    for r in results:
        verdict = "SKIPPED" if r.skipped else ("PASS" if r.passed else "FAIL")
        lines.append(f"[{verdict}] case={r.case}  msisdn={r.msisdn or '(none)'}")
        if r.skipped:
            lines.append(f"    reason: {r.skip_reason}")
        else:
            lines.append(f"    expected app status: {', '.join(r.expected)}")
            lines.append(f"    final app status   : {r.final_app_status or '(none)'}")
            lines.append(f"    final provider stat: {r.final_provider_status or '(none)'}")
            lines.append(f"    requestToPay ref   : {r.reference or '(none)'}")
            lines.append(f"    integration_mode   : {r.integration_mode or '(none)'}")
            if r.error:
                lines.append(f"    error              : {r.error}")
        lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    return txt_path


# -------------------------------- main ------------------------------------- #

def main() -> int:
    print("=" * 64)
    print("MTN MoMo sandbox GO-LIVE evidence runner")
    print("=" * 64)

    for k in ("MTN_MOMO_API_USER", "MTN_MOMO_API_KEY", "MTN_MOMO_SUBSCRIPTION_KEY"):
        if not env_has(k):
            print(f"ERROR: {k} missing. Run mtn-provision-sandbox.py first.")
            return 1

    # Confirm the app sees MTN as live, not simulated.
    try:
        caps = requests.get(f"{API}/api/system/capabilities/", timeout=5).json()
        mode = caps.get("collection", {}).get("merchant_api", {}).get("providers", {}).get("mtn_momo")
        if mode != "operational":
            print(f"ERROR: capabilities show mtn_momo='{mode}', expected 'operational'.")
            print("       Restart Django after provisioning so it picks up .env.")
            return 1
    except Exception as exc:
        print(f"ERROR: could not reach {API}/api/system/capabilities/ — is Django running? ({exc})")
        return 1

    configured = [c for c, n in TEST_NUMBERS.items() if n]
    missing = [c for c, n in TEST_NUMBERS.items() if not n]
    print(f"Cases to run : {', '.join(configured) or '(none)'}")
    if missing:
        print(f"Cases skipped: {', '.join(missing)} (no reserved test number set)")
    print()

    buyer_h = auth_header("mary_buyer")
    farmer_h = auth_header("james_farmer")
    listing = ensure_listing(buyer_h, farmer_h)

    results: list[CaseResult] = []
    for case in ("success", "pending", "failed"):
        msisdn = TEST_NUMBERS[case]
        print(f"--- case: {case} (msisdn={msisdn or 'SKIP'}) ---")
        r = run_case(case, msisdn, buyer_h, listing)
        results.append(r)
        if r.skipped:
            print(f"    SKIPPED: {r.skip_reason}\n")
        elif r.error:
            print(f"    ERROR: {r.error}\n")
        else:
            verdict = "PASS" if r.passed else "FAIL"
            print(f"    {verdict}: final={r.final_app_status} (expected {r.expected})\n")

    evidence = write_evidence(results)

    ran = [r for r in results if not r.skipped]
    passed = [r for r in ran if r.passed]
    print("=" * 64)
    print(f"Ran {len(ran)} case(s): {len(passed)} passed, {len(ran) - len(passed)} failed.")
    if missing:
        print(
            f"NOTE: {len(missing)} case(s) skipped for missing reserved numbers — "
            "a complete go-live submission should include all three states."
        )
    print(f"Evidence written:\n  {evidence}")
    print("=" * 64)

    # Exit non-zero if any RAN case failed (skips don't fail the run).
    return 0 if all(r.passed for r in ran) else 1


if __name__ == "__main__":
    sys.exit(main())
