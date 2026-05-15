# ── Stage 1: base image ───────────────────────────────────────
FROM python:3.12-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (needed for some pip packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Install Python dependencies ────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project code ──────────────────────────────────────────
COPY . .

# ── Collect static files (needs a dummy SECRET_KEY at build time) ─
RUN DJANGO_SECRET_KEY=build-time-dummy-key-not-used-in-production \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput

# ── Expose port ────────────────────────────────────────────────
EXPOSE 8000

# ── Run migrations then start gunicorn ────────────────────────
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
