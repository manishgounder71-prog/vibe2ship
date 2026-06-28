# FutureShield AI - Dockerfile for Google Cloud Run
# Multi-stage build for minimal production image

# ---- Build Stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (including PostgreSQL client lib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Production Stage ----
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies for PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY main.py .
COPY database.py .
COPY rag.py .
COPY .env.example .env
COPY templates/ templates/
COPY shared/ shared/
COPY sw.js .
COPY manifest.json .
COPY icon.svg .
COPY routes/ routes/

# database.db is created automatically by init_db() on first startup (SQLite mode)

# Ensure scripts in .local are in PATH
ENV PATH=/root/.local/bin:$PATH

# Expose Cloud Run default port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')" || exit 1

# Run with uvicorn on Cloud Run port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
