#!/bin/sh
set -e
echo "[entrypoint] collectstatic..."
python manage.py collectstatic --noinput
echo "[entrypoint] schema repair (no-op when django_migrations matches tables)..."
python manage.py repair_accounts_schema
echo "[entrypoint] migrate..."
python manage.py migrate --noinput
echo "[entrypoint] starting gunicorn on port ${PORT:-8000}..."
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 120
