# ==============================================================================
# P-GALLERY — PRODUCTION DOCKERFILE
# ==============================================================================

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PORT=8000 \
    DJANGO_DEBUG=False \
    DJANGO_SECRET_KEY=docker-build-temporary-secret-key-for-collectstatic-only

# Set working directory
WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip \
    && pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Create application non-root user
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser

# Create persistent storage directories and assign permissions
RUN mkdir -p /app/media /app/staticfiles /app/backups \
    && chown -R appuser:appgroup /app

# Copy application source code
COPY --chown=appuser:appgroup . /app/

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Collect static files during Docker image build
RUN python manage.py collectstatic --noinput --clear

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health/ || exit 1

# Set entrypoint and launch production Gunicorn server
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "config.wsgi:application"]


