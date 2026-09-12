# Domain & SSL Setup

Production URL: https://agripay-api-production.up.railway.app
Framework: django

The Railway URL is the verified fallback and stays in the public portfolio until a custom host passes every check below. A GitHub push cannot create or repair DNS records by itself.

## 1. Verify the Railway fallback

From the repository root:

```bash
python scripts/verify-public-deployment.py
```

The root page, `/landing`, `/login`, and `/health/` must all pass. Do not continue with a custom domain while the fallback deployment is unhealthy.

## 2. Add the custom host in Railway

1. Open the AgriPay web service in Railway.
2. Open **Settings -> Networking -> Custom Domain**.
3. Enter the exact host you intend to publish, such as `agripay.example.com`.
4. Copy the DNS target Railway displays. Do not guess or reuse a target from another Railway service.

## 3. Create the registrar DNS record

- For a subdomain, create the CNAME Railway specifies.
- For an apex/root domain, use the registrar's ALIAS/ANAME support or Railway's exact apex instructions.
- Remove conflicting A, AAAA, or CNAME records for the same host.
- Keep proxying disabled until Railway has issued the certificate when using a DNS provider with an optional proxy.

Wait until the hostname resolves to Railway and Railway reports the TLS certificate as active.

## 4. Configure Django and external callbacks

Set these variables on the AgriPay Railway web service using the exact HTTPS custom host:

```text
APP_URL=https://agripay.example.com
ALLOWED_HOSTS=agripay.example.com,.railway.app,.up.railway.app,healthcheck.railway.app
CSRF_TRUSTED_ORIGINS=https://agripay.example.com
CORS_ALLOWED_ORIGINS=https://agripay.example.com
```

Preserve any additional trusted origins required by admin or operational clients. Redeploy after changing variables.

TLS terminates at Railway's edge. `APP_URL` must use `https://`, never `127.0.0.1`.

## Stripe Webhook (production)

Keep the Railway webhook active during cutover. Add and verify the custom-domain webhook before removing any working endpoint:

```text
https://agripay.example.com/webhooks/stripe/
```

## 5. Verify before publishing

```bash
python scripts/verify-public-deployment.py https://agripay.example.com
```

Also confirm login, static assets, API requests, and a test Stripe webhook. Only then replace the Railway URL in the Frontline portfolio.

If any check fails, keep the Railway fallback public and inspect DNS resolution, Railway certificate status, deploy logs, `ALLOWED_HOSTS`, and CSRF/CORS origins.

Local development health remains `http://127.0.0.1:8000/health/`.
