# ECHOES OF SMASC '26 — DEPLOYMENT GUIDE

---

## 1. ARCHITECTURE OVERVIEW

- **Application**: Django 4.2.25 on Python 3.13
- **WSGI Server**: Gunicorn 22.0.0 (`gthread` worker model, 120s timeout, 550MB upload headroom)
- **Static Assets**: WhiteNoise 6.6.0 with `CompressedManifestStaticFilesStorage`
- **Database**: PostgreSQL 16 (production) with SQLite fallback (development)
- **Storage Backend**: Storage-abstracted supporting persistent disk (`FileSystemStorage`) and S3-compatible cloud storage (`S3Boto3Storage`)
- **Health Monitoring**: `/health/` endpoint returning HTTP 200 `{"status": "ok", "database": "connected"}`

---

## 2. PRODUCTION DEPLOYMENT TARGETS

### Target A: Render (Recommended 1-Click Blueprint)

The repository includes a ready [`render.yaml`](file:///c:/P-Gallery/render.yaml) blueprint specification:

1. Push this repository to GitHub:
   ```bash
   git remote add origin https://github.com/<your-username>/echoes-of-smasc-26.git
   git branch -M main
   git push -u origin main
   ```
2. In Render Dashboard: **New** $\rightarrow$ **Blueprint** $\rightarrow$ Select `echoes-of-smasc-26`.
3. Render automatically provisions:
   - Python 3.13 Web Service with Gunicorn & WhiteNoise
   - Managed PostgreSQL Database (`pgallery-db`)
   - 10 GB persistent media disk mounted at `/opt/render/project/src/media`
   - Zero-config auto-SSL HTTPS certificate.

---

### Target B: Docker Compose (Linux VPS / AWS EC2 / DigitalOcean)

The repository includes a production-hardened [`Dockerfile`](file:///c:/P-Gallery/Dockerfile) and [`docker-compose.yml`](file:///c:/P-Gallery/docker-compose.yml):

```bash
# 1. Clone repository to server:
git clone <your-repo-url> echoes-of-smasc-26 && cd echoes-of-smasc-26

# 2. Configure production .env:
cp .env.example .env
nano .env  # Set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DB_PASSWORD

# 3. Build and launch container stack:
docker compose build --no-cache
docker compose up -d

# 4. Apply database migrations & collect static files:
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput

# 5. Create superuser:
docker compose exec web python manage.py createsuperuser

# 6. Verify health check:
curl -f http://localhost:8000/health/
```

---

## 3. PRODUCTION ENVIRONMENT VARIABLES

| Variable | Required | Description | Example |
| :--- | :---: | :--- | :--- |
| `DJANGO_DEBUG` | Yes | Set to `False` in production | `False` |
| `DJANGO_SECRET_KEY` | Yes | Minimum 50-character random key | `django-insecure-...` |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated list of allowed domains/IPs | `yourdomain.edu.in,*.onrender.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Optional | Trusted HTTPS origins for CSRF | `https://yourdomain.edu.in` |
| `DATABASE_URL` | Yes (Prod) | PostgreSQL connection URI | `postgresql://user:pass@host:5432/dbname` |
| `USE_S3` | Optional | Set `True` for AWS S3 / Cloudflare R2 / MinIO | `False` |
| `AWS_STORAGE_BUCKET_NAME` | If S3 | S3 bucket name | `smasc-gallery-media` |
| `AWS_ACCESS_KEY_ID` | If S3 | Cloud storage access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | If S3 | Cloud storage secret key | `wJalrX...` |
| `PORT` | Auto | Injected by PaaS (Render / Heroku) | `8000` |

---

## 4. PERSISTENT MEDIA STORAGE NOTES

- **Local Docker Mode**: Media is mounted to persistent named volume `pgallery_media_volume`.
- **Render Mode**: Media is mounted to persistent disk `media-disk` at `/opt/render/project/src/media`.
- **S3 Mode**: Media is uploaded directly to cloud object storage when `USE_S3=True`.
- **Upload Validation Limits**: Image $\le$ 25 MB, Video $\le$ 500 MB (Individual file validation, zero cumulative storage quotas).

---

## 5. POST-DEPLOYMENT VERIFICATION CHECKLIST

- [ ] `curl -f https://<your-domain>/health/` returns `{"status": "ok", "database": "connected"}`
- [ ] Homepage `/` loads with all hero slides and featured photos
- [ ] Gallery `/gallery/` renders 30 photos with AJAX "Load More" functioning
- [ ] Videos `/videos/` renders video grid with custom player streaming
- [ ] Admin `/admin/` loads with Unfold CMS theme
- [ ] Static assets compile cleanly (`python manage.py collectstatic --noinput`)
- [ ] Automated test suite passes (`python manage.py test core`)

