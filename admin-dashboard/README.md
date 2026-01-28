# Chamba Admin Dashboard

Internal dashboard for platform configuration, monitoring, and management.

## Features

### Analytics Dashboard
- Real-time platform statistics
- Tasks over time (Area chart)
- Tasks by status (Pie chart)
- Volume over time (Bar chart)
- Platform health metrics
- Top agents and workers leaderboards

### Tasks Manager
- List all tasks with pagination
- Filter by status
- Search in title/description
- Task detail modal with full info
- Edit task details (title, description, bounty, deadline)
- Cancel tasks with reason (triggers escrow refund)

### Payments & Transactions
- Transaction history with period filters
- Payment volume stats
- Fees collected
- Active escrow tracking
- Transaction status and type indicators
- Direct links to BaseScan for tx hashes

### Users Management
- List and manage agents (task creators)
- List and manage workers (task executors)
- View user stats (tasks, spend/earnings, reputation)
- Suspend/activate users

### Settings
- Platform fees configuration
- Bounty limits
- Timeout settings
- Feature flags
- Payment network configuration
- All changes logged to audit trail

### Audit Log
- Complete history of configuration changes
- Filter by config category
- Shows old value → new value diff
- Reason for change
- Who made the change

## Quick Start

```bash
cd ideas/chamba/admin-dashboard

# Install dependencies
npm install

# Run development server
npm run dev
```

Open http://localhost:5174

## Environment Variables

Create a `.env.local` file:

```env
# Production
VITE_API_URL=https://api.chamba.ultravioletadao.xyz

# Local development
VITE_API_URL=http://localhost:8000
```

## Build for Production

```bash
npm run build
```

Output will be in `dist/` directory.

## Authentication

The dashboard uses admin key authentication. Set the `CHAMBA_ADMIN_KEY` environment variable on the backend to enable admin access.

```bash
# On the MCP server
export CHAMBA_ADMIN_KEY=your-secure-admin-key
```

## API Endpoints

The dashboard uses the following admin API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/verify` | GET | Verify admin key |
| `/api/v1/admin/stats` | GET | Platform statistics |
| `/api/v1/admin/analytics` | GET | Detailed analytics with time series |
| `/api/v1/admin/config` | GET | All config values |
| `/api/v1/admin/config/{key}` | GET/PUT | Get/update config |
| `/api/v1/admin/config/audit` | GET | Config audit log |
| `/api/v1/admin/tasks` | GET | List tasks |
| `/api/v1/admin/tasks/{id}` | GET/PUT | Get/update task |
| `/api/v1/admin/tasks/{id}/cancel` | POST | Cancel task |
| `/api/v1/admin/payments` | GET | List payments |
| `/api/v1/admin/payments/stats` | GET | Payment statistics |
| `/api/v1/admin/users/agents` | GET | List agents |
| `/api/v1/admin/users/workers` | GET | List workers |
| `/api/v1/admin/users/{id}/status` | PUT | Update user status |

## Tech Stack

- React 18
- TypeScript
- Vite
- TailwindCSS
- TanStack Query (React Query)
- React Router
- Recharts (for visualizations)

## Project Structure

```
admin-dashboard/
├── src/
│   ├── components/
│   │   └── TaskDetailModal.tsx
│   ├── pages/
│   │   ├── Analytics.tsx
│   │   ├── AuditLog.tsx
│   │   ├── Payments.tsx
│   │   ├── Settings.tsx
│   │   ├── Tasks.tsx
│   │   └── Users.tsx
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Deployment

Deploy to admin.chamba.ultravioletadao.xyz via:
- CloudFront + S3 (same infrastructure as main dashboard)
- Or any static hosting (Vercel, Netlify, etc.)

## Security Notes

- Admin key should be treated as a secret
- Never expose admin key in client-side code or URLs
- Use HTTPS in production
- Consider implementing proper admin user authentication with roles
