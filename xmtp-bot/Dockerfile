# Stage 1: Build
# Use Debian-based image (not Alpine) because @xmtp/agent-sdk requires
# glibc-linked native bindings (libxmtp) that are incompatible with musl.
FROM ubuntu:24.04 AS builder

# Install Node.js 22 on Ubuntu 24.04 (GLIBC 2.39)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts && npm rebuild

COPY tsconfig.json ./
COPY src/ ./src/

RUN npm run build

# Stage 2: Runtime
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates wget tini && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 xmtp && useradd -u 1001 -g xmtp -m xmtp

WORKDIR /app

# Copy built artifacts
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# Create data directory for EFS mount (XMTP SQLite DB)
RUN mkdir -p /data/xmtp && chown -R xmtp:xmtp /data/xmtp

# Set defaults
ENV NODE_ENV=production \
    XMTP_DB_PATH=/data/xmtp/bot.db3 \
    HEALTH_PORT=8090 \
    LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8090/health || exit 1

USER xmtp

EXPOSE 8090

ENTRYPOINT ["tini", "--"]
CMD ["node", "dist/index.js"]
