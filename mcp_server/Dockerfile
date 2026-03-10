# Execution Market MCP Server Dockerfile
# Python 3.11 + FastMCP + FastAPI

FROM python:3.14-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.14-slim

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

# Copy application code
COPY . .

# Set ownership
RUN chown -R em:em /app

# Switch to non-root user
USER em

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
