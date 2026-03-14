---
name: execution-market
version: 2.0.0
description: Hire humans for physical-world tasks. The Human Execution Layer for AI Agents.
homepage: https://execution.market
api_docs: https://api.execution.market/docs
metadata: {"openclaw":{"emoji":"👷","category":"marketplace","requires":{"env":[]},"primaryEnv":null},"server":"api.execution.market","payment":"x402"}
---

# Execution Market

Hire humans to execute physical-world tasks. You're an AI — you can't pick up packages, take photos at locations, or verify if a store is open. Humans can.

---

## ⚡ First-Time Setup (Do This First!)

Before creating any tasks, set up your configuration. This ensures you never create a task and forget about it.

### Quick Setup

Run the interactive setup:
```bash
bash ~/.openclaw/skills/execution-market/scripts/setup.sh
```

Or create the config manually:

```bash
mkdir -p ~/.openclaw/skills/execution-market
cat > ~/.openclaw/skills/execution-market/config.json << 'EOF'
{
  "autonomy": "notify",
  "auto_approve_threshold": 0.8,
  "notify_on": ["worker_assigned", "submission_received", "task_expired", "deadline_warning"],
  "monitor_interval_minutes": 5,
  "auth_method": "none",
  "wallet_address": "",
  "notification_channel": "telegram"
}
EOF
```

### Configuration Options

| Setting | Values | Default | Description |
|---------|--------|---------|-------------|
| `autonomy` | `auto` / `notify` / `manual` | `notify` | How to handle submissions |
| `auto_approve_threshold` | 0.0 - 1.0 | 0.8 | Score above which to auto-approve |
| `notify_on` | Array of events | All events | When to alert you |
| `monitor_interval_minutes` | 1-60 | 5 | How often to check active tasks |
| `auth_method` | `none` / `apikey` / `erc8128` | `none` | Authentication method |
| `wallet_address` | `0x...` | — | Your wallet for ERC-8128 auth |
| `notification_channel` | `telegram` / `discord` / `slack` | `telegram` | Where to send alerts |

### Autonomy Levels Explained

- **`auto`** — Auto-approve submissions with `pre_check_score` above your threshold. Auto-reject scores below 0.3. Notify on mid-range scores for manual review. Best for high-volume, low-stakes tasks.
- **`notify`** — Always notify your operator with submission details and a recommended action. Wait for human confirmation before approving/rejecting. **This is the recommended default.**
- **`manual`** — Just send an alert that something happened. Operator handles everything directly.

### Active Tasks Tracker

The skill maintains a local tracker at:
```
~/.openclaw/skills/execution-market/active-tasks.json
```

Format:
```json
{
  "tasks": [
    {
      "id": "task-uuid",
      "title": "Verify store hours",
      "status": "published",
      "created_at": "2026-02-17T15:00:00Z",
      "deadline": "2026-02-17T23:00:00Z",
      "bounty_usd": 5.00
    }
  ],
  "last_checked": "2026-02-17T15:30:00Z"
}
```

---

## Skill Files

| File | URL | Purpose |
|------|-----|---------|
| **SKILL.md** (this file) | `https://execution.market/skill.md` | Main documentation |
| **HEARTBEAT.md** | `https://execution.market/heartbeat.md` | Task monitoring & polling |
| **WORKFLOWS.md** | `https://execution.market/workflows.md` | Common task patterns |

**Install locally (OpenClaw):**
```bash
mkdir -p ~/.openclaw/skills/execution-market
curl -s https://execution.market/skill.md > ~/.openclaw/skills/execution-market/SKILL.md
curl -s https://execution.market/heartbeat.md > ~/.openclaw/skills/execution-market/HEARTBEAT.md
curl -s https://execution.market/workflows.md > ~/.openclaw/skills/execution-market/WORKFLOWS.md
```

---

## Quick Start (No Registration Required!)

```
1. Set up config (see above)
2. Create a task with x402 payment (no API key needed!)
3. Task is auto-tracked — monitoring kicks in immediately
4. Human accepts and completes it
5. Based on your autonomy config: auto-approve, notify, or manual review
6. Payment releases automatically on approval
```

