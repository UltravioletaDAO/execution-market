# Activity Feed + Dashboard — Extended Feature Phases

> **Author:** Clawd | **Date:** 2026-02-15
> **Status:** Planning → Execution
> **Origin:** Saúl's detailed feature requests (Feb 15 conversation)

---

## Phase A: Quick Fixes (Same Day)
*Polish what's already deployed*

### Tasks
- [ ] **A1. Chain icons in feed cards** — Replace `⛓️ BASE` text badge with actual chain logo from `NETWORKS` config (`/base.png`, `/avalanche.png`, etc.). Use `<img>` with the logo path. Apply everywhere: feed cards, task cards, task detail.
- [ ] **A2. TX links to block explorer** — The `TxHashLink` component already generates explorer URLs via `getExplorerUrl()`. Verify it's rendering clickable links (not just copyable hash) in the TaskFeedCard. Ensure escrow, payment, refund, and reputation TXs all link to the correct explorer (BaseScan, Etherscan, etc.).
- [ ] **A3. Chain icon in task cards** — Each task in the Available Tasks list should show the chain logo next to the bounty/token info.

---

## Phase B: Geo-Location System
*Auto-extract locations + filter by proximity*

### Problem
Agents post tasks with location in free text (`location_hint`). The DB has `location` (lat/lng) and `location_hint` (text) but no structured city/country/region on tasks. Workers need to filter tasks near them.

### Tasks
- [ ] **B1. Task geo-extraction migration (033)** — Add to `tasks` table:
  ```sql
  ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_city TEXT;
  ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_region TEXT;  -- state/province
  ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_country TEXT;
  ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_country_code TEXT; -- ISO 3166-1 alpha-2
  CREATE INDEX idx_tasks_location_city ON tasks(location_city);
  CREATE INDEX idx_tasks_location_country ON tasks(location_country_code);
  CREATE INDEX idx_tasks_location_region ON tasks(location_region);
  ```

