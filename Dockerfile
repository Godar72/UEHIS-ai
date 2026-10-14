# ──────────────────────────────────────────────────────────────
# UEHIS API — Multi-stage Dockerfile
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install system dependencies for GDAL / PostGIS bindings ──
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        gcc \
        g++ \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ─────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
        sqlalchemy \
        geoalchemy2 \
        psycopg2-binary

# ── Application code ────────────────────────────────────────
COPY . .

# ── Health check ───────────────────────────────────────────
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Expose and run ──────────────────────────────────────────
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
