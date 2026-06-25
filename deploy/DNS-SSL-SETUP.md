# Domain & SSL Setup

Production URL: https://agripay-api-production.up.railway.app
Framework: django

## SSL
TLS terminates at Railway's edge. Set `APP_URL` to the `https://` production URL (not `127.0.0.1`).

## Stripe Webhook (production)
`https://agripay-api-production.up.railway.app/webhooks/stripe/`

## Verification
```bash
curl https://agripay-api-production.up.railway.app/health/
```

Local dev: `http://127.0.0.1:8000/health/`
