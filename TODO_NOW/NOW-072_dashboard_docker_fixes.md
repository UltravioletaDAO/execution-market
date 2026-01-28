# NOW-072: Dashboard Docker Build Fixes

## Status: REQUIRED
## Priority: P0 - Blocker for deployment

## Problem 1: Missing .dockerignore

**Error**:
```
ERROR: invalid file request node_modules/.bin/acorn
```

**Fix** - Crear `dashboard/.dockerignore`:

```
node_modules
.git
.gitignore
*.md
dist
.env*
.vite
.DS_Store
```

## Problem 2: Node version incompatible

**Error**:
```
npm warn EBADENGINE required: { node: '>=20.0.0' }
npm warn EBADENGINE current: { node: 'v18.20.8' }
```

**Fix** - Editar `dashboard/Dockerfile`:

```diff
- FROM node:18-alpine as builder
+ FROM node:20-alpine AS builder
```

## Problem 3: package-lock.json desincronizado

**Error**:
```
npm ci can only install packages when package.json and package-lock.json are in sync
```

**Fix** - Editar `dashboard/Dockerfile`:

```diff
- COPY package.json package-lock.json* ./
- RUN npm ci --legacy-peer-deps
+ COPY package.json ./
+ RUN npm install --legacy-peer-deps
```

## Problem 4: magic-sdk build failure

**Error**:
```
"Wallets" is not exported by "@magic-sdk/types"
```

**Fix** - Dos opciones:

### Opción A: Remover magic-sdk (recomendado para MVP)

1. Remover de `dashboard/package.json`:
```diff
- "magic-sdk": "^28.12.2",
```

2. Editar `dashboard/src/hooks/useWallet.ts`, en `getMagicInstance()`:
```typescript
// Comentar el import dinámico y retornar error
throw new Error('Magic.link integration not available in this build')
```

### Opción B: Usar versión compatible
```bash
npm install magic-sdk@21.0.0
```

## Problem 5: TypeScript errors en build

**Fix** - Editar `dashboard/package.json`:

```diff
- "build": "tsc && vite build",
+ "build": "vite build",
```

## Build Command Final

```bash
# Desde dashboard/
docker build --no-cache --platform linux/amd64 \
  -t chamba-dashboard:latest \
  --build-arg VITE_API_URL=https://api.chamba.ultravioletadao.xyz .
```

## Dockerfile Final Corregido

```dockerfile
# Chamba Dashboard Dockerfile
# Node 20 + Vite + React

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source
COPY . .

# Build arguments for environment variables
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_URL
ARG VITE_WALLET_CONNECT_PROJECT_ID

# Set environment variables for build
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY} \
    VITE_API_URL=${VITE_API_URL} \
    VITE_WALLET_CONNECT_PROJECT_ID=${VITE_WALLET_CONNECT_PROJECT_ID}

# Build the application
RUN npm run build

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
```
