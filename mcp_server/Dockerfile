# Execution Market MCP Server Dockerfile
# Python 3.11 + FastMCP + FastAPI

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Download geo_match datasets (cached layer — invalidates only if this block changes)
# Dataset details: mcp_server/verification/geo_match/data/README.md
RUN mkdir -p /app/geo_data && cd /app/geo_data \
    && curl -fsSL -o cities500.zip https://download.geonames.org/export/dump/cities500.zip \
    && python -c "import zipfile; zipfile.ZipFile('cities500.zip').extract('cities500.txt', '.')" \
    && rm cities500.zip \
    && curl -fsSL -o us_zips.zip https://simplemaps.com/static/data/us-zips/1.86/basic/simplemaps_uszips_basicv1.86.zip \
    && python -c "import zipfile; zipfile.ZipFile('us_zips.zip').extract('uszips.csv', '.')" \
    && mv uszips.csv us_zips.csv \
    && rm us_zips.zip \
    && ls -lh /app/geo_data/

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r em && useradd -r -g em em

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache /wheels/*

# Patch SDK timeout: Ethereum L1 needs up to 600s+ for TX confirmation.
# The SDK hardcodes httpx.post timeout=120s which is insufficient.
# Change all timeout=120 to timeout=900 in the escrow module.
# 900s gives margin above the Facilitator's 600s TxWatcher timeout.
RUN sed -i 's/timeout=120/timeout=900/g' \
    /usr/local/lib/python3.11/site-packages/uvd_x402_sdk/advanced_escrow.py \
    && python -c "import uvd_x402_sdk.advanced_escrow; print('SDK timeout patched OK')"

# Build-time version metadata (injected by CI)
ARG GIT_SHA=unknown
ARG BUILD_TIMESTAMP=unknown

# Copy application code
COPY . .

# Copy geo_match datasets baked into the builder stage
COPY --from=builder /app/geo_data/cities500.txt /app/verification/geo_match/data/cities500.txt
COPY --from=builder /app/geo_data/us_zips.csv   /app/verification/geo_match/data/us_zips.csv

# Set ownership
RUN chown -R em:em /app

# Switch to non-root user
USER em

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    GIT_SHA=${GIT_SHA} \
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "30"]
# cache-bust 1776016407
