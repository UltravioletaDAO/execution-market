# 📰 Social News Feed — Planning Document

> **Author:** Clawd | **Date:** 2026-02-15
> **Status:** Planning | **Priority:** Post-Hackathon Phase 1

---

## Vision

Transform Execution Market from a task marketplace into a **social network of real-world work**. Users see a live feed of tasks being completed around the world, filtered by geography and social connections.

Think Instagram Stories meets TaskRabbit — but every "story" is a verified, paid, on-chain task.

---

## What We Already Have (DB Schema)

| Resource | Geo Fields | Status |
|----------|-----------|--------|
| `tasks` | `location GEOGRAPHY(POINT,4326)`, `location_radius_km`, `location_hint`, `location_address` | ✅ Ready |
| `executors` | `default_location GEOGRAPHY(POINT,4326)`, `location_city`, `location_country` | ✅ Ready |
| `submissions` | `evidence JSONB`, `evidence_files TEXT[]`, `evidence_ipfs_cid` | ✅ Ready |
| `tasks` indexes | `idx_tasks_location GIST`, `idx_executors_location GIST` | ✅ Ready |
| Follow system | — | ❌ Not built |
| Feed table | — | ❌ Not built |
| Geo parsing (city/state from lat/lng) | — | ❌ Not built |

**Key insight:** PostGIS `GEOGRAPHY(POINT,4326)` is already in the schema with GIST indexes. Geo queries are ready from day one.

---

## Phase 0: Data Foundation (Pre-requisite)
**Goal:** Ensure every task has structured geo data for feed filtering.
**Effort:** 1-2 days | **Dependencies:** None

### Tasks
- [ ] **0.1** Add `location_city`, `location_state`, `location_country` columns to `tasks` table
  - Migration: `ALTER TABLE tasks ADD COLUMN location_city VARCHAR(100), ADD COLUMN location_state VARCHAR(100), ADD COLUMN location_country VARCHAR(100)`
  - Index: `CREATE INDEX idx_tasks_location_city ON tasks(location_city)` etc.
- [ ] **0.2** Reverse geocoding service — parse `location` point → city/state/country
  - Option A: Use free Nominatim API (OpenStreetMap) at task creation
  - Option B: Use Mapbox/Google geocoding (more accurate, costs money)
  - Store results in the new columns at task creation time
- [ ] **0.3** Backfill existing tasks — parse `location_hint` text into structured fields
  - Script: regex extract from "Brickell, Miami, FL 33131" → city=Miami, state=Florida, country=US
  - For tasks with lat/lng: reverse geocode
  - For tasks with only text hints: NLP/regex extraction
- [ ] **0.4** Add `is_public` boolean to `submissions` table (default `true`)
  - Privacy control: workers can mark submissions as private
  - Feed only shows public submissions

---

## Phase 1: Global Activity Feed
**Goal:** A single feed showing all completed tasks worldwide, newest first.
**Effort:** 3-4 days | **Dependencies:** Phase 0

### Backend Tasks
- [ ] **1.1** Create `/api/v1/feed` endpoint
  ```
  GET /api/v1/feed?limit=20&cursor=<timestamp>&status=completed
  ```
  - Returns completed tasks with: title, category, bounty, location, executor display_name, evidence thumbnail, rating, completed_at
  - Cursor-based pagination (infinite scroll)
  - No auth required (public feed)
- [ ] **1.2** Create feed response model
  ```python
  class FeedItem:
      task_id: str
      title: str
      category: TaskCategory
      bounty_usd: float
      location_hint: str
      location_city: str | None
      location_country: str | None
      executor_display_name: str
      executor_avatar_url: str | None
      executor_reputation: int
      evidence_thumbnail_url: str | None  # First photo from evidence
      agent_rating: int | None  # Rating the agent gave
      completed_at: str
      time_to_complete_hours: float | None
  ```
- [ ] **1.3** Evidence thumbnail generation
  - On submission approval, generate a 400x400 thumbnail from the first evidence photo
  - Store in Supabase Storage: `evidence-thumbnails/{submission_id}.jpg`
  - If no photo evidence, use category icon as placeholder
- [ ] **1.4** SQL query for feed (optimized)
  ```sql
  SELECT t.id, t.title, t.category, t.bounty_usd, t.location_hint,
         t.location_city, t.location_country, t.completed_at,
         e.display_name, e.avatar_url, e.reputation_score,
         s.evidence, s.evidence_files
  FROM tasks t
  JOIN executors e ON t.executor_id = e.id
  LEFT JOIN submissions s ON s.task_id = t.id AND s.status = 'approved'
  WHERE t.status = 'completed'
    AND (s.id IS NULL OR s.is_public = true)
  ORDER BY t.completed_at DESC
  LIMIT $1 OFFSET $2
  ```

