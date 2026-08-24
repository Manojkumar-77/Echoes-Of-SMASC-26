import multiprocessing
import os

# Gunicorn production server configuration
bind = f"{os.getenv('GUNICORN_HOST', '0.0.0.0')}:{os.getenv('PORT', os.getenv('GUNICORN_PORT', '8000'))}"

# Worker configuration (threaded worker for I/O efficiency)
workers = int(os.getenv("GUNICORN_WORKERS", max(2, min(4, multiprocessing.cpu_count() * 2 + 1))))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
worker_class = "gthread"

# Timeouts & Keep-Alive (generous timeout for large video uploads)
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Request recycling to avoid memory leaks
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# Structured stdout/stderr logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")


def on_starting(server):
    """
    Automatic production safeguard: Runs database migrations and seeding
    before Gunicorn worker processes are spawned, ensuring tables exist even if
    the deployment platform executes Gunicorn directly.
    """
    try:
        import django
        from django.core.management import call_command
        django.setup()
        call_command('migrate', interactive=False)
        call_command('seed_initial_data')
        server.log.info("Startup database migrations and initial seeding verified.")
    except Exception as e:
        server.log.warning(f"Startup migration warning: {e}")


