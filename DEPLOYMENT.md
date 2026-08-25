# ECHOES OF SMASC '26 — PRODUCTION DEPLOYMENT GUIDE (RENDER + NEON POSTGRESQL)

---

## 1. ARCHITECTURE OVERVIEW

```text
Render Web Service (Gunicorn + WhiteNoise)
        │
        │ DATABASE_URL (SSL require)
        ▼
Neon PostgreSQL (Serverless Cloud Database)
```

- **Application Name**: Echoes Of SMASC '26 (`P-Gallery`)
- **Framework**: Django 4.2.25 on Python 3.13
- **WSGI Application**: `config.wsgi:application`
- **Web Server**: Gunicorn 23.0.0 (Threaded `gthread` concurrency, 120s timeout)
- **Production Database**: Neon PostgreSQL via `DATABASE_URL` (`psycopg2-binary==2.9.12`, `CONN_MAX_AGE=600`, `sslmode=require`)
- **Static Assets**: WhiteNoise 6.12.0 with `core.storage.ProductionManifestStaticFilesStorage`
- **Media Persistence**: Render persistent disk (`/opt/render/project/src/media`) or S3-compatible cloud storage (`USE_S3=True`)
- **Health Monitoring**: `/health/` returning HTTP 200 `{"status": "ok", "database": "connected"}`

---

## 2. STEP-BY-STEP PRODUCTION SETUP

### Step 1: Create a Neon PostgreSQL Database

1. Go to [https://neon.tech](https://neon.tech) and create a free account or log in.
2. Click **Create Project** $\rightarrow$ Name it `echoes-of-smasc-26`.
3. In the **Dashboard** / **Connection Details** pane:
   - Select **Direct connection** (or **Pooled connection**).
   - Select **Connection string** format: `postgres://...` or `postgresql://...`.
   - Copy the complete connection string:
     ```text
     postgresql://<username>:<password>@<ep-xyz-123456>.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```

---

### Step 2: Configure Render Web Service

1. Push your repository to GitHub:
   ```bash
   git push origin main
   ```
2. In the [Render Dashboard](https://dashboard.render.com):
   - Select your Web Service (`echoes-of-smasc-26`) or click **New +** $\rightarrow$ **Web Service**.
   - Connect repository: `Manojkumar-77/Echoes-Of-SMASC-26`.
3. Configure Service **Settings**:
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

### Step 3: Add Environment Variables in Render

In Render Dashboard $\rightarrow$ Select your Web Service $\rightarrow$ **Environment**:

| Key | Example / Recommended Value | Notes |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require` | **Your Neon PostgreSQL Connection String** |
| `DJANGO_DEBUG` | `False` | Disables debug mode |
| `DJANGO_SECRET_KEY` | *(Click "Generate" or enter a 50+ char random string)* | Cryptographic signing key |
| `PYTHON_VERSION` | `3.13.1` | Sets Python runtime |
| `DJANGO_ALLOWED_HOSTS` | `echoes-of-smasc-26.onrender.com` | Allowed host header domain |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://echoes-of-smasc-26.onrender.com` | Trusted CSRF origins for forms/admin |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` | Forces HTTPS redirection |

---

### Step 4: Deploy and Verify Migrations

1. Click **Manual Deploy** $\rightarrow$ **Clear build cache & deploy**.
2. Render will build the container, execute `collectstatic`, and upon startup run:
   - Connection check against Neon PostgreSQL
   - `python manage.py migrate --noinput`
   - `python manage.py seed_initial_data`
   - Launch Gunicorn server.

---

### Step 5: Create the Django Superuser

1. In Render Dashboard $\rightarrow$ Select `echoes-of-smasc-26` $\rightarrow$ Click **Shell**.
2. Run:
   ```bash
   python manage.py createsuperuser
   ```
3. Enter your administrator username, email, and password.
4. Log into the Unfold Admin panel at: `https://echoes-of-smasc-26.onrender.com/admin/`.

---

## 3. VERIFICATION CHECKLIST

- [ ] Liveness probe: `curl -f https://<your-service>.onrender.com/health/` returns `200 OK`
- [ ] Homepage `/` loads with all hero slides and featured photos
- [ ] Photos Gallery `/gallery/` renders with filter pills and lightbox modal
- [ ] Classmate Yearbook `/yearbook/` renders student profile cards
- [ ] Timeline `/timeline/` renders milestone events
- [ ] Video Archive `/videos/` streams video playback
- [ ] Admin `/admin/` allows logging in, uploading photos, and managing records
- [ ] Database records persist on Neon across redeployments

---

## 4. TROUBLESHOOTING

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `CRITICAL DATABASE CONFIGURATION ERROR` | `DATABASE_URL` missing in Render | Paste your Neon PostgreSQL connection string in Render Dashboard -> Environment -> `DATABASE_URL`. |
| `OperationalError: SSL error` | Missing SSL query param | Ensure your Neon URL ends with `?sslmode=require`. |
| `DisallowedHost` (HTTP 400) | `ALLOWED_HOSTS` missing domain | `config/settings.py` auto-includes `.onrender.com` and `RENDER_EXTERNAL_HOSTNAME`. |
| `CSRF verification failed` (HTTP 403) | `CSRF_TRUSTED_ORIGINS` missing scheme | Ensure `DJANGO_CSRF_TRUSTED_ORIGINS` includes `https://` prefix. |