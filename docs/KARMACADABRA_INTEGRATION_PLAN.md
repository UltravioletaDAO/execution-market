# Karma Kadabra → Execution Market: Integration Plan

> Detailed, granular implementation guide to make KK agents the **first clients** of Execution Market.
> Generated: 2026-02-12 | Companion to: `docs/KARMACADABRA_ANALYSIS.md`

---

## Executive Summary

**How hard is this?** Surprisingly feasible. Both projects already share the same facilitator, the same payment protocol (EIP-3009), and similar A2A discovery patterns. The core integration is a **Python SDK adapter** (~200 lines) in the KK `shared/` directory that wraps EM's REST API, letting any KK agent publish tasks and approve submissions with 3-4 lines of code.

**Estimated total effort:** 2-3 weeks for a production-ready MVP.

**What's already shared:**

| Component | Status |
|-----------|--------|
| Facilitator (`facilitator.ultravioletadao.xyz`) | Shared, live |
| EIP-3009 gasless payments | Both use it (GLUE and USDC) |
| A2A discovery protocol | Same concept, trivial mapping |
| AWS infrastructure | Both on AWS (different regions) |
| ERC-8004 identity standard | Both implement it (different registries) |

**What needs to be built:**

| Component | Effort | Side |
|-----------|--------|------|
| EM Client SDK for KK agents | 2-3 days | KK |
| KK agent task pipeline (publish/approve logic) | 3-5 days | KK |
| USDC funding for KK agent wallets | 1 day | Ops |
| Webhook receiver in KK for submission notifications | 2-3 days | KK |
| EM API key provisioning for KK agents | 1 hour | EM |
| Validator-as-Submission-Checker adapter | 2-3 days | KK + EM |
| E2E test suite | 2-3 days | Both |

---

## Table of Contents

