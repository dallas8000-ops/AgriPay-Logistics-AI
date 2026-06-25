# Deployment Guide

Platform: **railway**
Framework: **django**
Production URL: https://agripay-api-production.up.railway.app

## Pre-deploy checklist
1. Run readiness — aim for 80+ score
2. Switch to **live** Stripe keys in vault
3. Set DATABASE_URL and apply schema
4. Set production URL in project settings

## Environment variables (Railway web service)
```
DEBUG=False
APP_URL=https://agripay-api-production.up.railway.app
SECRET_KEY=<strong-random>
STRIPE_SECRET_KEY=sk_live_
STRIPE_PUBLISHABLE_KEY=pk_live_
STRIPE_WEBHOOK_SECRET=whsec_
DATABASE_URL=${{Postgres.DATABASE_URL}}
ALLOWED_HOSTS=.railway.app .up.railway.app healthcheck.railway.app
```

Local dev only: `APP_URL=http://127.0.0.1:8000`

## Deploy
```bash
railway up
```

## Post-deploy
1. Verify SSL: https://agripay-api-production.up.railway.app/health/
2. Register production Stripe webhook: `https://agripay-api-production.up.railway.app/webhooks/stripe/`
3. Schedule backups: scripts/backup-db.sh
