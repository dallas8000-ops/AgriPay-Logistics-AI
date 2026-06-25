# Domain & SSL Setup

Production URL: http://127.0.0.1:8000
Domain: 127.0.0.1
Framework: django

## SSL
SSL/TLS is automatic on Vercel, Railway, and Fly.io custom domains.

## Stripe Webhook (production)
Update webhook URL to: `http://127.0.0.1:8000/webhooks/stripe/`

## Verification
```bash
curl http://127.0.0.1:8000/health/
```
Run readiness from Stripe Installer after deploy.
