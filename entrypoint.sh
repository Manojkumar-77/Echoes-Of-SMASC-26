#!/bin/sh
set -e

echo "=== ECHOES OF SMASC '26 CONTAINER STARTUP ==="

# 1. Apply database migrations
echo "[1/2] Applying database migrations..."
python manage.py migrate --noinput

# 2. Verify initial seed data
echo "[2/2] Verifying initial seed data..."
python manage.py seed_initial_data

echo "=== STARTING GUNICORN SERVER ==="
exec "$@"
