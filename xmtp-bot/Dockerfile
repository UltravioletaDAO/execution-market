# Stage 1: Build
FROM node:20-alpine AS builder

RUN apk add --no-cache python3 make g++ linux-headers

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts && npm rebuild

COPY tsconfig.json ./
COPY src/ ./src/

RUN npm run build

# Stage 2: Runtime
FROM node:20-alpine

RUN apk add --no-cache wget tini

# Create non-root user
RUN addgroup -g 1001 xmtp && adduser -D -u 1001 -G xmtp xmtp

WORKDIR /app

# Copy built artifacts
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# Create data directory for EFS mount (XMTP SQLite DB)
RUN mkdir -p /data/xmtp && chown -R xmtp:xmtp /data/xmtp

# Set defaults
ENV NODE_ENV=production \
    XMTP_DB_PATH=/data/xmtp \
    HEALTH_PORT=8090 \
    LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8090/health || exit 1

USER xmtp

EXPOSE 8090

ENTRYPOINT ["tini", "--"]
CMD ["node", "dist/index.js"]
