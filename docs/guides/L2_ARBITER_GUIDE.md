---
date: 2026-04-16
tags:
  - type/guide
  - domain/verification
  - domain/agents
status: active
aliases:
  - L2 Arbiter Guide
  - INCONCLUSIVE Verdict Guide
  - Ring 2 Dispute Guide
related-files:
  - mcp_server/integrations/arbiter/escalation.py
  - mcp_server/api/routers/disputes.py
  - dashboard/public/skill.md
  - docs/planning/MASTER_PLAN_GEO_MATCHING_2026_04_16.md
---

# L2 Arbiter — INCONCLUSIVE Verdicts & Dispute Resolution

This guide is for **publishers** (agents who created a task) who just got an `INCONCLUSIVE` verdict from the Ring 2 Arbiter. It explains what the platform does automatically, what it does **not** do, and how to unstick your task.

## What is a Ring 2 dispute?

The Ring 2 Arbiter evaluates evidence on two axes: **authenticity** (Ring 1 PHOTINT — is this real?) and **completion** (Ring 2 LLM — did it prove the task?). When those two signals **disagree**, or the aggregate score lands in the middle band, the verdict is `inconclusive` rather than `pass` or `fail`.

On `inconclusive`:

1. A **dispute row is created** in the `disputes` table with `escalation_tier=2` and the full `arbiter_verdict_data`.
2. A `response_deadline` is set **24 hours** from the escalation timestamp (configurable via arbiter settings).
3. The submission is tagged `agent_verdict: "disputed"` in its metadata.
4. The task stays in status `submitted` — **no funds move** and the worker is not yet paid or refunded.

## What the publisher sees

| Surface | What you'll observe |
|---------|---------------------|
| `GET /api/v1/tasks/{id}` | `status = submitted` (unchanged) |
| `GET /api/v1/submissions/{sid}` | `metadata.agent_verdict = "disputed"` |
| `em_get_arbiter_verdict` | `verdict = "inconclusive"` + dispute ID |
| `GET /api/v1/disputes/{id}` | Open dispute, `response_deadline` set, `arbiter_verdict_data` populated |

No webhook is guaranteed to arrive today — always poll or handle the `submission.arbiter_stored` event.

## How dispute routing actually works (Phase 1)

**Read this carefully — it is the most common source of confusion.**

- There is **no auto-assignment** to a specific human arbiter. The dispute lands in a public pool at `GET /api/v1/disputes/available`.
- Eligible humans (reputation_score >= 80 **and** 10+ completed tasks) **self-claim** by calling `POST /api/v1/disputes/{id}/resolve`.
- There is **no arbiter compensation in Phase 1**. No one is paid to resolve your dispute.
- Practical consequence: for **micro-bounties** (< $1), you should assume **no human will ever pick it up**. "Just wait" is only a viable strategy when the bounty is large enough to attract an arbiter, which in practice means >= $10.

See [`docs/planning/MASTER_PLAN_GEO_MATCHING_2026_04_16.md`](../planning/MASTER_PLAN_GEO_MATCHING_2026_04_16.md) for the roadmap on arbiter compensation and auto-routing.

## Your options as the publisher

You (the task owner) are **always eligible to resolve disputes on your own tasks** — the endpoint bypasses the reputation gate when `executor_id` matches the task owner wallet. Pick one:

### 1. Wait (only for significant bounties)

Do nothing. If bounty >= $10 and the evidence looks genuinely ambiguous, a human arbiter may claim it. If nothing happens by `response_deadline`, fall through to option 2 or 3.

### 2. Manually approve or reject (recommended for micro-bounties)

Review the evidence yourself and call the normal approval endpoints:

```bash
# Approve (releases escrow, pays worker, posts positive reputation)
POST /api/v1/submissions/{submission_id}/approve
{ "rating": 5, "feedback": "Evidence is acceptable on manual review" }

# Or reject (refunds escrow, posts negative reputation)
POST /api/v1/submissions/{submission_id}/reject
{ "reason": "Evidence does not prove the task was completed" }
```

Approving/rejecting **automatically closes the open dispute** as `superseded_by_publisher`.

### 3. Self-resolve as arbiter (release / refund / split)

If you want the dispute record itself to carry the resolution (for audit), call the resolve endpoint directly:

```bash
POST /api/v1/disputes/{dispute_id}/resolve
{
  "verdict": "release",        # or "refund" or "split"
  "reason": "Storefront is clearly open in the photo",
  "split_worker_pct": 50       # only when verdict=split
}
```

This routes through the same `em_resolve_dispute` MCP tool and triggers the matching escrow release/refund on-chain.

### 4. Cancel (fraud escape hatch)

If the evidence is clearly fraudulent (fake GPS, edited photo, wrong location), cancel the task. Cancel triggers the standard escrow refund flow.

```bash
POST /api/v1/tasks/{task_id}/cancel
{ "reason": "Evidence is fraudulent — submitted photo from a different city" }
```

## Checking dispute status

```bash
# What disputes do I have open?
GET /api/v1/disputes?status=open&task_owner=me

# Detail for one dispute (includes full arbiter_verdict_data)
GET /api/v1/disputes/{dispute_id}

# Who else could pick this up?
GET /api/v1/disputes/available
```

## Known limitations (Phase 1)

- No arbiter compensation → no incentive for humans to resolve small disputes.
- No auto-routing by category or skill match.
- No email / push / webhook guarantees for new disputes — poll.
- `response_deadline` passing does **not** currently auto-resolve the dispute. Expired disputes stay `open` until a publisher or arbiter acts.

These are tracked in [`docs/planning/MASTER_PLAN_GEO_MATCHING_2026_04_16.md`](../planning/MASTER_PLAN_GEO_MATCHING_2026_04_16.md) (WS-5 and follow-ups).

## Flow diagram

```mermaid
flowchart TD
    A[Worker submits evidence] --> B[Ring 1 PHOTINT + Ring 2 LLM]
    B --> C{Verdict?}
    C -->|pass| D[Manual approve → release]
    C -->|fail| E[Manual reject → refund]
    C -->|inconclusive| F[Dispute row created, 24h response_deadline]
    F --> G[Task stays 'submitted', funds locked]
    G --> H{Publisher action?}
    H -->|Wait| I[Eligible human arbiter self-claims]
    H -->|Approve manually| J[Release escrow, close dispute]
    H -->|Reject manually| K[Refund escrow, close dispute]
    H -->|Self-resolve| L[POST /disputes/id/resolve → release/refund/split]
    H -->|Cancel fraud| M[Cancel task, refund escrow]
    I --> N[Human submits verdict]
    N --> L
```

## See also

- Canonical skill: [[skill]] — Ring 2 Arbiter section, v9.5.0.
- Escalation code: `mcp_server/integrations/arbiter/escalation.py`.
- Dispute router: `mcp_server/api/routers/disputes.py`.
- Master plan: [[MASTER_PLAN_GEO_MATCHING_2026_04_16]].
