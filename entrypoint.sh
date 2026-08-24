#!/bin/sh
set -e

echo "=== ECHOES OF SMASC '26 CONTAINER STARTUP ==="

# 1. Wait for database to be reachable if DATABASE_URL is provided
python -c "
import os, time
db_url = os.getenv('DATABASE_URL')
if db_url:
    try:
        import psycopg2
        from urllib.parse import urlparse
        res = urlparse(db_url)
        print('Polling PostgreSQL connection...')
        for i in range(15):
            try:
                conn = psycopg2.connect(
                    dbname=res.path[1:],
                    user=res.username,
                    password=res.password,
                    host=res.hostname,
                    port=res.port or 5432,
                    connect_timeout=3
                )
                conn.close()
                print('PostgreSQL database is ready!')
                break
            except Exception as e:
                print(f'Database warming up (attempt {i+1}/15)...')
                time.sleep(2)
    except Exception as e:
        print(f'Database warmup check note: {e}')
"

# 2. Apply database migrations
echo "[1/2] Applying database migrations..."
python manage.py migrate --noinput

# 3. Verify initial seed data
echo "[2/2] Verifying initial seed data..."
python manage.py seed_initial_data

echo "=== STARTING PRODUCTION GUNICORN SERVER ==="
exec "$@"