### Frontend Tasks
- [ ] **1.5** New tab in WorkerTasks: "Available | My Tasks | **Feed**"
  - Or: separate `/feed` route accessible from nav
- [ ] **1.6** FeedCard component
  - Avatar + display name + reputation badge
  - Task title + category icon
  - Evidence thumbnail (photo, expandable)
  - Location pin + city/country
  - Bounty amount + "completed X hours ago"
  - Rating stars (if rated)
- [ ] **1.7** Infinite scroll with cursor pagination
  - Load 20 items initially
  - Load more on scroll to bottom
  - Skeleton loading cards while fetching
- [ ] **1.8** Empty state: "No completed tasks yet. Be the first!"

---

## Phase 2: Geographic Filters
**Goal:** Filter feed by country, state/region, and city.
**Effort:** 3-4 days | **Dependencies:** Phase 0 + Phase 1

### Backend Tasks
- [ ] **2.1** Add geo filter params to `/api/v1/feed`
  ```
  GET /api/v1/feed?country=US&state=Florida&city=Miami&radius_km=25
  ```
- [ ] **2.2** Geo-proximity query using PostGIS
  ```sql
  WHERE ST_DWithin(t.location, ST_Point($lng, $lat)::geography, $radius_m)
  ```
  - Already have GIST index — this is fast
- [ ] **2.3** `/api/v1/feed/locations` endpoint — list available locations
  ```
  GET /api/v1/feed/locations
  → { countries: [{code: "US", name: "United States", task_count: 234}, ...],
      states: [{name: "Florida", country: "US", task_count: 89}, ...],
      cities: [{name: "Miami", state: "Florida", country: "US", task_count: 45}, ...] }
  ```
  - Cached, refreshed every 5 minutes
- [ ] **2.4** "Near me" filter using browser geolocation
  - `navigator.geolocation.getCurrentPosition()`
  - Default radius: 25km, adjustable

### Frontend Tasks
- [ ] **2.5** Location filter bar (horizontal pills)
  - 🌍 Global | 🇺🇸 US | 📍 Florida | 🏙️ Miami
  - Clicking expands to sub-regions
  - "Near Me" button (requests GPS permission)
- [ ] **2.6** Map view toggle (optional, Phase 2.5)
  - Mapbox GL / Leaflet showing task pins
  - Click pin → see completed task card
  - Cluster pins when zoomed out
- [ ] **2.7** Location selector in user profile
  - Set home city/country
  - Default feed filter based on profile location

---

## Phase 3: Social Layer (Follows + Friends Feed)
**Goal:** Follow other workers, see their activity in a dedicated feed.
**Effort:** 5-7 days | **Dependencies:** Phase 1

### Backend Tasks
- [ ] **3.1** Create `follows` table
  ```sql
  CREATE TABLE follows (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      follower_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,
      following_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE(follower_id, following_id),
      CHECK(follower_id != following_id)
  );
  CREATE INDEX idx_follows_follower ON follows(follower_id);
  CREATE INDEX idx_follows_following ON follows(following_id);
  ```
- [ ] **3.2** Follow/unfollow API endpoints
  ```
  POST /api/v1/users/{user_id}/follow
  DELETE /api/v1/users/{user_id}/follow
  GET /api/v1/users/{user_id}/followers?limit=20&cursor=
  GET /api/v1/users/{user_id}/following?limit=20&cursor=
  ```
- [ ] **3.3** Friends feed filter
  ```
  GET /api/v1/feed?scope=following
  ```
  ```sql
  WHERE t.executor_id IN (
      SELECT following_id FROM follows WHERE follower_id = $current_user
  )
  ```
- [ ] **3.4** Follower/following counts on executor profile
- [ ] **3.5** "People you might know" suggestions
  - Based on: same city, completed similar tasks, mutual follows
- [ ] **3.6** Privacy settings
  ```sql
  ALTER TABLE executors ADD COLUMN feed_privacy VARCHAR(20) DEFAULT 'public';
  -- Values: 'public', 'followers_only', 'private'
  ```

### Frontend Tasks
- [ ] **3.7** Follow button on user profiles and feed cards
- [ ] **3.8** Feed scope tabs: "Global | Near Me | Following"
- [ ] **3.9** User profile page enhancements
  - Follower/following counts (clickable → list)
  - Activity timeline (their completed tasks)
  - Follow/unfollow button
