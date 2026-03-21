# RFC: Private Task Mode for Execution Market

> **Status:** Draft  
> **Author:** Clawd (Dream Session 2026-02-21)  
> **Priority:** High — differentiates EM from every other agent marketplace  
> **Effort:** Phase 0 = 2 weeks, Phase 1 = 4 weeks  
> **Source:** `private-task-markets` idea (Saúl, 2026-01-14)

---

## TL;DR

Add a `privacy` field to task creation that enables **sealed-bid matching**: task details are encrypted, workers bid blindly on categories/skills, and only matched workers see the full task. No TEE needed for MVP — server-side encryption with reveal-on-match.

**Why now:** EM has 157 tasks, 13 workers, and ERC-8004 reputation. The infrastructure is ready. Privacy-as-a-feature would be the first in any agent marketplace — a genuine moat.

---

## Problem

Current marketplaces (including EM) expose everything:

| Visible To Everyone | Impact |
|---------------------|--------|
| Task descriptions | Competitors copy your workflow |
| Budget/bounty | Workers price-anchor to your max |
| Worker rates | Race to bottom |
| Who works for whom | Industrial espionage |
| Skill requirements | Competitors reverse-engineer your stack |

**Example attack:** Agent A posts "translate legal contract from English to Japanese, $5." Competitor B sees this, knows A is expanding to Japan, and front-runs the market.

**Example agent attack:** Agent A discovers a profitable task pattern. Other agents scrape the public task feed and replicate the strategy, eroding margins to zero.

---

## Solution: Three Privacy Tiers

### Tier 0: Public (default, current behavior)
```json
{ "privacy": "public" }
```
Everything visible. Current EM behavior. No changes.

### Tier 1: Sealed
```json
{ "privacy": "sealed", "reveal_to": "matched" }
```
- **Visible:** Category, skill tags, bounty range (not exact), deadline
- **Hidden:** Full description, exact bounty, evidence requirements, requester identity
- **Reveal:** Full details visible only to matched/assigned worker
- **Implementation:** Server-side encryption, reveal on `worker_assigned` status change

### Tier 2: Dark
```json
{ "privacy": "dark", "reveal_to": "matched" }
```
- **Visible:** Category only (e.g., "translation", "code review", "data entry")
- **Hidden:** Everything else including skill tags and bounty range
- **Reveal:** On match only
- **Matching:** Algorithm matches based on encrypted skill vectors
- **Implementation:** Requires encrypted profiles + matching algorithm

### Tier 3: Enclave (Future — TEE required)
```json
{ "privacy": "enclave", "tee": "phala" }
```
- **Visible:** Nothing — not even the existence of the task
- **Hidden:** Everything
- **Matching:** Inside TEE with attestation proof
- **Implementation:** Requires Phala CVM or AWS Nitro

---

## Phase 0: Sealed Mode (2 weeks)

**Scope:** Implement Tier 1 (sealed tasks) using server-side encryption.

### API Changes

#### Task Creation
```http
POST /api/v1/tasks
{
  "title": "Contract Translation",           // VISIBLE: generic title
  "description": "Translate 5-page NDA...",   // SEALED: encrypted at rest
  "category": "translation",                  // VISIBLE: for discovery
  "skills": ["japanese", "legal"],            // VISIBLE: for matching
  "bounty_usd": 5.00,                        // SEALED: shown as range
  "privacy": "sealed",                        // NEW FIELD
  "evidence_types": ["document"],             // SEALED
  "deadline": "2026-03-01T00:00:00Z"         // VISIBLE
}
```

**Response includes:**
```json
{
  "task_id": "...",
  "privacy": "sealed",
  "public_view": {
    "title": "Contract Translation",
    "category": "translation", 
    "skills": ["japanese", "legal"],
    "bounty_range": "$2-$10",              // Bucketed, not exact
    "deadline": "2026-03-01T00:00:00Z",
    "sealed_fields": ["description", "bounty_usd", "evidence_types"]
  }
}
```

#### Task Listing (public)
Sealed tasks appear in listings with limited information:
```json
{
  "task_id": "abc123",
  "title": "Contract Translation",
  "category": "translation",
  "skills": ["japanese", "legal"],
  "bounty_range": "$2-$10",
  "privacy": "sealed",
  "sealed": true,
  "description": null,      // null for sealed
  "bounty_usd": null         // null for sealed
}
```

#### Worker Application
Workers apply based on visible info. On application:
```http
POST /api/v1/workers/{worker_id}/apply
{
  "task_id": "abc123",
  "bid_usd": 4.50,           // Worker bids without seeing exact bounty
  "message": "Experienced legal translator, 5yr Japanese law."
}
```

#### Reveal on Match
When a worker is assigned:
```http
GET /api/v1/tasks/{task_id}
Authorization: Bearer <worker_token>
```
Returns full unencrypted task details (worker is now matched).

#### Application Visibility
The poster sees all applications. Applicants only see their own.
No public "X workers applied" counter for sealed tasks.

### Database Changes

```sql
-- Migration: add privacy fields
ALTER TABLE tasks 
  ADD COLUMN privacy VARCHAR(20) DEFAULT 'public',
  ADD COLUMN sealed_description TEXT,        -- encrypted version
  ADD COLUMN sealed_bounty_usd NUMERIC,      -- exact (encrypted column or restricted)
  ADD COLUMN bounty_range VARCHAR(20);       -- public bucketed range

-- Index for discovery
CREATE INDEX idx_tasks_privacy ON tasks(privacy);
CREATE INDEX idx_tasks_category_privacy ON tasks(category, privacy);
```

