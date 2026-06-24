#!/usr/bin/env python3
"""Create MTN MoMo sandbox API user + key and append to backend/.env."""
from __future__ import annotations

import base64
import os
import re
import sys
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / "backend" / ".env"
SANDBOX = "https://sandbox.momodeveloper.mtn.com"
DEFAULT_CALLBACK_HOST = os.environ.get("MTN_MOMO_CALLBACK_HOST", "127.0.0.1")


def load_env() -> dict[str, str]:
    data = {}
    if not ENV_PATH.exists():
        return data
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip()
    return data


def upsert_env(key: str, value: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    out, found = [], False
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    env = load_env()
    sub_key = env.get("MTN_MOMO_SUBSCRIPTION_KEY") or os.environ.get("MTN_MOMO_SUBSCRIPTION_KEY")
    if not sub_key:
        print("ERROR: MTN_MOMO_SUBSCRIPTION_KEY not set in .env")
        return 1

    if env.get("MTN_MOMO_API_USER") and env.get("MTN_MOMO_API_KEY"):
        print("MTN API user already configured in .env — skipping provision.")
        return 0

    ref = str(uuid.uuid4())
    callback_host = env.get("MTN_MOMO_CALLBACK_HOST") or DEFAULT_CALLBACK_HOST
    headers = {
        "Ocp-Apim-Subscription-Key": sub_key,
        "X-Reference-Id": ref,
        "Content-Type": "application/json",
    }
    body = {"providerCallbackHost": callback_host}

    print(f"Creating sandbox API user (ref={ref}, callback_host={callback_host})...")
    r = requests.post(f"{SANDBOX}/v1_0/apiuser", headers=headers, json=body, timeout=30)
    if r.status_code not in (200, 201):
        print(f"ERROR: apiuser create HTTP {r.status_code}: {r.text}")
        print("Hint: Subscribe to 'Collection' product at https://momodeveloper.mtn.com first.")
        return 1

    print("Generating API key...")
    r2 = requests.post(
        f"{SANDBOX}/v1_0/apiuser/{ref}/apikey",
        headers={"Ocp-Apim-Subscription-Key": sub_key},
        timeout=30,
    )
    if r2.status_code not in (200, 201):
        print(f"ERROR: apikey create HTTP {r2.status_code}: {r2.text}")
        return 1

    api_key = r2.json().get("apiKey")
    if not api_key:
        print(f"ERROR: unexpected response: {r2.text}")
        return 1

    upsert_env("MTN_MOMO_API_USER", ref)
    upsert_env("MTN_MOMO_API_KEY", api_key)
    upsert_env("MTN_MOMO_ENV", "sandbox")
    upsert_env("MTN_MOMO_TARGET_ENV", "sandbox")
    upsert_env("MTN_MOMO_CALLBACK_HOST", callback_host)

    # Verify token
    token_b64 = base64.b64encode(f"{ref}:{api_key}".encode()).decode()
    tr = requests.post(
        f"{SANDBOX}/collection/token/",
        headers={
            "Authorization": f"Basic {token_b64}",
            "Ocp-Apim-Subscription-Key": sub_key,
        },
        timeout=30,
    )
    if tr.status_code == 200 and tr.json().get("access_token"):
        print("SUCCESS: MTN sandbox token obtained — credentials work.")
    else:
        print(f"WARN: credentials saved but token test failed HTTP {tr.status_code}: {tr.text}")

    print(f"Wrote MTN_MOMO_API_USER and MTN_MOMO_API_KEY to {ENV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
