#!/usr/bin/env bash
# AgriPay - Stripe setup using official @stripe/cli
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
PROJECT_NAME="${1:-default}"

echo "AgriPay Stripe Setup (@stripe/cli)"
echo "==================================="

if [ ! -f "$ENV_FILE" ]; then
  cp "$ROOT/backend/.env.example" "$ENV_FILE"
fi

if ! command -v stripe &>/dev/null; then
  echo "Installing @stripe/cli..."
  npm install -g @stripe/cli
fi

stripe --version

if [ "${SKIP_LOGIN:-}" != "1" ]; then
  stripe login --project-name "$PROJECT_NAME"
fi

SECRET_KEY="$(stripe config --list --project-name "$PROJECT_NAME" 2>/dev/null | sed -n "s/.*test_mode_api_key = '\([^']*\)'.*/\1/p")"
PUB_KEY="$(stripe config --list --project-name "$PROJECT_NAME" 2>/dev/null | sed -n "s/.*test_mode_pub_key = '\([^']*\)'.*/\1/p")"

if [[ ! "$SECRET_KEY" =~ ^sk_test_ ]]; then
  echo "Run: stripe login --project-name $PROJECT_NAME"
  exit 1
fi

set_env() {
  local key=$1 val=$2
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

set_env STRIPE_SECRET_KEY "$SECRET_KEY"
set_env STRIPE_PUBLISHABLE_KEY "$PUB_KEY"

echo "Keys saved to backend/.env"

if [ -d "$ROOT/.railway" ]; then
  railway variables set STRIPE_SECRET_KEY="$SECRET_KEY" STRIPE_PUBLISHABLE_KEY="$PUB_KEY"
fi

echo "Webhook: stripe listen --forward-to localhost:8000/api/payments/webhook/stripe/ --project-name $PROJECT_NAME"
