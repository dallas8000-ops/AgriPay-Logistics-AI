#!/bin/sh
set -e
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2
