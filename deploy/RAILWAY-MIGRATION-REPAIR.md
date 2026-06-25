# Railway migration repair (AgriPay)

## Root cause

Deploy failed with:

```text
django.db.utils.ProgrammingError: relation "accounts_farmerprofile" does not exist
```

while `accounts.0001_initial` is already in `django_migrations`. That means **the migration history and the real schema diverged** — not that `0002`/`0003` are wrong.

Common causes:

1. `0001_initial` was applied with `--fake` or never ran fully
2. Postgres was reset or replaced but `django_migrations` was copied from elsewhere
3. `DATABASE_URL` was pointed at a different Postgres than the one that was migrated

**Do not add repair logic inside migration files.** Migrations should stay linear `AddField` / `CreateModel` operations.

## Fix (one time on Railway)

### Option A — automatic (recommended)

`entrypoint.sh` runs `repair_accounts_schema` before `migrate` on every deploy.
It is a **no-op** when the schema already matches `0001_initial`; it only repairs
when profile tables are missing.

Push the latest code and redeploy — no Console typing required.

### Option B — Railway CLI from your PC

```powershell
cd "C:\Software Projects\AgriPay Logistics AI"
railway link
railway run python manage.py repair_accounts_schema
railway run python manage.py migrate --noinput
```

### Option C — Railway Console

If the Console accepts input:

```bash
python manage.py repair_accounts_schema --dry-run
python manage.py repair_accounts_schema
python manage.py migrate --noinput
```

## If repair command refuses (accounts_user missing)

The database is too far gone for a light repair. Options:

- **No production data to keep:** delete the Postgres volume / create a new Postgres plugin, set `DATABASE_URL`, redeploy (clean `migrate`)
- **Data to keep:** export what you need, then reset Postgres and restore

## Prevent recurrence

- Set `DATABASE_URL=${{Postgres.DATABASE_URL}}` on the **web service** only; Postgres plugin name must match the reference (`Postgres`)
- Never `--fake` initial migrations on Railway unless the schema truly matches
- After changing Postgres plugins, treat it as a **new database** and migrate from scratch