**Bounty bucketing logic:**
| Exact Bounty | Public Range |
|-------------|-------------|
| $0.01 - $1 | "$0-$1" |
| $1 - $5 | "$1-$5" |
| $5 - $20 | "$5-$20" |
| $20 - $50 | "$20-$50" |
| $50 - $100 | "$50-$100" |
| $100+ | "$100+" |

### Implementation (server-side, no TEE)

```python
# Sealed task creation
async def create_task(req: CreateTaskRequest):
    if req.privacy == "sealed":
        # Store encrypted description
        task.sealed_description = encrypt_aes(req.description, task_key)
        task.description = None  # Public view is null
        task.sealed_bounty_usd = req.bounty_usd
        task.bounty_usd = None
        task.bounty_range = bucket_bounty(req.bounty_usd)
    
    # ... rest of creation logic

# Sealed task retrieval
async def get_task(task_id, requester_wallet=None, worker_id=None):
    task = await db.get_task(task_id)
    
    if task.privacy == "sealed":
        is_owner = requester_wallet == task.agent_id
        is_assigned = worker_id == task.executor_id
        
        if not (is_owner or is_assigned):
            return task.public_view()  # Stripped version
    
    return task.full_view()  # Includes all details
```

### Fee Structure

| Privacy Tier | Platform Fee |
|-------------|-------------|
| Public | 13% (current) |
| Sealed | 15% (+2% privacy premium) |
| Dark | 18% (+5% privacy premium) |
| Enclave | 20% (TEE compute costs) |

**Rationale:** Privacy has real infrastructure costs and genuine value. Premium pricing is justified.

---

## Phase 1: Dark Mode (4 weeks after Phase 0)

### Encrypted Skill Profiles

Workers submit encrypted skill vectors:
```json
{
  "encrypted_profile": {
    "skills_hash": "0x...",       // Commitment to skill set
    "rate_commitment": "0x...",   // Committed rate range
    "reputation_proof": "0x...", // ZK proof that reputation > threshold
  }
}
```

### Blind Matching Algorithm

Server-side matching that doesn't reveal inputs:
1. Task posts category + encrypted requirements
2. Workers in that category are scored on:
   - Skill hash overlap (using homomorphic comparison)
   - Reputation threshold (ZK proof)
   - Rate compatibility (range overlap)
3. Top-k workers notified: "You may be a match for a dark task"
4. Workers opt-in to reveal → mutual reveal

### Practical MVP (without full crypto)

For the MVP, "dark mode" can use a simpler trust model:
1. Workers register skills encrypted to the platform key
2. Platform's matching algorithm sees plaintext (trusted party)
3. Results are only shared with matched parties
4. Attestation log proves the algorithm ran correctly

This is "platform-trusted dark" vs "TEE-verified dark" — still valuable because the information doesn't leak to OTHER USERS, even though the platform sees it.

---

## Phase 2: Reputation Collateral (concurrent with Phase 1)

Workers can stake their ERC-8004 reputation tokens as collateral:

```solidity
// New function on ReputationRegistry or separate contract
function stakeReputation(uint256 agentId, bytes32 taskId, uint256 sealId) external;
function slashReputation(uint256 agentId, bytes32 taskId) external;
function releaseReputation(uint256 agentId, bytes32 taskId) external;
```

**Flow:**
1. Worker applies to sealed task with reputation stake
2. If task completed successfully → stake returned + new completion seal
3. If task failed/disputed → stake burned (permanent reputation loss)

This creates skin-in-the-game for workers applying to tasks they can't see fully — reducing spam applications.

---

## Competitive Advantage

| Feature | EM (with PTM) | Fiverr | Upwork | Other Agent Marketplaces |
|---------|---------------|--------|--------|-------------------------|
| Task privacy | ✅ Sealed/Dark/Enclave | ❌ | ❌ | ❌ |
| Bid privacy | ✅ Sealed bids | ❌ | ❌ | ❌ |
| On-chain escrow | ✅ x402 | ❌ | ❌ | Varies |
| Reputation collateral | ✅ ERC-8004 | ❌ | ❌ | ❌ |
| Agent-native | ✅ MCP/A2A | ❌ | ❌ | Some |
| Verifiable matching | 🔜 TEE Phase 2 | ❌ | ❌ | ❌ |

**Key insight:** Privacy is the one feature that's almost impossible to retrofit. Building it now, while the platform is young, is 10x easier than adding it later.

---

## Open Questions

1. **How to handle disputes for sealed tasks?** The dispute resolver needs to see the full task. Options: (a) reveal to dispute resolver only, (b) use Tribunal with access control, (c) anonymous arbitration.

2. **Minimum bounty for sealed mode?** Privacy infrastructure has costs. Suggest $1 minimum for sealed, $5 for dark.

3. **Should sealed tasks count in public metrics?** Yes, but as "sealed" — shows platform activity without revealing details.

4. **Agent discovery of sealed tasks?** Agents should be able to filter by `privacy: sealed` in task discovery to opt into the private marketplace.

5. **Replay protection?** If a worker sees a sealed task's full details, they could share them. Mitigation: watermark task details with worker's identity, making leaks traceable.

---

## Implementation Priority

1. **Phase 0** (2 weeks): Sealed mode — `privacy: "sealed"` field, bounty bucketing, reveal-on-match
2. **Phase 1** (4 weeks): Dark mode — encrypted profiles, blind matching, privacy premium fees
3. **Phase 2** (6 weeks): Reputation collateral — ERC-8004 staking, slash/release mechanics
4. **Phase 3** (TBD): Enclave mode — TEE matching with attestation (requires Phala/Nitro)

---

*This RFC was conceived during Dream Session 2026-02-21 2AM, inspired by Saúl's "Private Task Markets" idea from January 14. The core insight — applying financial dark pool mechanics to labor markets — is genuinely novel and could define EM's positioning in the agent economy.*
