# NOW-002: Crear Dockerfile para Dashboard

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: Ninguna
- **Archivos a crear**: `dashboard/Dockerfile`
- **Tiempo estimado**: 15-30 min

## Descripción
Crear un Dockerfile multi-stage para el Dashboard de Chamba (React/Vite) optimizado para producción.

## Contexto Técnico
- **Runtime**: Node 18 (build) + Nginx (serve)
- **Framework**: React + Vite + TailwindCSS
- **Puerto**: 80 (nginx)
- **Build output**: `dist/`

## Código de Referencia

```dockerfile
# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

## Nginx Config Requerido

```nginx
# dashboard/nginx.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing - todas las rutas van a index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}
```

## Criterios de Éxito
- [ ] Dockerfile creado en `dashboard/Dockerfile`
- [ ] nginx.conf creado en `dashboard/nginx.conf`
- [ ] `docker build` exitoso
- [ ] Imagen final < 50MB (nginx + static)
- [ ] SPA routing funciona (refresh en /profile no da 404)
- [ ] Assets cacheados correctamente

## Variables de Build
```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_URL=
```

## Comandos de Verificación
```bash
# Build
docker build -t chamba-dashboard:latest dashboard/

# Run locally
docker run -p 3000:80 chamba-dashboard:latest

# Test
curl http://localhost:3000/
curl http://localhost:3000/profile  # Should return index.html
```
