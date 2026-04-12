# Execution Market Dashboard Dockerfile
# Node 20 + Vite + React

# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files (lock file first for deterministic installs)
COPY package.json package-lock.json ./

# Install dependencies deterministically
# --legacy-peer-deps: required because several dashboard deps have conflicting peer ranges
RUN npm ci --legacy-peer-deps

# Copy source
COPY . .

# Vite reads .env.production automatically during build.
# Build args override .env.production only when provided (non-empty).
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_URL
ARG VITE_DYNAMIC_ENVIRONMENT_ID
ARG VITE_EVIDENCE_API_URL
ARG VITE_REQUIRE_AGENT_API_KEY
ARG VITE_GIT_SHA=unknown
ARG VITE_BUILD_TIMESTAMP=unknown

# Increase Node heap for Vite build (default is too low for large bundles)
ENV NODE_OPTIONS="--max_old_space_size=4096"

# Only set ENV if ARG is non-empty, otherwise let Vite read .env.production
RUN if [ -n "$VITE_SUPABASE_URL" ]; then export VITE_SUPABASE_URL="$VITE_SUPABASE_URL"; fi && \
    if [ -n "$VITE_SUPABASE_ANON_KEY" ]; then export VITE_SUPABASE_ANON_KEY="$VITE_SUPABASE_ANON_KEY"; fi && \
    if [ -n "$VITE_API_URL" ]; then export VITE_API_URL="$VITE_API_URL"; fi && \
    if [ -n "$VITE_DYNAMIC_ENVIRONMENT_ID" ]; then export VITE_DYNAMIC_ENVIRONMENT_ID="$VITE_DYNAMIC_ENVIRONMENT_ID"; fi && \
    if [ -n "$VITE_EVIDENCE_API_URL" ]; then export VITE_EVIDENCE_API_URL="$VITE_EVIDENCE_API_URL"; fi && \
    if [ -n "$VITE_REQUIRE_AGENT_API_KEY" ]; then export VITE_REQUIRE_AGENT_API_KEY="$VITE_REQUIRE_AGENT_API_KEY"; fi && \
    export VITE_GIT_SHA="$VITE_GIT_SHA" && \
    export VITE_BUILD_TIMESTAMP="$VITE_BUILD_TIMESTAMP" && \
    npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
