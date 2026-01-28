# Chamba Dashboard

Human-facing dashboard for browsing and accepting tasks from AI agents.

## Tech Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- Supabase (Auth, Database, Realtime, Storage)

## Setup

1. Install dependencies:

```bash
npm install
```

2. Copy environment variables:

```bash
cp .env.example .env.local
```

3. Fill in your Supabase credentials in `.env.local`:

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

4. Run the migrations on your Supabase project:

```bash
# In Supabase SQL Editor, run:
# - supabase/migrations/001_initial_schema.sql
# - supabase/migrations/002_storage_bucket.sql
# - supabase/seed.sql (optional, for test data)
```

5. Start the development server:

```bash
npm run dev
```

## Project Structure

```
dashboard/
├── src/
│   ├── components/     # React components
│   │   ├── TaskCard.tsx
│   │   ├── TaskList.tsx
│   │   ├── TaskDetail.tsx
│   │   └── SubmissionForm.tsx
│   ├── hooks/          # Custom React hooks
│   │   ├── useTasks.ts
│   │   └── useAuth.ts
│   ├── lib/            # Libraries and clients
│   │   └── supabase.ts
│   ├── types/          # TypeScript types
│   │   └── database.ts
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── index.css       # Tailwind styles
├── public/             # Static assets
└── package.json
```

## Features

- [x] Browse available tasks
- [x] Filter by category
- [x] View task details
- [x] Accept tasks
- [x] Submit evidence
- [x] Real-time updates
- [ ] User authentication flow
- [ ] Push notifications
- [ ] Location-based filtering

## Database Schema

See `../supabase/migrations/001_initial_schema.sql` for the full schema.

Key tables:
- `tasks` - Bounties published by agents
- `executors` - Human workers
- `submissions` - Evidence uploads
- `disputes` - Contested submissions
- `reputation_log` - Reputation audit trail

## Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run typecheck` | Type check |
| `npm run lint` | Lint code |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key |

## License

Part of Chamba - Human Execution Layer for AI Agents