- [ ] **3.10** Notifications: "Juan started following you", "Maria completed a task near you"
- [ ] **3.11** "Suggested Workers" sidebar/section

---

## Phase 4: Rich Feed Features
**Goal:** Make the feed engaging and interactive.
**Effort:** 4-5 days | **Dependencies:** Phase 1-3

### Tasks
- [ ] **4.1** Reactions on feed items (👏 🔥 💪 ⭐)
  - Table: `feed_reactions(id, executor_id, task_id, emoji, created_at)`
  - Show reaction counts on feed cards
- [ ] **4.2** Comments on completed tasks
  - Table: `feed_comments(id, task_id, executor_id, content, created_at)`
  - "Great work!" "How long did this take?" etc.
- [ ] **4.3** Share task to external (Twitter/X, copy link)
  - OG meta tags for task pages (preview card when shared)
  - `execution.market/task/{id}` public view
- [ ] **4.4** Worker streaks and achievements
  - "🔥 5-day streak", "💯 10 tasks completed", "🌎 Tasks in 3 countries"
  - Show on feed cards and profile
- [ ] **4.5** Real-time feed updates (Supabase Realtime)
  - New completed tasks appear at top with animation
  - "3 new tasks completed" banner (like Twitter)
- [ ] **4.6** Feed notification preferences
  - Email digest: daily/weekly summary of followed workers' activity
  - Push notifications for nearby completed tasks

---

## Phase 5: Discovery & Leaderboards
**Goal:** Gamification and discovery to drive engagement.
**Effort:** 3-4 days | **Dependencies:** Phase 2-3

### Tasks
- [ ] **5.1** Leaderboards
  - Global top workers (by tasks completed, by earnings, by rating)
  - City/country leaderboards
  - Weekly/monthly resets
- [ ] **5.2** Trending locations
  - "🔥 Trending in Miami: 12 tasks completed today"
  - Based on completion velocity
- [ ] **5.3** Worker profiles as public pages
  - `execution.market/@username`
  - Portfolio of completed tasks with evidence
  - Verifiable on-chain reputation score
- [ ] **5.4** Search workers by skill/location/availability
- [ ] **5.5** "Featured Tasks" curated section

---

## Technical Architecture

### Feed Query Optimization
```
Tasks table (PostGIS GIST index) 
  → JOIN executors (B-tree on id)
  → LEFT JOIN submissions (B-tree on task_id)
  → WHERE status = 'completed'
  → ORDER BY completed_at DESC
  → LIMIT/OFFSET or cursor pagination
```

**Performance targets:**
- Feed load: < 200ms for 20 items
- Geo query (radius): < 300ms with GIST index
- Following feed: < 250ms (indexed follows table)

### Caching Strategy
- Location hierarchy (countries/states/cities): Redis, 5-min TTL
- Feed items: No cache (always fresh, paginated)
- User follow counts: Redis, 1-min TTL
- Leaderboards: Redis, 15-min TTL

### Storage
- Evidence thumbnails: Supabase Storage (auto-generated on approval)
- Full evidence: Existing Supabase Storage + IPFS

---

## Priority & Timeline

| Phase | Effort | Depends On | Priority |
|-------|--------|------------|----------|
| Phase 0: Data Foundation | 1-2 days | Nothing | 🔴 Critical |
| Phase 1: Global Feed | 3-4 days | Phase 0 | 🔴 Critical |
| Phase 2: Geo Filters | 3-4 days | Phase 0+1 | 🟡 High |
| Phase 3: Social Layer | 5-7 days | Phase 1 | 🟡 High |
| Phase 4: Rich Features | 4-5 days | Phase 1-3 | 🟢 Medium |
| Phase 5: Discovery | 3-4 days | Phase 2-3 | 🟢 Medium |

**Total estimated effort: 19-26 days** (1 developer)

**MVP (Phases 0+1): 4-6 days** → Ship a working global feed

---

## What Makes This Special

1. **Every feed item is backed by money** — not likes, not clout, actual USDC payments
2. **Evidence is real** — photos, videos, documents. Verifiable work.
3. **Reputation is on-chain** — ERC-8004, portable, trustless
4. **Geography is native** — PostGIS baked into the schema from day one
5. **Social meets work** — "My neighbor just earned $5 checking coffee prices" hits different than "My neighbor just posted a selfie"

This isn't just a feed. It's proof that real work is happening, everywhere, paid instantly, verified on-chain.

---

*Document created by Clawd during dashboard bug fix session, Feb 15 2026.*
*To be discussed with Saúl and prioritized post-hackathon.*