1. [Feasibility Assessment](#1-feasibility-assessment)
2. [Integration Architecture](#2-integration-architecture)
3. [Phase 1: EM Client SDK for KK](#3-phase-1-em-client-sdk-for-kk)
4. [Phase 2: KK Agent Task Pipeline](#4-phase-2-kk-agent-task-pipeline)
5. [Phase 3: Webhook & Submission Handling](#5-phase-3-webhook--submission-handling)
6. [Phase 4: Validator Integration](#6-phase-4-validator-integration)
7. [Payment Bridge (GLUE ↔ USDC)](#7-payment-bridge-glue--usdc)
8. [Authentication & Identity](#8-authentication--identity)
9. [Changes Required per Side](#9-changes-required-per-side)
10. [Risk Assessment & Mitigations](#10-risk-assessment--mitigations)
11. [Testing Strategy](#11-testing-strategy)
12. [Timeline & Milestones](#12-timeline--milestones)

---

## 1. Feasibility Assessment

### 1.1 What Makes This Easy

**Same payment protocol.** Both projects use EIP-3009 `transferWithAuthorization()` through the same Ultravioleta Facilitator. The only difference is the token: GLUE (KK) vs USDC (EM). Since EM operates on Base mainnet with USDC, KK agents need USDC in their wallets to pay for EM tasks. This is a funding operation, not a code change.

**Same facilitator.** `facilitator.ultravioletadao.xyz` already handles both projects. No new infrastructure needed.

**EM's Fase 1 mode is perfect for this.** In Fase 1 (EM's default production mode):
- Task creation: only an advisory `balanceOf()` check — no auth signature needed
- Task approval: server signs 2 fresh EIP-3009 auths (agent→worker + agent→treasury)
- Task cancellation: no-op (no funds were locked)

This means KK agents don't need to sign any payment headers at task creation — they just need USDC balance on Base. EM's server handles the payment signing at approval time.

**EM doesn't require API keys by default.** `EM_REQUIRE_API_KEY=false` (current production config) means KK agents can call the API immediately with no provisioning. When auth is disabled, EM uses the platform agent identity (`agent_id: 2106`).

**REST API is fully documented.** EM's `POST /api/v1/tasks`, `GET /api/v1/tasks/{id}/submissions`, and `POST /api/v1/submissions/{id}/approve` are all that KK needs.

### 1.2 What Needs Work

| Challenge | Difficulty | Solution |
|-----------|------------|----------|
| KK agents have GLUE, EM needs USDC | Low | Fund KK agent wallets with USDC on Base mainnet |
| KK is on Base Sepolia, EM is on Base mainnet | Low | KK agents get a second wallet config for mainnet |
| No webhook receiver in KK | Medium | Add FastAPI endpoint to receive EM submission notifications |
| KK agents have no "publish to EM" logic | Medium | New `em_client.py` in KK's `shared/` library |
| Validator needs adapter for EM submissions | Medium | Map EM evidence format to KK validator input |
| Different ERC-8004 registries | Low | Cross-reference by wallet address, not agent ID |

### 1.3 What's NOT Needed (Complexity Avoided)

- **No GLUE↔USDC swap needed** for MVP — just fund KK wallets with USDC directly
- **No protocol changes** to either side — pure API integration
- **No smart contract changes** — both projects' contracts work as-is
- **No facilitator changes** — already shared
- **No new infrastructure** — KK's existing ECS services can call EM's API
- **No changes to EM's payment flow** — Fase 1 handles everything server-side

---

## 2. Integration Architecture

### 2.1 High-Level Flow

```mermaid
sequenceDiagram
    participant KK as KK Agent<br/>(e.g., Skill-Extractor)
    participant EM_API as EM API<br/>(api.execution.market)
    participant Dashboard as EM Dashboard<br/>(execution.market)
    participant Worker as Human Worker
    participant KK_WH as KK Webhook<br/>Receiver
    participant KK_VAL as KK Validator<br/>(CrewAI)

    Note over KK: Agent identifies need for physical-world data
    KK->>EM_API: POST /api/v1/tasks<br/>{title, instructions, bounty_usd, ...}
    EM_API->>EM_API: balanceOf(KK wallet) check
    EM_API-->>KK: 201 {task_id, status: "published"}

    Note over Dashboard: Task appears on worker dashboard
    Worker->>Dashboard: Browse tasks, apply
    Dashboard->>EM_API: POST /api/v1/tasks/{id}/apply
    Worker->>EM_API: POST /api/v1/tasks/{id}/submit<br/>{evidence_urls, text_report, gps}

    EM_API->>KK_WH: POST /webhook<br/>{event: "submission_received", task_id, submission_id}
    KK_WH->>KK: Notify agent: new submission

    KK->>EM_API: GET /api/v1/tasks/{id}/submissions
    KK->>KK_VAL: Validate evidence (Quality + Fraud + Price crews)
    KK_VAL-->>KK: Score: 87/100, PASS

    KK->>EM_API: POST /api/v1/submissions/{id}/approve
    EM_API->>EM_API: Sign 2x EIP-3009 (KK wallet→worker + KK wallet→treasury)
    EM_API->>EM_API: Settle via Facilitator (gasless)
    EM_API-->>KK: 200 {payment_tx: "0x..."}
    EM_API->>Worker: USDC payment received
```

### 2.2 Component Diagram

```mermaid
graph TD
    subgraph "Karmacadabra (us-east-1)"
        SE[Skill-Extractor<br/>Port 9004]
        VE[Voice-Extractor<br/>Port 9005]
        KH[Karma-Hello<br/>Port 9002]
        VAL[Validator<br/>Port 9001]
        EMC[em_client.py<br/>NEW — shared library]
        WH[webhook_receiver.py<br/>NEW — FastAPI endpoint]
    end

    subgraph "Execution Market (us-east-2)"
        API[EM REST API<br/>api.execution.market]
        DB[(Supabase)]
        DASH[Dashboard<br/>execution.market]
    end

    subgraph "Shared Infrastructure"
        FAC[Facilitator<br/>facilitator.ultravioletadao.xyz]
        USDC[USDC on Base Mainnet]
    end

    SE & VE & KH -->|"import"| EMC
    EMC -->|"REST API calls"| API
    API -->|"webhook POST"| WH
    WH -->|"notify"| SE & VE & KH
    SE & VE & KH -->|"validate"| VAL
    API -->|"EIP-3009"| FAC
    FAC -->|"transfer"| USDC
    API -->|"CRUD"| DB
    DASH -->|"read"| DB
```

---

## 3. Phase 1: EM Client SDK for KK

### 3.1 New File: `shared/em_client.py`

A lightweight Python client that wraps EM's REST API. Lives in KK's `shared/` directory so all agents can import it.

**Estimated size:** ~200 lines
**Dependencies:** `httpx` (async HTTP, already in KK's requirements) or `aiohttp`

```python
"""
Execution Market Client for Karmacadabra Agents.

Allows any KK agent to publish tasks on Execution Market,
monitor submissions, and approve/reject completed work.

Usage:
    from em_client import EMClient

    em = EMClient(
        base_url="https://api.execution.market",
        api_key="em_sk_live_xxx"  # Optional if EM_REQUIRE_API_KEY=false
    )

    # Publish a task
    task = await em.publish_task(
        title="Photograph store display at Mall X",
        instructions="Take 3 photos of the main product display...",
        category="physical_presence",
        bounty_usd=0.50,
        deadline_hours=4,
        evidence_required=["photo", "gps_coordinates"],
        location_hint="Bogota, Mall X, 2nd floor"
    )

    # Check for submissions
    submissions = await em.get_submissions(task["id"])

    # Approve with payment
    result = await em.approve_submission(submissions[0]["id"])
    print(f"Payment TX: {result['data']['payment_tx']}")
"""
```

**Methods required:**

| Method | EM Endpoint | Purpose |
|--------|-------------|---------|
| `publish_task(...)` | `POST /api/v1/tasks` | Create task bounty |
| `get_task(task_id)` | `GET /api/v1/tasks/{id}` | Check task status |
| `get_tasks(status=None)` | `GET /api/v1/tasks` | List agent's tasks |
| `get_submissions(task_id)` | `GET /api/v1/tasks/{id}/submissions` | Get worker submissions |
| `approve_submission(id, notes=None)` | `POST /api/v1/submissions/{id}/approve` | Approve + pay |
| `reject_submission(id, reason)` | `POST /api/v1/submissions/{id}/reject` | Reject submission |
| `cancel_task(task_id)` | `POST /api/v1/tasks/{id}/cancel` | Cancel + refund |
| `get_available_tasks()` | `GET /api/v1/tasks/available` | Browse available tasks |

### 3.2 Configuration

New environment variables for KK agents:

```bash
# Execution Market integration
EM_API_URL=https://api.execution.market
EM_API_KEY=em_sk_live_xxx             # Optional for now
EM_WEBHOOK_SECRET=whsec_xxx           # For HMAC verification
EM_DEFAULT_BOUNTY_USD=0.50            # Default bounty for auto-published tasks
EM_DEFAULT_DEADLINE_HOURS=4           # Default deadline
EM_PAYMENT_NETWORK=base               # Base mainnet
EM_ENABLED=true                       # Feature flag to enable/disable
```

### 3.3 Error Handling

The SDK must handle:
- **402 Payment Required**: Agent wallet has insufficient USDC balance
- **400 Bad Request**: Invalid task parameters (bounty too low, etc.)
- **429 Rate Limited**: Back off and retry with exponential backoff
- **503 Service Unavailable**: EM payment service down, queue and retry
- **Network errors**: Timeouts, DNS failures (cross-region call)

### 3.4 File Changes in KK

| File | Change | Lines |
|------|--------|-------|
| `shared/em_client.py` | **NEW** — EM REST API client | ~200 |
| `shared/requirements.txt` | Add `httpx>=0.27.0` (if not present) | 1 |
| `agents/*/main.py` | Import `EMClient`, add task publishing logic | ~30 per agent |
| `docker-compose.yml` | Add EM env vars to agent services | ~10 |
| `terraform/ecs-fargate/main.tf` | Add EM env vars to ECS task definitions | ~10 |

---

## 4. Phase 2: KK Agent Task Pipeline

### 4.1 When Do KK Agents Publish EM Tasks?

Each KK agent has natural trigger points where it needs physical-world data:

| KK Agent | Trigger | EM Task Category | Example |
|----------|---------|------------------|---------|
| **Skill-Extractor** | Processes chat logs, finds user mentions a certification | `knowledge_access` | "Photograph the AWS certification of user @f3l1p3_bx" |
| **Voice-Extractor** | Needs voice sample to verify personality profile | `digital_physical` | "Record a 30-second voice message from user @eljuyan" |
| **Karma-Hello** | Twitch event mentioned in chat, needs confirmation | `physical_presence` | "Verify that the Ethereum meetup is happening at Cafe XYZ" |
| **User Agents** | Comprehensive report needs real-world verification | `human_authority` | "Get a notarized translation of this document" |
| **Validator** | Cross-reference check against physical evidence | `simple_action` | "Buy the product at Store Y and photograph the receipt" |

### 4.2 Implementation Pattern per Agent

```python
# In agents/skill-extractor/main.py

from shared.em_client import EMClient

class SkillExtractorAgent(ERC8004BaseAgent):
    def __init__(self, config):
        super().__init__(...)
        self.em = EMClient(
            base_url=os.getenv("EM_API_URL", "https://api.execution.market"),
            api_key=os.getenv("EM_API_KEY"),
        )

    async def process_chat_log(self, log_data):
        """Process chat log and potentially publish EM task."""
        skills = self._extract_skills(log_data)

        # Check if any skill needs physical verification
        for skill in skills:
            if skill.needs_verification:
                task = await self.em.publish_task(
                    title=f"Verify {skill.name} certification for {skill.user}",
                    instructions=f"Take a photo of the {skill.name} certification...",
                    category="knowledge_access",
                    bounty_usd=0.50,
                    deadline_hours=24,
                    evidence_required=["photo", "text_report"],
                    location_hint=skill.location_hint,
                )
                logger.info(f"Published EM task {task['id']} for {skill.user}")
                self._track_pending_task(task["id"], skill)

    async def handle_em_submission(self, task_id, submission_id):
        """Handle incoming EM submission notification."""
        submissions = await self.em.get_submissions(task_id)
        submission = next(s for s in submissions if s["id"] == submission_id)

        # Use KK Validator for quality check
        score = await self.validator.validate(submission["evidence"])

        if score >= 70:
            result = await self.em.approve_submission(
                submission_id,
                notes=f"Validated by KK Validator. Score: {score}/100"
            )
            logger.info(f"Approved submission {submission_id}, tx: {result['data'].get('payment_tx')}")
        else:
            await self.em.reject_submission(
                submission_id,
                reason=f"Quality score too low: {score}/100. Please re-submit with clearer photos."
            )
```

### 4.3 Task Template Registry

Pre-defined task templates for common KK needs:

```python
# shared/em_task_templates.py

TASK_TEMPLATES = {
    "verify_certification": {
        "category": "knowledge_access",
        "bounty_usd": 0.50,
        "deadline_hours": 48,
        "evidence_required": ["photo", "text_report"],
        "instructions_template": "Photograph the {cert_name} certification belonging to {user}. Include: 1) Full certificate visible, 2) Name clearly readable, 3) Issue date visible.",
    },
    "verify_event": {
        "category": "physical_presence",
        "bounty_usd": 0.30,
        "deadline_hours": 4,
        "evidence_required": ["photo", "gps_coordinates"],
        "instructions_template": "Visit {location} and verify that {event_name} is happening. Take a photo showing the event in progress.",
    },
    "collect_voice_sample": {
        "category": "digital_physical",
        "bounty_usd": 0.20,
        "deadline_hours": 72,
        "evidence_required": ["text_report"],
        "instructions_template": "Record a 30-second voice message from {user} saying: '{prompt}'. Upload the audio file.",
    },
    "purchase_and_verify": {
        "category": "simple_action",
        "bounty_usd": 1.00,
        "deadline_hours": 24,
        "evidence_required": ["photo", "text_report"],
        "instructions_template": "Purchase {item} from {store_name} at {location}. Photograph: 1) The product, 2) The receipt with date/price visible.",
    },
}
```

---

## 5. Phase 3: Webhook & Submission Handling

### 5.1 Webhook Receiver

New FastAPI endpoint in each KK agent (or a shared webhook service):

```python
# shared/em_webhook.py

import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException

async def verify_webhook_signature(request: Request, secret: str) -> dict:
    """Verify HMAC-SHA256 signature from EM webhook."""
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"sha256={expected}", signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return json.loads(body)

def add_webhook_routes(app: FastAPI, handler_callback):
    """Add EM webhook endpoints to an existing FastAPI app."""

    @app.post("/em/webhooks")
    async def em_webhook(request: Request):
        secret = os.getenv("EM_WEBHOOK_SECRET", "")
        payload = await verify_webhook_signature(request, secret)

        event_type = payload.get("event")
        if event_type == "submission_received":
            await handler_callback(
                task_id=payload["task_id"],
                submission_id=payload["submission_id"],
                evidence=payload.get("evidence", {}),
            )
        elif event_type == "task_expired":
            logger.warning(f"EM task expired: {payload['task_id']}")

        return {"received": True}
```

### 5.2 Polling Fallback

If webhooks aren't configured (or for reliability), agents can poll:

```python
# In agent main loop
async def poll_em_submissions(self):
    """Periodically check for new EM submissions."""
    while True:
        try:
            tasks = await self.em.get_tasks(status="submitted")
            for task in tasks:
                submissions = await self.em.get_submissions(task["id"])
                for sub in submissions:
                    if sub["status"] == "pending":
                        await self.handle_em_submission(task["id"], sub["id"])
        except Exception as e:
            logger.error(f"EM poll error: {e}")
        await asyncio.sleep(60)  # Poll every minute
```

### 5.3 EM Webhook Configuration

EM's webhook system uses HMAC-SHA256 signed payloads. Configuration via EM admin API:

```bash
# Register webhook for KK agent
curl -X POST https://api.execution.market/api/v1/webhooks \
  -H "Authorization: Bearer em_sk_live_xxx" \
  -d '{
    "url": "https://skill-extractor.karmacadabra.ultravioletadao.xyz/em/webhooks",
    "events": ["submission_received", "task_expired", "task_cancelled"],
    "secret": "whsec_xxx"
  }'
```

**Note:** If EM's webhook system isn't fully wired yet, polling is the MVP path.

---

## 6. Phase 4: Validator Integration

### 6.1 Evidence Format Mapping

KK's Validator expects a specific input format. EM submissions have a different schema:

```python
# shared/em_evidence_adapter.py

def em_submission_to_kk_validation_input(submission: dict) -> dict:
    """Map EM submission evidence to KK Validator input format."""
    evidence = submission.get("evidence", {})
    return {
        "data_type": "em_submission",
        "source": "execution_market",
        "task_id": submission.get("task_id"),
        "content": {
            "text_report": evidence.get("text_report", ""),
            "photo_urls": evidence.get("photo_urls", []),
            "gps_coordinates": evidence.get("gps_coordinates"),
            "submitted_at": submission.get("created_at"),
            "worker_id": submission.get("executor_id"),
        },
        "expected": {
            "category": submission.get("task_category"),
            "required_evidence": submission.get("evidence_schema", {}).get("required", []),
            "location_hint": submission.get("location_hint"),
        },
    }
```

### 6.2 Validation Scoring for EM

The Validator's 3 crews map naturally to EM submission review:

| KK Crew | EM Application |
|---------|---------------|
| **Quality Crew** | Are all required evidence types present? Photos clear? GPS within range? |
| **Fraud Crew** | Is the photo AI-generated? Is the GPS spoofed? Is the text copy-pasted? |
| **Price Crew** | Was the task completed thoroughly enough to justify the bounty? |

### 6.3 Auto-Approval Threshold

KK agents can set a confidence threshold for auto-approval:

```python
EM_AUTO_APPROVE_THRESHOLD = 80   # Auto-approve if score >= 80
EM_AUTO_REJECT_THRESHOLD = 30    # Auto-reject if score < 30
# Scores 30-79: Queue for manual review (or ask agent's operator)
```

---

## 7. Payment Bridge (GLUE ↔ USDC)

### 7.1 MVP: Direct USDC Funding (No Swap Needed)

For the MVP, **no token swap is needed.** Simply fund KK agent wallets with USDC on Base mainnet:

```bash
# Fund KK system agents with USDC on Base mainnet
# Each agent needs enough for ~10-20 test tasks at $0.50 each = ~$5-10

# From Execution Market treasury or a funded wallet:
# Send USDC to each KK agent's Base mainnet wallet

# KK Agent wallets (same addresses on Base mainnet as Base Sepolia):
# Validator:        0x1219eF9484BF7E40E6479141B32634623d37d507
# Karma-Hello:      0x2C3e071df446B25B821F59425152838ae4931E75
# Skill-Extractor:  0xC1d5f7478350eA6fb4ce68F4c3EA5FFA28C9eaD9
# Voice-Extractor:  0x8E0Db88181668cDe24660d7eE8Da18a77DdBBF96
```

**Why this works:** KK agent wallets are standard EOAs. Their private keys (in AWS Secrets Manager) work on any EVM chain. The same wallet that holds GLUE on Base Sepolia can hold USDC on Base mainnet.

**Cost for MVP testing:** ~$20-50 USDC total (enough for 40-100 test tasks).

### 7.2 Future: Automated GLUE→USDC Bridge

For production, agents could auto-swap when they need to publish EM tasks:

1. Agent earns GLUE from data sales → accumulates balance
2. When agent needs to publish EM task → calls DEX (e.g., Uniswap on Base) to swap GLUE→USDC
3. Publishes EM task with USDC bounty

**This requires:** GLUE liquidity pool on Base mainnet + DEX integration. Not needed for MVP.

### 7.3 Fee Economics

| Item | Cost | Paid By |
|------|------|---------|
| EM task bounty | $0.10-$1.00 | KK agent (USDC) |
| EM platform fee | 13% of bounty | KK agent (USDC) |
| Facilitator gas | Free | Facilitator absorbs |
| KK data sale revenue | 0.01-0.50 GLUE | Paid by data buyers |

**Example economics for Skill-Extractor:**
- Buys chat log from Karma-Hello: 0.01 GLUE (~$0.001)
- Needs photo verification: publishes EM task at $0.50 + 13% = $0.565 total
- Sells enriched profile: 0.50 GLUE (~$0.05)
- **Net per verified profile:** -$0.51 in USDC + 0.49 GLUE profit

This shows that KK agents publishing EM tasks is an **expense** for the agent, justified by the value of the physical-world data received. The agent economy needs the GLUE value to exceed the USDC cost for sustainability.

---

## 8. Authentication & Identity

### 8.1 Current State (No Auth Required)

EM currently runs with `EM_REQUIRE_API_KEY=false`. This means:
- All API endpoints accept unauthenticated requests
- Requests are attributed to the platform agent (ID: 2106)
- KK agents can start calling the API immediately

**For MVP:** This is fine. All tasks are attributed to EM's platform agent.

### 8.2 With API Keys (Recommended for Production)

For proper attribution, each KK agent should have its own EM API key:

```sql
-- Create API key for KK Skill-Extractor
INSERT INTO api_keys (key_hash, agent_id, tier, organization_id, description)
VALUES (
    sha256('em_sk_live_kk_skill_extractor_xxx'),
    'kk_skill_extractor',
    'starter',
    'ultravioleta_kk',
    'Karmacadabra Skill-Extractor agent'
);
```

**Benefits:**
- Tasks attributed to specific KK agents (not generic platform agent)
- Rate limiting per agent
- Analytics: which KK agent publishes the most tasks
- Revocation if needed

### 8.3 ERC-8004 Cross-Registry Identity

Both projects have ERC-8004 registries, but on different contracts:

| Project | Registry | Network | Agent IDs |
|---------|----------|---------|-----------|
| KK | `0x8a20f665...` (custom) | Base Sepolia | 1-54 |
| EM | `0x8004A169...` (CREATE2) | Base Mainnet | 2106 |

**Cross-referencing:** By wallet address, not agent ID. When KK agent `0xC1d5f747...` calls EM's API, EM can look up the wallet in KK's registry to verify it's a registered KK agent.

**Implementation:** Add optional `X-ERC8004-Registry` header that tells EM which registry to check:

```python
# In em_client.py
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "X-ERC8004-Registry": "0x8a20f665c02a33562a0462a0908a64716Ed7463d",
    "X-ERC8004-Network": "base-sepolia",
    "X-ERC8004-Agent-ID": str(self.agent.agent_id),
}
```

---

## 9. Changes Required per Side

### 9.1 Changes in Karmacadabra (KK Side)

| # | File | Change Type | Description | Lines |
|---|------|-------------|-------------|-------|
| 1 | `shared/em_client.py` | **NEW** | EM REST API client (publish, approve, cancel, poll) | ~200 |
| 2 | `shared/em_webhook.py` | **NEW** | Webhook receiver + HMAC verification | ~60 |
| 3 | `shared/em_task_templates.py` | **NEW** | Pre-defined task templates for common KK needs | ~80 |
| 4 | `shared/em_evidence_adapter.py` | **NEW** | Map EM submission format → KK Validator input | ~40 |
| 5 | `agents/skill-extractor/main.py` | **MODIFY** | Add EM task publishing + submission handling | +30 |
| 6 | `agents/voice-extractor/main.py` | **MODIFY** | Add EM task publishing + submission handling | +30 |
| 7 | `agents/karma-hello/main.py` | **MODIFY** | Add EM task publishing (event verification) | +20 |
| 8 | `agents/validator/main.py` | **MODIFY** | Add `/validate-em-submission` endpoint | +40 |
| 9 | `docker-compose.yml` | **MODIFY** | Add EM env vars to all agent services | +15 |
| 10 | `terraform/ecs-fargate/main.tf` | **MODIFY** | Add EM env vars to ECS task definitions | +10 |
| 11 | `shared/contracts_config.py` | **MODIFY** | Add Base mainnet USDC config for EM payments | +10 |
| 12 | `.env.example` | **MODIFY** | Document EM integration env vars | +8 |

**Total KK changes:** ~4 new files (~380 lines), ~7 modified files (~163 lines)

### 9.2 Changes in Execution Market (EM Side)

| # | File | Change Type | Description | Lines |
|---|------|-------------|-------------|-------|
| 1 | None required for MVP | — | EM's existing API handles everything | 0 |

**For enhanced integration (optional):**

| # | File | Change Type | Description | Lines |
|---|------|-------------|-------------|-------|
| 1 | `api/routes.py` | **MODIFY** | Add `X-KK-Validator-Score` header passthrough on approval | +10 |
| 2 | `config/platform_config.py` | **MODIFY** | Add `feature.kk_validation_enabled` flag | +5 |
| 3 | `supabase/migrations/031_kk_integration.sql` | **NEW** | Add `kk_validator_score` column to submissions | ~10 |
| 4 | `api/reputation.py` | **MODIFY** | Cross-reference KK registry for agent identity | +20 |

**Total EM changes for MVP:** Zero. The existing API works as-is.
**Total EM changes for enhanced:** ~4 files, ~45 lines.

### 9.3 Operational Changes

| # | Task | Side | Effort |
|---|------|------|--------|
| 1 | Fund KK agent wallets with USDC on Base mainnet | Ops | 30 min |
| 2 | Generate EM API keys for KK agents (optional) | Ops | 15 min |
| 3 | Configure webhook URLs in EM (optional) | Ops | 15 min |
| 4 | Add `EM_*` env vars to KK ECS task definitions | Ops | 30 min |
| 5 | Test end-to-end flow on production | QA | 2-3 hours |

---

## 10. Risk Assessment & Mitigations

### 10.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cross-region latency (us-east-1 → us-east-2) | Low | Low | ~20ms added latency, negligible for task workflows |
| EM API downtime | Low | Medium | Polling with retry + local task queue in KK agent |
| USDC balance depletion on KK wallets | Medium | High | Balance monitoring alert + auto-top-up from treasury |
| Webhook delivery failure | Medium | Low | Polling fallback (every 60s) handles missed webhooks |
| Rate limiting on EM API | Low | Low | KK agents publish ~1-5 tasks/hour, well within limits |

### 10.2 Economic Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| KK tasks go unfulfilled (no workers) | High (early) | High | Start with Bogota-area tasks, recruit local workers |
| Bounties too low for worker interest | Medium | High | A/B test $0.20 vs $0.50 vs $1.00 bounties |
| Fraudulent submissions waste KK budget | Medium | Medium | KK Validator auto-reject + min reputation requirement |
| GLUE value insufficient to cover USDC costs | High | Medium | Direct USDC funding for MVP, economic model needs validation |

### 10.3 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Private key leak for KK agents on mainnet | Low | Critical | AWS Secrets Manager, separate testnet/mainnet keys |
| Wrong network (Sepolia vs mainnet) confusion | Medium | Medium | Explicit `EM_PAYMENT_NETWORK=base` env var, no defaults |
| EM API breaking changes | Low | Medium | Version pinning, SDK handles gracefully |

---

## 11. Testing Strategy

### 11.1 Test Phases

```
Phase A: Unit Tests (KK side)
├── Test em_client.py against mock EM API
├── Test em_webhook.py signature verification
├── Test em_evidence_adapter.py format mapping
└── Test em_task_templates.py template rendering

Phase B: Integration Tests (Both sides, testnet)
├── KK agent → EM API (create task, verify response)
├── EM → KK webhook (send notification, verify receipt)
├── Full cycle: publish → submit (manual) → approve
└── Error cases: insufficient balance, expired task, rejected submission

Phase C: E2E Tests (Production, small bounties)
├── Skill-Extractor publishes $0.10 task on EM
├── Manual worker submits evidence
├── KK Validator scores submission
├── Agent auto-approves, payment settles
└── Verify USDC transfer on-chain (Base mainnet)
```

### 11.2 Test Budget

- Phase A: $0 (mocked)
- Phase B: $0 (testnet)
- Phase C: ~$5 USDC (10 test tasks at $0.50 each)

### 11.3 Test Script

```bash
# E2E test: KK Skill-Extractor publishes task on EM
cd karmacadabra
python -m pytest shared/tests/test_em_integration.py -v

# Manual test flow:
# 1. Run: python scripts/test_em_publish.py
# 2. Open execution.market, find the task
# 3. Submit evidence manually
# 4. Watch KK agent auto-approve in logs
# 5. Verify USDC transfer on basescan.org
```

---

## 12. Timeline & Milestones

### Week 1: Foundation

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Write `shared/em_client.py` | EM REST API client with all methods |
| 1 | Write `shared/em_task_templates.py` | 4-5 task templates |
| 2 | Write unit tests for em_client | 15+ tests passing |
| 2 | Write `shared/em_webhook.py` | Webhook receiver with HMAC |
| 3 | Integrate into Skill-Extractor | First agent publishes EM tasks |
| 3 | Fund KK wallets with USDC | 5 wallets funded on Base mainnet |

**Milestone 1:** Skill-Extractor can publish a task on EM and see it on the dashboard.

### Week 2: Full Pipeline

| Day | Task | Deliverable |
|-----|------|-------------|
| 4 | Write `shared/em_evidence_adapter.py` | Format mapping for Validator |
| 4 | Add `/validate-em-submission` to Validator | Validator scores EM evidence |
| 5 | Implement submission polling in agents | Agents detect new submissions |
| 5 | Implement auto-approve/reject logic | End-to-end automated flow |
| 6 | Integrate Voice-Extractor and Karma-Hello | 3 agents publishing EM tasks |
| 6 | Integration tests (all agents → EM) | Full suite passing |

**Milestone 2:** 3 KK agents autonomously publish, review, and pay for EM tasks.

### Week 3: Production & Polish

| Day | Task | Deliverable |
|-----|------|-------------|
| 7 | E2E tests on production ($0.10 bounties) | Verified payment on-chain |
| 7 | Balance monitoring + alerts | CloudWatch alarm for low USDC |
| 8 | Deploy to ECS (all agents updated) | Live on production |
| 8 | Documentation + runbook | Ops guide for monitoring |
| 9 | Performance testing (10 concurrent tasks) | Latency and reliability metrics |
| 10 | Bug fixes + polish | Ready for demo |

**Milestone 3:** KK agents are live on Execution Market as the first autonomous clients.

---

## Appendix A: API Call Examples

### A.1 Create Task (KK → EM)

```bash
curl -X POST https://api.execution.market/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer em_sk_live_kk_skill_extractor" \
  -d '{
    "title": "Photograph AWS certification",
    "instructions": "Find and photograph the AWS Solutions Architect certification belonging to user f3l1p3_bx. Requirements:\n1. Full certificate must be visible\n2. Name clearly readable\n3. Issue date visible\n4. Certificate number visible",
    "category": "knowledge_access",
    "bounty_usd": 0.50,
    "deadline_hours": 48,
    "evidence_required": ["photo", "text_report"],
    "location_hint": "Bogota, Colombia",
    "min_reputation": 30,
    "payment_token": "USDC",
    "payment_network": "base"
  }'
```

**Response:**
```json
{
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "Photograph AWS certification",
    "status": "published",
    "category": "knowledge_access",
    "bounty_usd": 0.50,
    "deadline": "2026-02-14T12:00:00Z",
    "created_at": "2026-02-12T12:00:00Z",
    "agent_id": "kk_skill_extractor",
    "payment_network": "base",
    "payment_token": "USDC"
}
```

### A.2 Get Submissions (KK ← EM)

```bash
curl https://api.execution.market/api/v1/tasks/a1b2c3d4.../submissions \
  -H "Authorization: Bearer em_sk_live_kk_skill_extractor"
```

### A.3 Approve Submission (KK → EM)

```bash
curl -X POST https://api.execution.market/api/v1/submissions/xyz.../approve \
  -H "Authorization: Bearer em_sk_live_kk_skill_extractor" \
  -H "Content-Type: application/json" \
  -d '{"notes": "KK Validator score: 87/100. All evidence requirements met."}'
```

---

## Appendix B: Decision Log

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| **MVP: No token swap** | Direct USDC funding is simpler, faster, proven | GLUE→USDC DEX swap (adds complexity, needs liquidity) |
| **Polling over webhooks for MVP** | Works without EM webhook infrastructure | Webhooks (faster but needs configuration) |
| **em_client.py in KK shared/** | All agents share the same client | Per-agent client (duplication), MCP tools (more complex) |
| **Fase 1 payment mode** | No auth signing needed at task creation, server handles payment | Fase 2 (adds escrow complexity), preauth (requires X-Payment header) |
| **No EM code changes for MVP** | EM's existing API is sufficient | Custom KK endpoints in EM (premature optimization) |
| **Validator integration optional** | Core flow works without AI validation | Mandatory validation (blocks basic testing) |
| **Base mainnet only** | Both projects converge on Base, simplest path | Multi-chain (adds complexity for no MVP benefit) |
