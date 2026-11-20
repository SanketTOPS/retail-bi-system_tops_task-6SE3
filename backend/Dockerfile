# ==============================================================================
# Dockerfile — FastAPI Production Container
# ==============================================================================
FROM python:3.11-slim as base

# 1. Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# 2. Install essential system dependencies (for psycopg2, openpyxl, reportlab, matplotlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copy backend application source code
COPY . /app/

# 5. Create storage directories for uploads and PDF report compilation
RUN mkdir -p /app/uploads/datasets /app/uploads/pdfs && \
    chmod -R 777 /app/uploads

# 6. Expose default port (Render/Railway sets PORT dynamically)
EXPOSE 8000

# 7. Healthcheck instruction
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# 8. Container Startup Command
# Uses shell form to evaluate the dynamic $PORT environment variable assigned by Cloud PaaS (Render, Railway, Fly.io)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
