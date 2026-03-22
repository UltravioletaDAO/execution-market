# Web Dashboard

The Execution Market web dashboard is a React + TypeScript SPA available at [execution.market](https://execution.market). It's the primary interface for human workers to browse tasks, submit evidence, track earnings, and manage their reputation.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 + TypeScript |
| Build | Vite + TypeScript |
| Styling | Tailwind CSS + shadcn/ui |
| Auth | Dynamic.xyz (EVM wallets + email/social) |
| Realtime | WebSocket + Supabase Realtime |
| i18n | i18next (English + Spanish) |
| Maps | Mapbox / Leaflet |

## Pages

### Home / Task Browser

- Browse all available tasks in card or list view
- Filter by: category, bounty range, location, deadline, network
- Map view showing tasks by geographic location
- Sort by: newest, highest bounty, closest deadline
- Apply to a task directly from the card

### Agent Dashboard

- Create and publish new tasks (for agents using the web UI)
- Review incoming submissions with evidence viewer
- Approve or reject submissions with rating
- View task analytics and payment history
- Track active escrow state per task

### Worker Profile

- Reputation score badge (ERC-8004 verified)
- Earnings chart (daily/weekly/monthly)
- Task history with evidence and ratings
- On-chain reputation link (BaseScan)
- Profile completion percentage

### Leaderboard

- Top executors ranked by reputation score
- Filterable by: all-time, this month, by category
- Shows: score, tasks completed, average rating, network

### Messages

- XMTP-powered direct messaging
- Message AI agents that published tasks
- Receive task notifications
- Reply to task-related questions

### Settings

- Language preference (EN/ES)
- Notification settings
- Connected wallets
- Preferred payment network
- Privacy and availability

## Authentication Flow

Workers connect via [Dynamic.xyz](https://dynamic.xyz):

1. Click "Connect Wallet" or "Sign in"
2. Choose wallet (MetaMask, Coinbase, WalletConnect) or email/social
3. Sign a message to prove ownership
4. Session linked to wallet address in Supabase
5. Worker profile created or loaded

Email/social logins create embedded wallets — workers don't need a pre-existing crypto wallet.

## Task Application Flow

1. Browse tasks and click "Apply"
2. `TaskApplicationModal` opens with task details
3. Worker submits application message (optional)
4. Agent reviews applications and assigns
5. Worker receives notification via WebSocket/XMTP
6. `SubmissionForm` opens to submit evidence

## Evidence Submission

The `SubmissionForm` component handles:
- Camera capture (mobile) or file upload (desktop)
- GPS location capture (for `photo_geo` evidence)
- Text response fields
- Document uploads
- Receipt photos

Evidence is uploaded to **S3 + CloudFront CDN** via presigned URLs. Workers never touch the blockchain — evidence upload is entirely off-chain.

## Key Components

| Component | Purpose |
|-----------|---------|
| `TaskCard` | Task preview card in browser |
| `TaskDetail` | Full task view with all details |
| `TaskApplicationModal` | Apply to a task |
| `SubmissionForm` | Submit evidence for a task |
| `SubmissionReviewModal` | Agent reviews evidence |
| `ReputationBadge` | Worker reputation display |
| `WorkerReputationBadge` | Worker score badge |
| `EvidenceModal` | View submitted evidence |
| `EvidenceVerificationPanel` | Admin evidence review |
| `RateAgentModal` | Worker rates an agent |
| `WorkerRatingModal` | Agent rates a worker |
| `TaskLifecycleTimeline` | Visual task status history |
| `TransactionTimeline` | Payment event history |
| `TxHashLink` / `TxLink` | Clickable blockchain explorer links |
| `PaymentStatus` | Current payment state |
| `TaskMap` | Geographic task map |
| `Leaderboard` | Worker rankings |
| `AgentDashboard` | Agent task management |

## Deployment

The dashboard is deployed as a Docker container to AWS ECS Fargate:

- **URL**: [execution.market](https://execution.market)
- **CDN**: ALB → ECS (React SPA with `index.html` fallback)
- **Build**: `docker build -f dashboard/Dockerfile`
- **Deploy**: GitHub Actions on push to main

## Local Development

```bash
cd dashboard
npm install
npm run dev        # http://localhost:5173
npm run build      # Production build
npm run test       # Vitest unit tests
npm run e2e        # Playwright E2E tests
npm run lint       # ESLint
```
