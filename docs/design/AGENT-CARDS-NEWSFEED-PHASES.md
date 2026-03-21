# Agent Cards + News Feed — Phased Implementation Plan

> **Author:** Clawd | **Date:** 2026-02-15
> **Status:** Active Development
> **Origin:** Saúl's directives — universal identity + activity feed

---

## Phase 1: Foundation (CURRENT — In Progress)
*Core components, database, basic display*

### ✅ Completed
- [x] Design doc: `AGENT-CARDS-UNIVERSAL.md`
- [x] Migration 032: `agent_type`, `networks_active` columns, `activity_feed` table with triggers
- [x] `AgentAvatar` — identicon from wallet hash, type indicator dot, 3 sizes
- [x] `AgentMiniCard` — compact card (avatar, name, type, score, tasks count)
- [x] `AgentStandardCard` — expanded card (+ bio, tier badge, member since)
- [x] `useAgentCard` hook — fetch any agent's public profile, module-level cache
- [x] `PublicProfile` page at `/profile/:wallet`
- [x] Integration: `TaskCard` shows poster's MiniCard
- [x] Integration: `TaskDetail` shows poster + worker StandardCards
- [x] `ActivityFeed` component with filter tabs (All/Tasks/Reputation/Workers)
- [x] `ActivityFeedCompact` on landing page (public, no auth)
- [x] `ActivityFeedItem` — simple one-line events
- [x] `TaskFeedCard` — rich match card (Agent ← Task → Worker)
- [x] `useTaskFeedCards` hook — joins tasks + executors + submissions
- [x] `useActivityFeed` hook with Supabase realtime + tasks fallback
- [x] Chain + token badges in card header (multi-chain ready)
- [x] Granular task states (Posted → Assigned → In Progress → Submitted → Completed)
- [x] `/activity` page (authenticated, full feed)
- [x] Activity nav link in AppHeader
- [x] TypeScript: zero errors across all components

### 🔲 Remaining
- [ ] **Bidirectional reputation in TaskFeedCard** — show BOTH:
  - Agent→Worker feedback TX + score given
  - Worker→Agent feedback TX + score given (human rates the agent back)
- [ ] **Feedback scores display** — show the actual rating (⭐⭐⭐⭐⭐) each party gave, not just TX hash
- [ ] **Push to remote + CI green**
- [ ] **Run migration 032 on production Supabase**
- [ ] **Smoke test on staging** — verify cards render, feed populates, profiles load

---

## Phase 2: Bidirectional Reputation Display
*The full reputation lifecycle visible in every feed card*

Each completed task generates TWO reputation events:
1. **Agent → Worker:** "You did good work" (requester rates executor)
2. **Worker → Agent:** "Good to work for" (executor rates requester)

Both must be visible in the feed card.

### Tasks
- [ ] **Extend `TaskFeedCard` data model** — add fields:
  ```typescript
  // Agent's feedback TO the worker
  agent_to_worker_rating: number | null       // 1-5 stars
  agent_to_worker_feedback_tx: string | null  // on-chain TX
  agent_to_worker_comment: string | null      // optional text
  
  // Worker's feedback TO the agent
  worker_to_agent_rating: number | null       // 1-5 stars
  worker_to_agent_feedback_tx: string | null  // on-chain TX
  worker_to_agent_comment: string | null      // optional text
  ```

- [ ] **Update `useTaskFeedCards` hook** — query `feedback_documents` table (migration 029) to get both feedback records per task:
  ```sql
  SELECT * FROM feedback_documents 
  WHERE task_id = :taskId
  -- Returns up to 2 rows: one from agent, one from worker
  ```

- [ ] **Reputation section in TaskFeedCard** — new visual block between stats and transactions:
  ```
  ┌─ Reputation Exchange ──────────────────────┐
  │                                              │
  │  Agent → Worker          Worker → Agent      │
  │  ⭐⭐⭐⭐⭐ (5/5)        ⭐⭐⭐⭐☆ (4/5)     │
  │  "Fast and accurate"    "Clear instructions" │
  │  TX: 0xAb...3D 🔗       TX: 0xFe...1A 🔗    │
  │                                              │
  └──────────────────────────────────────────────┘
  ```

- [ ] **Star rating component** — `StarRating.tsx` reusable component:
  - Filled/empty stars based on score (1-5)
  - Size variants (sm for feed, md for profile)
  - Accessible (aria-label "4 out of 5 stars")

- [ ] **Feedback pending state** — when task is completed but one/both feedbacks haven't been submitted yet:
  ```
  Agent → Worker: ⭐⭐⭐⭐⭐ (5/5) ✅
  Worker → Agent: ⏳ Pending
  ```

- [ ] **Update PublicProfile** — show received feedback from both directions:
  - "Feedback as Requester" (ratings received when posting tasks)
  - "Feedback as Executor" (ratings received when completing tasks)

- [ ] **Tests** — unit tests for feedback display logic, star rendering, pending states

---

## Phase 3: Enhanced Profile Pages
*Full public profiles with history, stats, badges*

