# P-GALLERY — OPERATIONS & MAINTENANCE RUNBOOK

---

## 1. ROUTINE OPERATIONS & LIFECYCLE COMMANDS

### Stack Management
```bash
# Start all services in background
docker compose up -d

# View live container status
docker compose ps

# View service logs
docker compose logs -f --tail=100 web
docker compose logs -f --tail=100 db

# Restart web application (zero data loss)
docker compose restart web

# Graceful stack shutdown (preserves volumes)
docker compose down
```

> ⚠️ **CRITICAL WARNING**: Never run `docker compose down -v`. The `-v` flag permanently destroys named data volumes.

---

## 2. HEALTH & MONITORING

### Health Endpoint Verification
```bash
curl -f http://localhost:8000/health/
# Expected HTTP 200: {"status":"ok","database":"connected"}
```

### Media Integrity Audit
```bash
docker compose exec web python manage.py audit_media
# Reports total disk usage, DB-referenced media, and orphan candidates
```

### Query Performance Audit
```bash
docker compose exec web python manage.py query_audit
# Verifies 1–6 queries/view performance baseline
```

---

## 3. INCIDENT RESPONSE & TROUBLESHOOTING

### Scenario A: Database Connection Failure (`status: degraded` on `/health/`)
1. Inspect database container logs: `docker compose logs --tail=100 db`
2. Check if PostgreSQL process is healthy: `docker compose exec db pg_isready -U postgres -d pgallery`
3. Restart database container: `docker compose restart db`
4. Verify web reconnects automatically: `curl -f http://localhost:8000/health/`

### Scenario B: 502 Bad Gateway from Nginx / Reverse Proxy
1. Check Gunicorn process status: `docker compose logs --tail=100 web`
2. Verify Gunicorn bind port in `gunicorn.conf.py` matches upstream.
3. Restart web container: `docker compose restart web`

### Scenario C: Upload Request Timeout on 500MB Video
1. Verify Nginx `client_max_body_size 550M;` is configured.
2. Verify Gunicorn timeout in `gunicorn.conf.py` is at least `120s`.
3. Check available disk space on media volume mount.

