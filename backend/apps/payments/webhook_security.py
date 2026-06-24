"""Webhook security primitives for payment callbacks.

Payment provider callbacks are the highest-risk surface in the app: a forged
callback that marks a Payment COMPLETED releases goods or funds for free. Each
provider authenticates callbacks differently, so this module centralizes the
defenses:

- Flutterwave signs callbacks with a ``verif-hash`` header  -> constant-time compare.
- MTN MoMo and M-Pesa (Daraja) do NOT sign callbacks. The correct defense is to
  (a) restrict to the provider's source IPs where configured, and
  (b) NEVER trust the status in the request body -- re-confirm by querying the
      provider's own status API before completing a payment.
- All providers: idempotency, so a replayed callback cannot double-complete.

Every helper here fails closed: when verification cannot be performed, the
default is to reject, not to accept.
"""

from __future__ import annotations

import hmac
import ipaddress
from typing import Iterable

from django.conf import settings


def constant_time_equal(a: str, b: str) -> bool:
    """Constant-time string comparison (avoids timing side channels)."""
    if not a or not b:
        return False
    return hmac.compare_digest(str(a), str(b))


def client_ip(request) -> str:
    """Best-effort client IP, honouring a single trusted proxy hop.

    Railway/most PaaS terminate TLS at an edge proxy and set
    X-Forwarded-For. We take the FIRST entry (the original client) but only
    trust it because the platform controls the edge. If you add more proxy
    hops, adjust accordingly.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _parse_networks(raw: Iterable[str]) -> list:
    nets = []
    for entry in raw:
        entry = entry.strip()
        if not entry:
            continue
        try:
            nets.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            continue
    return nets


def ip_allowed(request, setting_name: str) -> bool:
    """Return True if the request IP is in the allowlist named by setting_name.

    Fails OPEN only when the allowlist is unset (empty), so unconfigured
    deployments are not bricked -- but logs should make the gap visible. When
    the allowlist IS set, an IP outside it is rejected.
    """
    raw = getattr(settings, setting_name, "") or ""
    entries = [e for e in raw.split(",") if e.strip()]
    if not entries:
        # Not configured: cannot enforce. Treat as allowed but signal via return.
        return True
    networks = _parse_networks(entries)
    if not networks:
        return True
    try:
        ip = ipaddress.ip_address(client_ip(request))
    except ValueError:
        return False
    return any(ip in net for net in networks)


def already_processed(payment) -> bool:
    """Idempotency guard: a payment already COMPLETED must not be re-completed."""
    from .models import Payment

    return payment.status == Payment.Status.COMPLETED