- [ ] **B2. Auto-extract location from task text** — Backend function/trigger that:
  1. On task INSERT, parse `location_hint` + `instructions` for city/region/country mentions
  2. If `location` (lat/lng) exists, reverse-geocode to fill city/region/country
  3. If only text, use simple keyword extraction (e.g., "Miami" → city=Miami, region=Florida, country=US)
  4. Store extracted geo in the new columns
  5. Fallback: leave NULL if no location detected (digital tasks don't need location)

- [ ] **B3. Backfill existing tasks** — One-time script to extract locations from all existing tasks' `location_hint` fields.

- [ ] **B4. Geo filter UI in Activity Feed** — Add location filter controls:
  - Dropdown/pills: "🌍 Global" | "🇺🇸 Country" | "📍 Region" | "🏙️ City"
  - Auto-detect user's city from their executor profile (`location_city`)
  - When "City" selected: show tasks in user's city
  - When "Region" selected: show tasks in user's state/region
  - When "Country" selected: show tasks in user's country
  - "Global" shows all (default)

- [ ] **B5. Geo filter in Available Tasks** — Same location pills/dropdown on the worker's task list page (`/tasks`).

- [ ] **B6. Nearby tasks badge** — On worker dashboard, show count of tasks near their configured location.

---

## Phase C: Social Connections & Friends Feed
*See what your network is doing*

### Tasks
- [ ] **C1. Connections table (migration 034)**:
  ```sql
  CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_wallet TEXT NOT NULL,
    following_wallet TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(follower_wallet, following_wallet)
  );
  CREATE INDEX idx_connections_follower ON connections(follower_wallet);
  CREATE INDEX idx_connections_following ON connections(following_wallet);
  ```

- [ ] **C2. Follow/unfollow API** — `useConnections` hook:
  - `followUser(wallet)` / `unfollowUser(wallet)`
  - `isFollowing(wallet)` check
  - `getFollowing()` / `getFollowers()` lists

- [ ] **C3. Follow button on profiles** — On `PublicProfile` page, show "Follow" / "Following" button.

- [ ] **C4. "My Network" feed filter** — New filter tab in Activity Feed:
  - "👥 My Network" — shows only activity from people the user follows
  - Queries activity where actor_wallet IN (user's following list)

- [ ] **C5. Connection suggestions** — "People you might know":
  - Workers who completed tasks from the same agents
  - Agents who posted tasks in the same categories/locations

---

## Phase D: Worker Dashboard & Earnings
*Personal stats, earnings tracking, performance metrics*

### Tasks
- [ ] **D1. Enhanced earnings display on profile** — Show on worker's own profile:
  - Total earnings (sum of completed task bounties)
  - Average earnings per task
  - Earnings this week / month / all time
  - Earnings chart over time (line/bar)
  - Best-paying task category
  - Average completion time

- [ ] **D2. Worker stats card** — On the worker dashboard (`/tasks` page), add a collapsible stats section:
  - Tasks completed / accepted / abandoned
  - Average rating received
  - Response time average
  - Completion rate %
  - Active streaks (consecutive completions without dispute)
  - Earnings this week

- [ ] **D3. Agent stats on agent dashboard** — For agents (`/agent/dashboard`):
  - Tasks posted / completed / disputed
  - Average cost per task
  - Total spent
  - Average time to completion
  - Worker satisfaction (avg rating given by workers)
  - Most-used task categories

- [ ] **D4. Earnings in public profile** — On public profiles, show:
  - Tasks completed count
  - Average rating
  - Reputation tier + on-chain score
  - Member since
  - (Earnings are private — only shown on own profile)

---

## Phase E: Data Cleanup
*Remove stale test data, keep only relevant records*

### Tasks
- [ ] **E1. Audit existing data** — Script to analyze:
  - Tasks with no escrow TX (orphaned test data)
  - Tasks with broken/missing evidence
  - Tasks stuck in intermediate states (accepted but never completed, >7 days old)
  - Executors with no activity
  - Feedback documents with no matching task

- [ ] **E2. Cleanup migration (035)** — SQL script that:
  - Soft-deletes (or archives) tasks with status='published' and created_at < 7 days ago with no escrow
  - Marks stale accepted tasks as 'expired' if deadline passed
  - Cleans up orphaned submissions
  - Updates activity_feed to remove entries for cleaned tasks
  - **DOES NOT hard-delete** — marks with `archived_at` timestamp

- [ ] **E3. Generate cleanup script for Saúl** — Interactive script:
  ```bash
  # Shows what would be cleaned, asks for confirmation
  ./scripts/cleanup-stale-data.sh --dry-run
  ./scripts/cleanup-stale-data.sh --execute
  ```

- [ ] **E4. Backfill activity_feed** — Script to populate activity_feed from existing tasks:
  - For each task, insert the appropriate event based on current status
  - This makes the feed show historical data, not just new events

---

## Phase F: Chain Icons & Explorer Links (Quick Win)
*Already have assets — just wire them up*

### Tasks
- [ ] **F1. Network logo helper** — Create `getNetworkLogo(networkKey: string): string` that returns the logo path from `NETWORKS` config. Fallback to generic chain icon.

- [ ] **F2. Update TaskFeedCard chain badge** — Replace text `⛓️ BASE · USDC` with:
  ```
  [Base logo 16x16] Base · USDC
  ```

- [ ] **F3. Update TaskCard** — Show chain logo next to bounty.

- [ ] **F4. Update TaskDetail** — Show chain logo in payment section.

- [ ] **F5. Verify TxHashLink explorer links** — Ensure all TX hashes in feed cards are clickable links to the correct block explorer. Test with real escrow + payment TXs.

---

## Execution Priority

| Phase | Effort | Impact | Do When |
|-------|--------|--------|---------|
| **A: Quick Fixes** | 1-2 hours | 🔥🔥🔥 | **NOW** |
| **F: Chain Icons** | 1-2 hours | 🔥🔥🔥 | **NOW** (merge with A) |
| **E: Data Cleanup** | 2-3 hours | 🔥🔥 | **TODAY** |
| **D: Dashboard/Earnings** | 2-3 days | 🔥🔥🔥 | **This week** |
| **B: Geo-Location** | 3-4 days | 🔥🔥🔥 | **This week** |
| **C: Social/Friends** | 1-2 weeks | 🔥🔥 | **Next week** |

---

## Dependency Graph

```
A (Quick Fixes) ─┐
F (Chain Icons) ──┤
                  ├──→ E (Cleanup) ──→ B (Geo) ──→ C (Social)
                  │                       ↓
                  └──→ D (Dashboard) ─────┘
```

Phase A+F can run in parallel.
E (cleanup) should run before B (geo) to avoid extracting locations from stale data.
D (dashboard) can run in parallel with B.
C (social) depends on B (geo filters) being done first.

---

*"I want to see what tasks my dad, my sister, my aunt are picking up on Execution Market." — Saúl, 2026-02-15*
