#!/usr/bin/env python3
"""Verify that an AgriPay public host serves the expected app and health routes."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

import requests


REQUIRED_ROUTES = ("/", "/landing", "/login", "/health/")


def verify_deployment(
    base_url: str,
    *,
    get: Callable[..., requests.Response] = requests.get,
) -> list[dict[str, object]]:
    base_url = base_url.rstrip("/")
    results = []
    for route in REQUIRED_ROUTES:
        url = f"{base_url}{route}"
        try:
            response = get(url, timeout=15)
            error = ""
            if response.status_code != 200:
                error = f"expected HTTP 200, received {response.status_code}"
            elif route != "/health/" and "AgriPay" not in response.text:
                error = "response does not contain the AgriPay product identity"
            results.append(
                {
                    "route": route,
                    "url": getattr(response, "url", url),
                    "status": response.status_code,
                    "ok": not error,
                    "error": error,
                }
            )
        except requests.RequestException as exc:
            results.append(
                {
                    "route": route,
                    "url": url,
                    "status": None,
                    "ok": False,
                    "error": str(exc),
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "base_url",
        nargs="?",
        default="https://agripay-api-production.up.railway.app",
    )
    args = parser.parse_args()

    results = verify_deployment(args.base_url)
    for result in results:
        state = "PASS" if result["ok"] else "FAIL"
        detail = result["error"] or f"HTTP {result['status']}"
        print(f"[{state}] {result['route']} - {detail} - {result['url']}")
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())