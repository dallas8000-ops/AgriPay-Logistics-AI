# AgriPay Logistics AI

A mobile-first East Africa agribusiness platform connecting farmers, market vendors, produce buyers, and truck drivers — with mobile money payments, delivery tracking, proof-of-delivery, and AI-powered pricing.

**Supported countries:** Uganda, Kenya, Tanzania, Rwanda

## Features

| Module | Description |
|--------|-------------|
| Onboarding | Role-based profiles for farmer, vendor, buyer, driver |
| Marketplace | Browse and list produce with local currency |
| Payments | MTN MoMo, Airtel Money, M-Pesa (live when API creds set; simulated otherwise) + Stripe |
| Logistics | Driver assignment, live tracking, proof-of-delivery |
| AI Services | Price estimates, route summaries, buyer reliability scores |
| Disputes | Raise and resolve order disputes |
| Admin | Platform stats dashboard |
| Offline | Queue actions locally, sync when back online |
| Notifications | In-app + SMS/WhatsApp-style alerts (event-driven) |
| PWA | Installable app with offline caching & action queue |
| Admin | Full platform dashboard with stats, orders, disputes |

## Tech Stack

- **Backend:** Django 5 + Django REST Framework, JWT auth, RBAC
- **Frontend:** React 19 + TypeScript, Vite, mobile-first UI, dark/light mode
- **Database:** PostgreSQL (SQLite for local dev)
- **Payments:** Stripe (live) + mobile money provider APIs when configured

### Mobile money integration modes

| Provider | Live when configured | Sandbox signup |
|----------|---------------------|----------------|
| MTN MoMo | `MTN_MOMO_API_USER`, `MTN_MOMO_API_KEY`, `MTN_MOMO_SUBSCRIPTION_KEY` | [MTN MoMo Developer](https://momodeveloper.mtn.com/) |
| Airtel Money | `AIRTEL_MONEY_CLIENT_ID`, `AIRTEL_MONEY_CLIENT_SECRET` | [Airtel Open API](https://developers.airtel.africa/) |
| M-Pesa | `MPESA_*` vars + `MPESA_CALLBACK_URL` | [Safaricom Daraja](https://developer.safaricom.co.ke/) |

Without credentials, checkout runs in **simulated** mode (clearly labeled in the UI — no fake USSD messages). With credentials, the backend calls real sandbox APIs (`requestToPay`, Airtel collect, M-Pesa STK push) and polls provider status / handles webhooks at `/api/payments/webhook/mtn/` and `/api/payments/webhook/mpesa/`.
- **DevOps:** Docker, GitHub Actions, deploy-ready for Railway

## Quick Start

### Local development

**Recommended** — verifies the correct app before opening (avoids wrong project on shared ports):

```powershell
.\scripts\dev.ps1
```

**Manual start:**

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # USE_SQLITE=True by default
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Before opening the browser, confirm AgriPay is actually running:

```powershell
.\scripts\verify-dev-app.ps1
.\scripts\open-app.ps1
```

Use **http://127.0.0.1:5174** — not `localhost:5173` (another Vite project on this machine may answer there).

### Demo accounts

Primary demo persona is **Uganda** (UGX, MTN MoMo) — sign in as `james_farmer` for invoices and SMS reconcile.

| User | Password | Role |
|------|----------|------|
| admin | admin12345 | Admin |
| james_farmer | demo12345 | Farmer (Mbale, UG) |
| mary_buyer | demo12345 | Buyer (Kampala, UG) |
| peter_driver | demo12345 | Driver |
| grace_vendor | demo12345 | Vendor |

### Docker

```bash
docker compose up --build
```

- API: http://localhost:8000
- App: http://127.0.0.1:5174
- Admin: http://localhost:8000/admin

## Setup (Stripe Projects — official installer)

Stripe Projects is the official CLI installer that automates Railway, Postgres, Stripe API keys, and `.env` sync. Docs: https://docs.stripe.com/projects

**One command** (run from project root):
```powershell
stripe plugin install projects
.\scripts\setup-all.ps1
```

First run opens the browser once for Stripe Projects auth. After that, it will:
1. `stripe projects init --yes --accept-tos` — initialize `.projects/` in this repo
2. `stripe projects link railway --accept-tos --yes` — connect your Railway account
3. `stripe projects add railway/postgres` + `railway/hosting` — provision infra (non-interactive)
4. `stripe projects env --refresh` + `env --pull` — sync all credentials into `.env` automatically

**If Railway commands fail in the agent/CI terminal**, run these manually in your own PowerShell:

```powershell
stripe projects link railway --accept-tos --yes
stripe projects add railway/postgres --yes --accept-tos --non-interactive --name agripay-db

# Hosting needs --config (not --resource-info). On Windows, use the helper script:
node scripts/stripe-add-config.mjs railway/hosting '{"repo":"owner/repo"}' --name railway-hosting
# Or deploy a Docker image:
node scripts/stripe-add-config.mjs railway/hosting '{"image":"nginx:latest"}' --name railway-hosting

stripe projects env --refresh
stripe projects env --pull
.\scripts\setup-all.ps1 -SkipInit
```

Postgres credentials arrive as `AGRIPAY_DB_VARIABLES` in `.env`; `setup-all.ps1` extracts `DATABASE_URL` into `backend/.env`.

**Webhook listener** (separate terminal):
```powershell
stripe listen --forward-to localhost:8000/api/payments/webhook/stripe/
```

**Check status anytime:**
```powershell
stripe projects status
stripe projects env
```

Legacy manual scripts (`setup-railway.ps1`, `setup-stripe.ps1`) now delegate to `setup-all.ps1`.

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/register/` | Register user |
| `POST /api/auth/token/` | JWT login |
| `GET /api/marketplace/listings/` | Browse produce |
| `POST /api/marketplace/orders/` | Place order |
| `POST /api/payments/` | Initiate payment |
| `POST /api/ai/price-estimate/` | AI crop pricing |
| `GET /api/logistics/` | Delivery tracking |
| `GET /api/disputes/` | Dispute center |

## Deploy (Railway)

**Railway:** Connect repo — `railway.toml` configures Docker build and `/health/` check.


Set these env vars in production:
- `DATABASE_URL` (auto-provided by the Railway Postgres plugin)
- `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
- `DEBUG=false`
- Stripe keys (run `scripts/setup-stripe.ps1` locally first)

Health check: `GET /health/`

## License

MIT
