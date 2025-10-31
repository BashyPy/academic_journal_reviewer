# Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies and create user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1000 app

WORKDIR /app

# Copy requirements and wheels, then install
COPY --from=builder /build/requirements.txt .
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --find-links /wheels -r requirements.txt \
    && rm -rf /wheels requirements.txt

# Copy application code
COPY --chown=app:app app/ ./app/
COPY --chown=app:app .env.example .env

# Create logs directory with proper permissions
RUN mkdir -p logs && chown -R app:app logs

# Switch to non-root user
USER app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]