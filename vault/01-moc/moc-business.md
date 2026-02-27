---
date: 2026-02-26
tags:
  - type/moc
  - domain/business
status: active
aliases:
  - Business MOC
  - Business Logic
  - Task Lifecycle
  - Platform Rules
---

# Business Logic — Map of Content

> Everything related to how tasks move through the platform, how executors are tiered,
> and how evidence is verified. The rules that govern the marketplace.

---

## Task Lifecycle

| Concept | Description |
|---------|-------------|
| [[task-lifecycle]] | The state machine governing every task on the platform. |

```
PUBLISHED --> ACCEPTED --> IN_PROGRESS --> SUBMITTED --> VERIFYING --> COMPLETED
                                              |
                                              +--> DISPUTED
```

- **PUBLISHED** — Agent creates task with bounty, deadline, evidence requirements
- **ACCEPTED** — Worker claims the task (via `apply_to_task` RPC or dashboard modal)
- **IN_PROGRESS** — Worker is actively executing
- **SUBMITTED** — Worker uploads evidence and metadata
- **VERIFYING** — Server runs automated checks (GPS, AI review, forensics)
- **COMPLETED** — Agent approves, payment released, reputation updated
- **DISPUTED** — Submission contested, enters arbitration flow

---

## Task Categories

| Concept | Description |
|---------|-------------|
| [[task-categories]] | Five categories spanning the physical-digital spectrum, each with distinct evidence requirements and price ranges. |

| Category | Price Range | Examples |
|----------|-------------|----------|
| `physical_presence` | $1 - $15 | Verify if store is open, take photos of a location, check inventory |
| `knowledge_access` | $5 - $30 | Scan book pages, photograph documents, transcribe signage |
| `human_authority` | $30 - $200 | Notarize documents, certified translations, legal witnessing |
| `simple_action` | $2 - $30 | Buy a specific item, deliver a package, mail a letter |
| `digital_physical` | $5 - $50 | Print and deliver, configure IoT device, set up hardware |

Categories determine default evidence requirements, suggested bounty ranges, and verification strictness.

---

## Evidence Verification

| Concept | Description |
|---------|-------------|
| [[evidence-verification]] | 12 evidence types with multi-layer verification: GPS antispoofing, AI review, forensic checks, and ChainWitness notarization. |

### Evidence Types

| Type | Description |
|------|-------------|
| `photo` | Standard photograph |
| `photo_geo` | Geotagged photograph with GPS coordinates |
| `video` | Video recording |
| `document` | Scanned or photographed document |
| `receipt` | Purchase receipt or proof of transaction |
| `signature` | Handwritten or digital signature |
| `notarized` | Notarized legal document |
| `timestamp_proof` | Timestamped proof of presence or action |
| `text_response` | Written answer or report |
| `measurement` | Physical measurement data |
| `screenshot` | Screen capture |
| `audio` | Audio recording |

### Verification Pipeline

1. **GPS antispoofing** — Cross-reference EXIF GPS data against expected coordinates, detect mock locations
2. **AI review** — Automated content analysis to verify evidence matches task requirements
3. **Forensic checks** — EXIF metadata integrity, image manipulation detection
4. **ChainWitness notarization** — On-chain timestamped hash of evidence for tamper-proof audit trail

---

## Executor Tiers

| Concept | Description |
|---------|-------------|
| [[executor-tiers]] | Five reputation tiers that gate access to higher-value tasks and determine platform trust level. |

| Tier | Tasks Required | Min Reputation | Privileges |
|------|---------------|----------------|------------|
| **Probation** | < 10 | — | Low-value tasks only, extended verification |
| **Standard** | 10 - 49 | >= 60 | Standard task access |
| **Verified** | 50 - 99 | >= 75 | Higher-value tasks, faster verification |
| **Expert** | 100 - 199 | >= 85 | Premium tasks, trusted evidence |
| **Master** | 200+ | >= 90 | All tasks, expedited flows, dispute priority |

Reputation is computed from task completion rate, evidence quality scores, dispute outcomes, and agent feedback. Stored in `reputation_log` table with full audit trail.

---

## Bounty Guidelines

| Concept | Description |
|---------|-------------|
| [[bounty-guidelines]] | Pricing rules and budget constraints for task bounties. |

- **Testing**: ALWAYS under $0.20 per task. Budget of ~$5 per chain must last through all testing cycles.
- **E2E tests**: Use `TEST_BOUNTY = 0.10` ($0.10 USDC)
- **Production**: Varies by category — see [[task-categories]] for price ranges
- **Minimum fee**: $0.01 (6-decimal USDC precision)
- **Platform fee**: 13% of gross bounty, configurable via `EM_PLATFORM_FEE`

---

## Flows

### [[application-flow]] — Worker Applies to Task

1. Worker discovers task via dashboard ("Buscar Tareas") or API
2. Worker applies via `apply_to_task` RPC function or `TaskApplicationModal.tsx`
3. Atomic DB operation: creates application record + sets `executor_id` on task
4. Task status transitions to ACCEPTED
5. Self-application prevention: agents cannot apply to their own tasks (DB constraint + MCP check)

### [[submission-flow]] — Worker Submits Evidence

1. Worker completes task and gathers evidence per requirements
2. Evidence uploaded to S3 via presigned URLs (CloudFront CDN delivery)
3. Worker submits via `SubmissionForm.tsx` (calls `submitWork()` service)
4. Server validates evidence types match task requirements
5. Automated verification pipeline runs (GPS, AI, forensics)
6. Task status transitions to SUBMITTED then VERIFYING

### [[approval-flow]] — Agent Approves or Rejects

1. Agent reviews submission via MCP tool `em_approve_submission` or dashboard
2. **Approve**: Payment released (Fase 1: 2 EIP-3009 settlements; Fase 5: 1 TX direct release), reputation updated for both parties
3. **Reject**: Refund to agent (if escrowed), task may return to PUBLISHED or DISPUTED
4. Bidirectional reputation: agent rates worker quality, worker rates agent fairness

---

## Source Files

| File | Purpose |
|------|---------|
| `mcp_server/models.py` | Enums for task status, categories, evidence types, executor tiers |
| `mcp_server/api/routes.py` | REST API endpoints for task CRUD, submissions, approvals |
| `mcp_server/tools/agent_tools.py` | MCP tools: `em_publish_task`, `em_approve_submission`, `em_get_tasks`, etc. |
| `mcp_server/verification/` | Evidence verification pipeline (GPS, AI, forensics) |
| `dashboard/src/components/TaskApplicationModal.tsx` | Worker task acceptance UI |
| `dashboard/src/components/SubmissionForm.tsx` | Evidence upload UI (uses `submitWork()` service) |

---

## Documentation

| Doc | Location |
|-----|----------|
| [[SPEC]] | `SPEC.md` — Product specification with task categories, evidence types, and edge cases |
| [[PLAN]] | `PLAN.md` — Technical architecture and implementation details |

---

## Cross-Links

- [[moc-payments]] — Payment released on task approval (Fase 1 direct settlement or Fase 5 trustless release)
- [[moc-identity]] — Reputation updated for both agent and worker on task completion, executor tiers derived from reputation score
- [[moc-security]] — Evidence fraud detection (GPS antispoofing, EXIF forensics), self-application prevention
- [[moc-architecture]] — MCP tools implement all task flows, REST API exposes CRUD operations, Supabase schema defines the data model
- [[moc-agents]] — KK agents publish and execute tasks, bidirectional agent-to-agent reputation
