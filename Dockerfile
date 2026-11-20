# ═══════════════════════════════════════════════════════════════════════════════
# Multi-stage Dockerfile — Single container: React build + FastAPI
# Stage 1: Build React frontend
# Stage 2: Python runtime serving API + static frontend
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: React Builder ─────────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
# In production, API calls go to the same origin (no VITE_API_URL needed — Vite default is /api/v1)
RUN npm run build


# ── Stage 2: Python + FastAPI Runtime ──────────────────────────────────────────
FROM python:3.11-slim

# System deps for psycopg2, Pillow / reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libfreetype6-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy React build output from Stage 1 into expected relative path
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Uploads directory (will be populated at runtime)
RUN mkdir -p uploads

# Expose the port Railway / Render will bind to
EXPOSE 8000

# Start FastAPI (single process — Railway/Render manage scaling via PORT env)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
