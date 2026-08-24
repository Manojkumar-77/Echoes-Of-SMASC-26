# ==============================================================================
# P-GALLERY — PRODUCTION DOCKERFILE
# ==============================================================================

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_DEBUG=False

# Set working directory
WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create application non-root user
RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --gid 1001 --no-create-home appuser

# Create persistent storage directories and assign permissions
RUN mkdir -p /app/media /app/staticfiles /app/backups \
    && chown -R appuser:appgroup /app

# Copy application source code
COPY --chown=appuser:appgroup . /app/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health/ || exit 1

# Launch production Gunicorn server
CMD ["gunicorn", "-c", "gunicorn.conf.py", "config.wsgi:application"]

