# ECHOES OF SMASC '26 — PRODUCTION DEPLOYMENT GUIDE (RENDER + POSTGRESQL)

---

## 1. ARCHITECTURE & DISCOVERY

- **Application Name**: Echoes Of SMASC '26 (`P-Gallery`)
- **Framework**: Django 4.2.25 on Python 3.13
- **WSGI Application**: `config.wsgi:application`
- **ASGI Application**: `config.asgi:application`
- **App Server**: Gunicorn 23.0.0 (Threaded `gthread` concurrency, 120s timeout)
- **Production Database**: PostgreSQL 16+ via `DATABASE_URL` (`psycopg2-binary==2.9.12`, `CONN_MAX_AGE=600`, `sslmode: prefer`)
- **Static Assets**: WhiteNoise 6.12.0 with `core.storage.ProductionManifestStaticFilesStorage`
- **Media Persistence**: 
  - Render persistent disk mounted at `/opt/render/project/src/media`
  - Optional cloud object storage (AWS S3 / Cloudflare R2 / MinIO via `USE_S3=True`)
- **Liveness Monitoring**: `/health/` returning HTTP 200 `{"status": "ok", "database": "connected"}`

---

## 2. PRODUCTION DEPLOYMENT ON RENDER

### Method A: 1-Click Blueprint (`render.yaml`) (Recommended)

1. Push the repository to GitHub:
   ```bash
   git add .
   git commit -m "feat(deploy): production-ready Render and PostgreSQL configuration"
   git push origin main
   ```
2. In the Render Dashboard: Click **New +** $\rightarrow$ **Blueprint**.
3. Connect your GitHub repository `Manojkumar-77/Echoes-Of-SMASC-26`.
4. Render automatically provisions:
   - Python Web Service (`echoes-of-smasc-26`)
   - Managed PostgreSQL Database (`pgallery-db`)
   - 10 GB persistent media disk mounted at `/opt/render/project/src/media`
   - Automated HTTPS SSL certificate.

---

### Method B: Manual Service Creation via Render Dashboard

If configuring manually without Blueprint:

#### 1. Create Managed PostgreSQL Database
- In Render Dashboard: **New +** $\rightarrow$ **PostgreSQL**.
- Name: `pgallery-db`
- Database: `pgallery`
- User: `pgallery_user`
- Plan: Free or Starter
- Copy the **Internal Database URL** once created.

#### 2. Create Web Service
- In Render Dashboard: **New +** $\rightarrow$ **Web Service**.
- Connect your GitHub repository `Manojkumar-77/Echoes-Of-SMASC-26`.
- **Runtime**: `Python`
- **Build Command**:
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput --clear
  ```
- **Start Command**:
  ```bash
  python manage.py migrate --noinput && python manage.py seed_initial_data && gunicorn config.wsgi:application -c gunicorn.conf.py
  ```
- **Health Check Path**: `/health/`

---

## 3. REQUIRED PRODUCTION ENVIRONMENT VARIABLES

Configure these under **Environment** in the Render Dashboard:

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `DJANGO_DEBUG` | `False` | Disables debug mode and activates security headers |
| `DJANGO_SECRET_KEY` | *(50+ char random string)* | Cryptographic signing key |
| `DATABASE_URL` | *(PostgreSQL Internal URL)* | PostgreSQL database connection string |
| `PYTHON_VERSION` | `3.13.1` | Pinned Python runtime |
| `DJANGO_ALLOWED_HOSTS` | `echoes-of-smasc-26.onrender.com` | Allowed host header domain |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://echoes-of-smasc-26.onrender.com` | Allowed CSRF origins for forms/admin |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` | Forces HTTPS redirection |

### Optional Cloud Object Storage (S3 / Cloudflare R2):
| Key | Example Value | Purpose |
| :--- | :--- | :--- |
| `USE_S3` | `True` | Enables S3 storage backend |
| `AWS_STORAGE_BUCKET_NAME` | `pgallery-media` | Storage bucket name |
| `AWS_ACCESS_KEY_ID` | `AKIA...` | Cloud access key |
| `AWS_SECRET_ACCESS_KEY` | `wJalrX...` | Cloud secret key |
| `AWS_S3_ENDPOINT_URL` | `https://<account_id>.r2.cloudflarestorage.com` | S3 custom endpoint |
| `AWS_S3_CUSTOM_DOMAIN` | `media.yourdomain.edu.in` | Optional CDN domain |

---

## 4. CREATING THE DJANGO SUPERUSER

Once deployed:
1. Open Render Dashboard $\rightarrow$ Select `echoes-of-smasc-26` $\rightarrow$ Click **Shell**.
2. Run:
   ```bash
   python manage.py createsuperuser
   ```
3. Enter your administrator username, email, and password.
4. Log into the Unfold CMS Admin at: `https://<your-service>.onrender.com/admin/`.

---

## 5. POST-DEPLOYMENT VERIFICATION CHECKLIST

- [ ] Liveness probe: `curl -f https://<your-service>.onrender.com/health/` returns `200 OK`
- [ ] Homepage `/` loads with dark theme and clear hero typography
- [ ] Static assets `/static/css/global.css` load with HTTP 200
- [ ] Photos Gallery `/gallery/` renders with filter pills and lightbox modal
- [ ] Classmate Yearbook `/yearbook/` renders student profile cards
- [ ] Scrapbook `/scrapbook/` renders memory grids
- [ ] Timeline `/timeline/` renders milestone events
- [ ] Video Archive `/videos/` streams video playback
- [ ] Contact Form `/contact/` submits successfully with CSRF protection
- [ ] Admin `/admin/` allows logging in, uploading photos, and managing records

---

## 6. TROUBLESHOOTING MATRIX

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `DisallowedHost` (HTTP 400) | `ALLOWED_HOSTS` missing domain | `config/settings.py` automatically includes `.onrender.com` wildcard and `RENDER_EXTERNAL_HOSTNAME`. |
| `CSRF verification failed` (HTTP 403) | `CSRF_TRUSTED_ORIGINS` missing scheme | Ensure `DJANGO_CSRF_TRUSTED_ORIGINS` includes `https://` prefix. |
| `no such table: core_heroslide` | App started before database migrations ran | Ensure start command includes `python manage.py migrate --noinput` ahead of `gunicorn`. |
| `GET /static/... 404` | Missing `STATIC_ROOT` compilation | Run `python manage.py collectstatic --noinput --clear` during build step. |
| `GET /media/... 404` | Media URL gated behind `DEBUG=True` | `config/urls.py` uses unconditional `re_path` media serving. |