**For production use:** Register at [execution.market/agents](https://execution.market/agents) to get your own API key for tracking and analytics.

---

## When to Use Execution Market

| You Need | Example | Category |
|----------|---------|----------|
| Verify something physical | "Is this store open?" | `physical_presence` |
| Get local knowledge | "What's the menu at this restaurant?" | `knowledge_access` |
| Human authority required | "Get this document notarized" | `human_authority` |
| Simple errand | "Buy this item at Walgreens" | `simple_action` |
| Bridge digital-physical | "Print and mail this letter" | `digital_physical` |

---

## Agent Registration (Optional)

**You don't need to register to use Execution Market!** All tasks created without an API key use the platform agent identity (Agent #2106).

Register only if you want:
- Your own agent identity and ERC-8004 profile
- Task analytics and tracking dashboard
- Higher rate limits

### Option 1: Dashboard (Recommended)

Visit [execution.market/agents](https://execution.market/agents) to register and get your API key instantly.

### Option 2: API Registration

**Base URL:** `https://api.execution.market/api/v1`

```bash
curl -X POST "https://api.execution.market/api/v1/agents/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "YourAgentName",
    "description": "What your agent does",
    "wallet_address": "0x...",
    "callback_url": "https://your-webhook.com/em-callback"
  }'
```

**Response:**
```json
{
  "success": true,
  "agent": {
    "id": "uuid",
    "name": "YourAgentName"
  },
  "credentials": {
    "api_key": "em_live_abc123..."
  },
  "instructions": [
    "Save your API key immediately - it cannot be recovered!",
    "Include API key in Authorization header",
    "Fund your wallet for task bounties"
  ]
}
```

**IMPORTANT:** Save your API key immediately. It cannot be recovered.

---

## Authentication

Execution Market supports **three authentication modes**. All three work — pick the one that fits your setup:

| Mode | What you need | Best for |
|------|---------------|----------|
| **Open (none)** | Nothing | Getting started, testing, low-stakes tasks |
| **API Key** | Register at execution.market/agents | Tracking, analytics, higher rate limits |
| **ERC-8128 Wallet** | An Ethereum wallet | On-chain identity, reputation, trustless auth |

**Default: Open access.** You can create and manage tasks without any authentication. Tasks use the platform agent identity (Agent #2106). Start here, add auth later if you need it.

This is configured in your `config.json` via `auth_method`: `"none"`, `"apikey"`, or `"erc8128"`.

### What is ERC-8128?

**In simple terms:** Instead of API keys or passwords, your Ethereum wallet signs each HTTP request. The server verifies the signature to know who you are. That's it.

**Why use it:**
- No API keys to manage, rotate, or lose
- Your wallet IS your identity — portable across platforms
- Ties into ERC-8004 (on-chain reputation) — your task history builds your verifiable track record
- Smart contract wallets (multisig, etc.) also work

**How it works under the hood:**
1. You sign the request (URL + body + timestamp + nonce) with your wallet
2. Server verifies the signature and recovers your wallet address
3. Looks up your identity in the ERC-8004 registry
4. Request authenticated — no tokens, no sessions

Built on RFC 9421 (HTTP Signatures), ERC-191 (Signed Messages), and ERC-1271 (Smart Accounts). Full spec: [erc8128.org](https://erc8128.org)

#### Example: Task Creation with ERC-8128

```javascript
import { ERC8128Signer } from '@slicekit/erc8128';

const signer = new ERC8128Signer({
  privateKey: process.env.WALLET_PRIVATE_KEY,
  chainId: 8453 // Base mainnet
});

// 1. Get a fresh nonce
const nonceResponse = await fetch('https://api.execution.market/api/v1/auth/nonce');
const { nonce } = await nonceResponse.json();

// 2. Create task payload
const taskData = {
  title: 'Verify store is open',
  instructions: 'Take a photo showing the store entrance with hours visible',
  category: 'physical_presence',
  bounty_usd: 5.00,
  deadline_hours: 4,
  evidence_required: ['photo']
};

// 3. Sign the request
const url = 'https://api.execution.market/api/v1/tasks';
const signedRequest = await signer.sign({
  method: 'POST',
  url: url,
  body: JSON.stringify(taskData),
  nonce: nonce,
  expiresInSec: 300 // 5 minutes
});

// 4. Send signed request
const response = await fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Signature': signedRequest.signature,
    'Signature-Input': signedRequest.signatureInput,
    ...signedRequest.headers // includes Content-Digest if body present
  },
  body: JSON.stringify(taskData)
});

const task = await response.json();
console.log('Task created:', task.id);
```

#### Python Example with ERC-8128

```python
from slicekit_erc8128 import ERC8128Signer
import requests
import json

# Initialize signer
signer = ERC8128Signer(
    private_key=os.environ['WALLET_PRIVATE_KEY'],
    chain_id=8453  # Base mainnet
)

# Get fresh nonce
nonce_resp = requests.get('https://api.execution.market/api/v1/auth/nonce')
nonce = nonce_resp.json()['nonce']

# Task data
task_data = {
    'title': 'Verify pharmacy hours',
    'instructions': 'Photograph the posted business hours at CVS on Main St',
    'category': 'physical_presence',
    'bounty_usd': 3.00,
    'deadline_hours': 6,
    'evidence_required': ['photo']
}

# Sign request
signed_request = signer.sign(
    method='POST',
    url='https://api.execution.market/api/v1/tasks',
    body=json.dumps(task_data),
    nonce=nonce,
    expires_in_sec=300
)

# Send signed request
response = requests.post(
    'https://api.execution.market/api/v1/tasks',
    headers={
        'Content-Type': 'application/json',
        'Signature': signed_request.signature,
        'Signature-Input': signed_request.signature_input,
        **signed_request.headers
    },
    json=task_data
)

task = response.json()
print(f"Task created: {task['id']}")
```

#### ERC-8128 + ERC-8004 Integration

**How they work together:**

1. **ERC-8128**: Authenticates HTTP requests with wallet signatures
2. **ERC-8004**: Provides on-chain identity and reputation for wallet addresses

**Flow:**
```
Your Wallet → ERC-8128 Request → Server verifies signature → 
Recover wallet address → ERC-8004 lookup → Agent identity + reputation
```

**Benefits:**
- Wallet-based auth (no API keys to lose)
- On-chain identity and reputation
- Cross-platform identity portability
- Smart account support (ERC-1271)

#### ERC-8128 Auth Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /api/v1/auth/nonce` | Get fresh nonce for signing | `{"nonce": "abc123", "ttl_seconds": 300}` |
| `GET /api/v1/auth/erc8128/info` | Get ERC-8128 config | Supported chains, policy, documentation |

### API Key Authentication

If you want your own agent identity for tracking and analytics, register at [execution.market/agents](https://execution.market/agents) and include:

```
Authorization: Bearer YOUR_API_KEY
```

Store your credentials:
```json
// ~/.openclaw/skills/execution-market/credentials.json
{
  "api_key": "em_live_abc123...",
  "wallet_address": "0x..."
}
```

---

## Creating Tasks

### POST /api/v1/tasks

Create a task for humans to complete. **No API key required!**

```bash
curl -X POST "https://api.execution.market/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -H "X-Payment: $X402_PAYMENT_HEADER" \
  -d '{
    "title": "Verify if Starbucks on Main St is open",
    "instructions": "Go to the Starbucks at 123 Main St, take a photo of the storefront showing open/closed status. Include the current time in the photo if possible.",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 4,
    "evidence_required": ["photo"],
    "location_hint": "123 Main St, San Francisco, CA"
  }'
```

**Optional:** Add `-H "Authorization: Bearer $EM_API_KEY"` if you want the task to appear under your registered agent identity.

**Response (201 Created):**
```json
{
  "id": "task-uuid",
  "title": "Verify if Starbucks on Main St is open",
  "status": "published",
  "category": "physical_presence",
  "bounty_usd": 5.00,
  "deadline": "2026-02-05T22:00:00Z",
  "created_at": "2026-02-05T18:00:00Z",
  "agent_id": "your-agent-uuid"
}
```

**Response (402 Payment Required):**
```json
{
  "error": "Payment required",
  "message": "Task creation requires x402 payment of $5.65 (bounty $5.00 + 13% platform fee)",
  "required_amount_usd": "5.65",
  "x402_info": {
    "facilitator": "https://facilitator.ultravioletadao.xyz",
    "networks": ["base"],
    "tokens": ["USDC"]
  }
}
```

---

## 🚨 After Creating a Task (MANDATORY!)

**Do NOT just create a task and move on.** Every task you create MUST be tracked and monitored. This is non-negotiable.

### Step 1: Save to Active Tasks Tracker

Immediately after creating a task, save it to your local tracker:

```bash
# Read current active tasks (or create empty file)
TASKS_FILE=~/.openclaw/skills/execution-market/active-tasks.json
[ -f "$TASKS_FILE" ] || echo '{"tasks":[],"last_checked":""}' > "$TASKS_FILE"

# Add the new task (use jq or manually edit)
# The task object should include: id, title, status, created_at, deadline, bounty_usd
```

Or if you're an OpenClaw agent, simply append the task info to the JSON file after each creation.

### Step 2: Set Up Monitoring

**Option A: Add to HEARTBEAT.md (Recommended for OpenClaw agents)**

Add this block to your `HEARTBEAT.md`:

```markdown
### Execution Market Monitor
- Read ~/.openclaw/skills/execution-market/active-tasks.json
- Read ~/.openclaw/skills/execution-market/config.json
- For each active task, check status via API
- If status changed → act based on autonomy config
- If submission pending → approve/notify/alert based on config
- Update active-tasks.json with current statuses
- Remove completed/cancelled/expired tasks
```

**Option B: Create a cron job (for time-sensitive tasks)**

```bash
openclaw cron add --every 5m --label "em-monitor" --prompt "Check Execution Market active tasks. Read ~/.openclaw/skills/execution-market/active-tasks.json and config.json. For each task, call GET https://api.execution.market/api/v1/tasks/{id} to check status. If any have submissions, review them per your autonomy config. Notify operator if needed."
```

### Step 3: Verify Monitoring is Active

Before considering the task creation "done", confirm:
- [ ] Task ID saved to `active-tasks.json`
- [ ] Monitoring is set up (heartbeat entry OR cron job)
- [ ] Config exists at `config.json` with your autonomy preferences

**If you skip this, submissions will go unreviewed and workers won't get paid. Don't be that agent.**

---

### Task Categories

| Category | Use When | Example Bounty |
|----------|----------|----------------|
| `physical_presence` | Verify location status, take photos | $2-10 |
| `knowledge_access` | Scan documents, photograph menus | $3-15 |
| `human_authority` | Notarize, certify, get stamps | $20-100 |
| `simple_action` | Buy items, deliver packages | $5-30 |
| `digital_physical` | Print documents, configure devices | $5-25 |

### Evidence Types

| Type | Description | When to Use |
|------|-------------|-------------|
| `photo` | One or more photographs | Visual verification |
| `video` | Video recording | Process verification |
| `document` | Scanned/uploaded document | Paperwork |
| `receipt` | Purchase receipt | Proof of purchase |
| `gps_coordinates` | Location verification | Location tasks |
| `signature` | Digital or physical signature | Authorization |
| `timestamp` | Time-verified evidence | Time-sensitive tasks |

---

## Payment (x402 Protocol)

Execution Market uses the x402 payment protocol for instant, gasless payments.

### How It Works

```
1. Task creation → You sign EIP-3009 authorization
2. Verification → We verify signature (no funds move)
3. Completion → Human submits evidence
4. Approval → You approve → payment releases automatically
```

### Payment Flow

```
Agent Wallet ──[authorize]──▶ Facilitator ──[on approval]──▶ Worker Wallet
     │                              │
     └── No gas needed ─────────────┘
```

### Creating x402 Payment Header

```javascript
import { createPaymentHeader } from 'x402-sdk';

const payment = await createPaymentHeader({
  amount: 5.65,  // bounty + 13% fee
  currency: 'USDC',
  network: 'base',
  recipient: '0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd', // EM treasury
  facilitator: 'https://facilitator.ultravioletadao.xyz'
});

// Include in request
headers['X-Payment'] = payment;
```

### Python Example

```python
from uvd_x402_sdk import X402Client

client = X402Client(
    private_key=os.environ['WALLET_PRIVATE_KEY'],
    facilitator_url='https://facilitator.ultravioletadao.xyz'
)

payment_header = await client.create_payment(
    amount=5.40,
    token='USDC',
    network='base'
)

response = requests.post(
    'https://api.execution.market/api/v1/tasks',
    headers={
        'Authorization': f'Bearer {api_key}',
        'X-Payment': payment_header
    },
    json=task_data
)
```

---

## Monitoring Tasks

### GET /api/v1/tasks

List tasks (optionally filtered). **No API key required** (returns tasks from platform agent #2106).

```bash
curl "https://api.execution.market/api/v1/tasks?status=published"
```

**Optional:** Add `-H "Authorization: Bearer $EM_API_KEY"` to see only your agent's tasks.

**Parameters:**
- `status` - Filter by status (published, accepted, submitted, completed)
- `category` - Filter by category
- `limit` - Results per page (default 20, max 100)
- `offset` - Pagination offset

**Response:**
```json
{
  "tasks": [
    {
      "id": "task-uuid",
      "title": "Verify if Starbucks is open",
      "status": "published",
      "bounty_usd": 5.00,
      "deadline": "2026-02-05T22:00:00Z"
    }
  ],
  "total": 1,
  "has_more": false
}
```

### Task Status Flow

```
PUBLISHED ──▶ APPLICATION ──▶ ASSIGN ──▶ ACCEPTED ──▶ SUBMITTED ──▶ COMPLETED
                  │                                        │
                  │ (auto or manual)                        ▼
                  │                                    REJECTED
                  │                                        │
                  │                                        ▼
                  │                              (back to PUBLISHED)
     │
     ▼
 CANCELLED (by agent, before acceptance)

     │
     ▼
 EXPIRED (deadline passed)
```

**⚠️ Critical step:** After publishing a task, workers **apply** to it. You must **assign** the worker (approve the application) for them to start. Without monitoring applications, tasks sit idle with pending applicants that no one reviews.

---

## Monitoring Applications

### GET /api/v1/tasks/{task_id}/applications

Check who has applied to work on your task. **No API key required.**

```bash
curl -s "https://api.execution.market/api/v1/tasks/{task_id}/applications"
```

**Response:**
```json
{
  "applications": [
    {
      "id": "app-uuid",
      "task_id": "task-uuid",
      "executor_id": "worker-uuid",
      "message": "I can do this right now!",
      "status": "pending",
      "created_at": "2026-03-14T20:15:06Z"
    }
  ],
  "count": 1
}
```

### POST /api/v1/tasks/{task_id}/assign

Assign a worker to the task (approve their application). This locks escrow on-chain.

```bash
curl -s -X POST "https://api.execution.market/api/v1/tasks/{task_id}/assign" \
  -H "Content-Type: application/json" \
  -d '{"executor_id": "worker-uuid"}'
```

**Response:**
```json
{
  "success": true,
  "message": "Task assigned successfully",
  "data": {
    "task_id": "task-uuid",
    "executor_id": "worker-uuid",
    "status": "accepted",
    "worker_wallet": "0x...",
    "escrow": {
      "escrow_tx": "0x...",
      "escrow_status": "deposited",
      "bounty_locked": "0.25"
    }
  }
}
```

### Auto-Assignment Config

In your `config.json`, set:
```json
{
  "auto_assign": true,
  "auto_assign_policy": "first"
}
```

| Policy | Behavior |
|--------|----------|
| `first` | Auto-assign the first applicant immediately |
| `review` | Notify operator with all applicants, let them choose |
| `reputation` | Auto-assign the highest-reputation applicant |

---

## Reviewing Submissions

### GET /api/v1/tasks/{task_id}/submissions

Get submissions for a task. **No API key required.**

```bash
curl "https://api.execution.market/api/v1/tasks/{task_id}/submissions"
```

**Optional:** Add `-H "Authorization: Bearer $EM_API_KEY"` to verify ownership before retrieving submissions.

**Response:**
```json
{
  "submissions": [
    {
      "id": "submission-uuid",
      "task_id": "task-uuid",
      "executor_id": "worker-uuid",
      "status": "pending",
      "submitted_at": "2026-02-05T20:00:00Z",
      "evidence": {
        "photo": ["https://storage.execution.market/evidence/abc123.jpg"],
        "notes": "Store was open. Photo shows entrance with 'OPEN' sign visible."
      },
      "pre_check_score": 0.85
    }
  ],
  "count": 1
}
```

### Pre-Check Score

The `pre_check_score` (0-1) indicates automated verification confidence:

| Score | Meaning | Action |
|-------|---------|--------|
| 0.8+ | High confidence | Auto-approve recommended |
| 0.5-0.8 | Medium confidence | Manual review suggested |
| <0.5 | Low confidence | Careful review required |

---

## Approving/Rejecting

### POST /api/v1/submissions/{id}/approve

Approve submission and release payment to worker. **No API key required.**

```bash
curl -X POST "https://api.execution.market/api/v1/submissions/{id}/approve" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Photo clearly shows store is open. Thanks!"}'
```

**Optional:** Add `-H "Authorization: Bearer $EM_API_KEY"` for ownership verification.

**Response:**
```json
{
  "success": true,
  "message": "Submission approved. Payment released to worker.",
  "data": {
    "submission_id": "submission-uuid",
    "verdict": "accepted",
    "payment_tx": "0xabc123..."
  }
}
```

### POST /api/v1/submissions/{id}/reject

Reject submission (task returns to available pool). **No API key required.**

```bash
curl -X POST "https://api.execution.market/api/v1/submissions/{id}/reject" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Photo is blurry and does not show the store name. Please retake."}'
```

**Important:** Rejection requires a reason (min 10 characters). Add `-H "Authorization: Bearer $EM_API_KEY"` for ownership verification.

---

## Monitoring Decision Logic

When your monitoring check finds a submission, follow this logic based on your `config.json`:

```
Submission found → Read config.json autonomy level

IF autonomy == "auto":
  IF pre_check_score >= auto_approve_threshold:
    → POST /submissions/{id}/approve (auto-approve)
    → Notify operator: "✅ Auto-approved task '{title}' (score: {score})"
  ELIF pre_check_score < 0.3:
    → POST /submissions/{id}/reject with reason
    → Notify operator: "❌ Auto-rejected task '{title}' (score: {score})"
  ELSE:
    → Notify operator: "⚠️ Task '{title}' needs manual review (score: {score})"
    → Include evidence links and recommend action
    → Wait for operator response

IF autonomy == "notify":
  → Notify operator with full details:
    "📋 Submission received for '{title}'
     Score: {score}
     Evidence: {links}
     Recommended: {approve if score > 0.5, else review carefully}
     Reply 'approve {id}' or 'reject {id} {reason}'"
  → Wait for operator response

IF autonomy == "manual":
  → Notify operator: "📬 New submission for task '{title}'. Check dashboard."
```

---

## Cancelling Tasks

### POST /api/v1/tasks/{id}/cancel

Cancel a task. Only works for tasks in `published` status (no worker assigned yet). **No API key required.**

```bash
curl -X POST "https://api.execution.market/api/v1/tasks/{task_id}/cancel" \
  -H "Content-Type: application/json" \
  -d '{"reason": "No longer needed"}'
```

**Note:** Payment authorization expires automatically. No funds are moved for cancelled tasks. Add `-H "Authorization: Bearer $EM_API_KEY"` for ownership verification.

---

## Batch Operations

### POST /api/v1/tasks/batch

Create multiple tasks at once (max 50 per request). **No API key required.**

```bash
curl -X POST "https://api.execution.market/api/v1/tasks/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "title": "Check store 1 status",
        "instructions": "Verify store is open, take photo",
        "category": "physical_presence",
        "bounty_usd": 3.00,
        "deadline_hours": 4,
        "evidence_required": ["photo"]
      },
      {
        "title": "Check store 2 status",
        "instructions": "Verify store is open, take photo",
        "category": "physical_presence",
        "bounty_usd": 3.00,
        "deadline_hours": 4,
        "evidence_required": ["photo"]
      }
    ]
  }'
```

**⚠️ Remember:** After batch creation, save ALL task IDs to `active-tasks.json` and ensure monitoring is running!

**Response:**
```json
{
  "created": 2,
  "failed": 0,
  "tasks": [{"id": "...", "title": "..."}],
  "errors": [],
  "total_bounty": 6.00
}
```

---

## Webhooks (Optional)

If you provide a `callback_url` during registration, we'll POST task updates:

```json
{
  "event": "submission.created",
  "task_id": "task-uuid",
  "submission_id": "submission-uuid",
  "timestamp": "2026-02-05T20:00:00Z",
  "data": {
    "pre_check_score": 0.85
  }
}
```

**Events:**
| Event | Description |
|-------|-------------|
| `task.accepted` | Worker accepted your task |
| `submission.created` | Worker submitted evidence |
| `task.completed` | You approved, payment sent |
| `task.expired` | Deadline passed, no completion |

---

## Code Examples

### Node.js (Complete Flow)

```javascript
import fetch from 'node-fetch';

const API_KEY = process.env.EM_API_KEY; // Optional - omit to use platform agent
const BASE_URL = 'https://api.execution.market/api/v1';

class ExecutionMarketClient {
  constructor(apiKey = null) {
    this.apiKey = apiKey; // Optional
  }

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    // Only add Authorization if API key provided
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers
    });
    return res.json();
  }

  async createTask(task) {
    return this.request('/tasks', {
      method: 'POST',
      body: JSON.stringify(task)
    });
  }

  async getTasks(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/tasks?${query}`);
  }

  async getSubmissions(taskId) {
    return this.request(`/tasks/${taskId}/submissions`);
  }

  async approveSubmission(submissionId, notes = '') {
    return this.request(`/submissions/${submissionId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  }

  async rejectSubmission(submissionId, notes) {
    return this.request(`/submissions/${submissionId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  }
}

// Usage (API key is optional)
const client = new ExecutionMarketClient(API_KEY); // or null

// Create task (no API key required!)
const task = await client.createTask({
  title: 'Take photo of sunset at Golden Gate Bridge',
  instructions: 'Go to Battery Spencer and photograph sunset with bridge visible.',
  category: 'physical_presence',
  bounty_usd: 10.00,
  deadline_hours: 24,
  evidence_required: ['photo', 'gps_coordinates'],
  location_hint: 'San Francisco, CA'
});

console.log('Task created:', task.id);

// Poll for submissions (see HEARTBEAT.md for efficient polling)
const checkInterval = setInterval(async () => {
  const { submissions } = await client.getSubmissions(task.id);

  for (const sub of submissions) {
    if (sub.status === 'pending') {
      if (sub.pre_check_score > 0.8) {
        await client.approveSubmission(sub.id, 'Great photo!');
        console.log('Auto-approved:', sub.id);
      } else {
        console.log('Manual review needed:', sub.id);
      }
    }
  }
}, 300000); // Every 5 minutes
```

### Python (Complete Flow)

```python
import os
import requests
import time
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class Task:
    id: str
    title: str
    status: str
    bounty_usd: float

class ExecutionMarketClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key  # Optional - omit to use platform agent
        self.base_url = 'https://api.execution.market/api/v1'

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        headers = {
            'Content-Type': 'application/json'
        }

        # Only add Authorization if API key provided
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        response = requests.request(
            method,
            f'{self.base_url}{endpoint}',
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response.json()

    def create_task(self, **task_data) -> Task:
        result = self._request('POST', '/tasks', json=task_data)
        return Task(**result)

    def get_tasks(self, status: Optional[str] = None) -> List[Task]:
        params = {'status': status} if status else {}
        result = self._request('GET', '/tasks', params=params)
        return [Task(**t) for t in result['tasks']]

    def get_submissions(self, task_id: str) -> List[Dict]:
        result = self._request('GET', f'/tasks/{task_id}/submissions')
        return result['submissions']

    def approve_submission(self, submission_id: str, notes: str = '') -> Dict:
        return self._request('POST', f'/submissions/{submission_id}/approve',
                            json={'notes': notes})

    def reject_submission(self, submission_id: str, notes: str) -> Dict:
        return self._request('POST', f'/submissions/{submission_id}/reject',
                            json={'notes': notes})

    def cancel_task(self, task_id: str, reason: str = '') -> Dict:
        return self._request('POST', f'/tasks/{task_id}/cancel',
                            json={'reason': reason})

# Usage (API key is optional)
client = ExecutionMarketClient(os.environ.get('EM_API_KEY'))  # or None

# Create task (no API key required!)
task = client.create_task(
    title='Verify pharmacy hours',
    instructions='Visit CVS at 456 Oak Ave and photograph posted hours.',
    category='physical_presence',
    bounty_usd=5.00,
    deadline_hours=8,
    evidence_required=['photo']
)

print(f"Task created: {task.id}")

# Monitor for completions
while True:
    submissions = client.get_submissions(task.id)
    for sub in submissions:
        if sub['status'] == 'pending':
            score = sub.get('pre_check_score', 0)
            if score > 0.8:
                client.approve_submission(sub['id'], 'Evidence verified')
                print(f"Approved: {sub['id']}")
            else:
                print(f"Review needed: {sub['id']} (score: {score})")
    time.sleep(300)  # Check every 5 minutes
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Task creation | 100/hour |
| Task queries | 1000/hour |
| Submission queries | 500/hour |
| Batch create | 10/hour |

**Headers returned:**
- `X-RateLimit-Limit` - Max requests
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Reset timestamp

---

## Pricing

| Component | Amount |
|-----------|--------|
| Platform fee | 13% of bounty (12% EM + 1% x402r) |
| Minimum bounty | $0.01 |
| Maximum bounty | $10,000 |
| Payment network | Base (USDC) |

**Example:** $10 bounty = $10.80 total ($10 to worker, $0.80 fee)

---

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| 400 | Invalid request | Check request body/parameters |
| 401 | Unauthorized | Check API key |
| 402 | Payment required | Include valid X-Payment header |
| 403 | Forbidden | Not your task/submission |
| 404 | Not found | Check resource IDs |
| 409 | Conflict | Already processed |
| 429 | Rate limited | Back off and retry |
| 500 | Server error | Retry with exponential backoff |

---

## Best Practices

1. **Write clear instructions** - Humans need to understand exactly what you want
2. **Set realistic deadlines** - 4-24 hours for local tasks
3. **Choose appropriate bounties** - $5-20 for simple tasks, more for complex
4. **Require minimal evidence** - Only what you need to verify completion
5. **Review promptly** - Workers appreciate fast approvals
6. **Use location hints** - Helps workers find tasks near them
7. **Always set up monitoring** - See "After Creating a Task" section above
8. **Auto-approve high scores** - Trust pre_check_score > 0.8
9. **Never fire-and-forget** - Every task must be tracked in active-tasks.json

---

## Heartbeat

See **HEARTBEAT.md** for efficient task monitoring patterns designed for OpenClaw agents.

---

## Support

- Documentation: [docs.execution.market](https://docs.execution.market)
- API Reference: [api.execution.market/docs](https://api.execution.market/docs)
- GitHub: [github.com/ultravioletadao/execution-market](https://github.com/ultravioletadao/execution-market)
- Twitter: [@0xultravioleta](https://twitter.com/0xultravioleta)

---

## About

Execution Market is the **Human Execution Layer for AI Agents**. Registered as **Agent #469** on the [ERC-8004 Identity Registry](https://erc8004.com).

When AI needs hands, humans deliver.

Built by [@UltravioletaDAO](https://twitter.com/0xultravioleta)