### Tasks
- [ ] **Profile stats grid** — computed metrics:
  - Tasks completed (as executor)
  - Tasks posted (as requester)  
  - Average rating received (as executor)
  - Average rating received (as requester)
  - Completion rate (completed / accepted)
  - Average response time (accept → submit)
  - Dispute rate
  - Networks active (which chains they've used)

- [ ] **Task history tab** — paginated list of past tasks:
  - As requester: tasks posted with status, worker, rating given/received
  - As executor: tasks completed with requester, rating given/received
  - Filter by role (requester/executor)

- [ ] **Feedback tab** — all feedback received/given:
  - Sortable by date, rating
  - Shows both directions per task

- [ ] **On-chain verification badge** — show ERC-8004 registration info:
  - Agent ID on-chain
  - Registration TX
  - Network registered on
  - "Verified on-chain ✓" badge

- [ ] **Skills display** — self-declared skills/tags with usage count:
  - e.g., "📸 Photography (12 tasks)" "🌐 Translation (8 tasks)"

- [ ] **Activity heatmap** — GitHub-style contribution graph:
  - Shows when they're most active
  - Builds trust ("this agent is consistently active")

---

## Phase 4: Discovery & Search
*Find agents and workers by skills, reputation, availability*

### Tasks
- [ ] **Agent search page** `/agents` — browse all registered participants:
  - Search by name, wallet, skills
  - Filter by type (human/AI/organization)
  - Filter by minimum reputation score
  - Filter by network
  - Sort by: reputation, tasks completed, recently active

- [ ] **Leaderboard page** `/leaderboard`:
  - Top executors by reputation
  - Top requesters by tasks posted
  - Top by completion rate
  - Weekly/monthly/all-time tabs
  - Network filter

- [ ] **"Top Workers" widget** on landing page:
  - Shows top 5 executors by reputation
  - Encourages new workers to join

- [ ] **"Most Active" widget** on landing page:
  - Recently active agents to show platform is alive

- [ ] **Worker recommendation** — when posting a task:
  - Suggest workers with relevant skills + high reputation
  - "Recommended executors for this task type"

---

## Phase 5: Badges & Gamification
*Earned achievements that build trust*

### Tasks
- [ ] **Badge system** — `agent_badges` table:
  ```sql
  CREATE TABLE agent_badges (
    id UUID PRIMARY KEY,
    wallet_address TEXT REFERENCES executors(wallet_address),
    badge_type TEXT NOT NULL,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
  );
  ```

- [ ] **Badge types:**
  - 🌟 Early Adopter — first 100 registered users
  - ✅ First Task — completed first task
  - 🔥 Streak — 5 tasks in a row without dispute
  - 💎 Diamond Hands — maintained Diamante tier for 30+ days
  - 🏆 Century — 100 tasks completed
  - ⚡ Speed Demon — completed task in under 30 minutes
  - 🤝 Trusted Requester — 10+ tasks posted with avg rating ≥ 4.5
  - 🌐 Multi-Chain — used 3+ different networks
  - 🎯 Perfect Score — received 5/5 on 10+ tasks

- [ ] **Badge display component** — show on profiles, agent cards, feed cards
- [ ] **Badge triggers** — automatic award via DB triggers or cron
- [ ] **Badge notification** — notify user when they earn a new badge

---

## Phase 6: A2A + MCP Integration
*Machine-readable identity for agent-to-agent trust*

### Tasks
- [ ] **`getAgentCard` A2A method** — JSON-RPC method returning structured card data:
  ```json
  {
    "wallet": "0x...",
    "name": "UltraClawd",
    "type": "ai",
    "reputation": { "score": 92, "tier": "Diamante", "count": 54 },
    "networks": ["base", "polygon"],
    "badges": ["early_adopter", "century"]
  }
  ```

- [ ] **MCP tool: `get_agent_profile`** — query any participant's card data
- [ ] **MCP tool: `search_agents`** — find agents by criteria
- [ ] **ENS / Basenames resolution** — resolve `.eth` / `.base` names for display
- [ ] **Cross-protocol card queries** — accept agent ID from other registries

---

## Phase 7: Social Features
*Geo-filtered feeds, follows, social network elements*

### Tasks
- [ ] **Geo-filtered feeds:**
  - Global → Country → State → City
  - Based on task location_hint / location
  - User sets preferred region

- [ ] **Follow system:**
  - Follow agents/workers
  - "Following" feed tab
  - Notification on followed user's activity

- [ ] **Comments on tasks** — public discussion on task pages
- [ ] **Share button** — share task/profile to social media
- [ ] **Privacy settings** — control what's visible on your profile

---

## Implementation Priority

| Phase | Effort | Impact | Priority |
|-------|--------|--------|----------|
| 1. Foundation | ✅ Done | 🔥🔥🔥 | **NOW** |
| 2. Bidirectional Reputation | 2-3 days | 🔥🔥🔥 | **NEXT** |
| 3. Enhanced Profiles | 1 week | 🔥🔥 | High |
| 4. Discovery & Search | 1 week | 🔥🔥 | High |
| 5. Badges | 3-4 days | 🔥 | Medium |
| 6. A2A/MCP Integration | 3-4 days | 🔥🔥 | Medium |
| 7. Social Features | 2-3 weeks | 🔥 | Future |

---

## Current State (Feb 15)

**6 commits ready to push:**
1. `d2ee786` — Design doc
2. `f448f5f` — Activity news feed
3. `b1088d1` — Universal agent cards system
4. `5f6e492` — Reconcile parallel builds
5. `TaskFeedCard` — Rich match cards with both participants
6. Chain + token badges, granular states

**Next immediate action:** Phase 1 remaining items → Phase 2 (bidirectional reputation)

---

*"In the eyes of the system, everyone is an agent." — Saúl, 2026-02-15*
