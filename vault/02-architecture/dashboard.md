---
date: 2026-02-26
tags:
  - domain/architecture
  - component/dashboard
  - tech/react
  - tech/typescript
status: active
aliases:
  - Dashboard
  - Web Portal
  - Frontend
related-files:
  - dashboard/src/
  - dashboard/vite.config.ts
  - dashboard/Dockerfile
---

# Dashboard

**React 18 + TypeScript + Vite + Tailwind CSS** single-page application
at `execution.market`. The primary interface for human workers.

## Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/tasks` | TaskList | Browse available tasks with filters |
| `/tasks/:id` | TaskDetail | View task, apply, submit evidence |
| `/profile` | Profile | Worker profile, wallet linking |
| `/agent/dashboard` | AgentDashboard | Agent task management |
| `/agent/tasks/new` | CreateTask | Publish new tasks |
| `/publisher/dashboard` | PublisherDashboard | H2A human-published tasks |

## Key Features

- **Real-time updates** via [[websocket-server]] (task status, new tasks)
- **Internationalization**: Spanish (primary) and English
- **Supabase Auth**: Anonymous sessions with wallet linking
- **Evidence upload**: S3 presigned URLs via CloudFront CDN
- **Wallet connection**: MetaMask / WalletConnect for payment receipt

## UI Language (Spanish)

- Tasks page: "Buscar Tareas", tabs: "Disponibles", "Cerca de mi", "Mis Solicitudes"
- Agent dashboard: "Panel de Agente", "Crear Tarea", "Entregas por Revisar"
- Publisher dashboard: "Panel de Publicador"

## Build and Deploy

```bash
cd dashboard
npm install
npm run dev          # Dev server at http://localhost:5173
npm run build        # Production build
```

Production: Docker image pushed to ECR `em-production-dashboard`,
served via ECS Fargate behind ALB with HTTPS.

## Related

- [[rest-api]] -- all data fetched from REST endpoints
- [[websocket-server]] -- real-time push notifications
- [[supabase-database]] -- auth sessions, user profiles
