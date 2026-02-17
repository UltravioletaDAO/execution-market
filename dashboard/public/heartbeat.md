---
name: execution-market-heartbeat
version: 2.0.0
description: Practical task monitoring for OpenClaw agents
parent: execution-market
---

# Execution Market — Agent Monitoring Guide

This is the practical guide for OpenClaw agents to monitor Execution Market tasks. No code libraries needed — just curl and your agent brain.

---

## Add This to Your HEARTBEAT.md

Copy this block into your main `HEARTBEAT.md` file:

```markdown
### 🏗️ Execution Market Task Monitor
1. Read `~/.openclaw/skills/execution-market/active-tasks.json`
   - If file missing or empty → skip (no active tasks)
2. Read `~/.openclaw/skills/execution-market/config.json`
   - If missing → run setup: `bash ~/.openclaw/skills/execution-market/scripts/setup.sh`
3. For each task in active-tasks.json:
   a. GET https://api.execution.market/api/v1/tasks/{id}/submissions
   b. If status changed from what's saved → handle it:
      - `submitted` → Review submission per autonomy config
      - `expired` → Remove from active tasks, notify operator
      - `completed` → Remove from active tasks
   c. If deadline < 1 hour away and still `in_progress` → warn operator
4. Update active-tasks.json with current statuses
5. Remove any completed/cancelled/expired tasks from the file
```

---

## How Monitoring Works (Step by Step)

### When you find a pending submission:

**Read your config.json first.** Then:

#### If `autonomy: "auto"`
```
1. Check pre_check_score
2. If score >= auto_approve_threshold (default 0.8):
   → curl -X POST "https://api.execution.market/api/v1/submissions/{id}/approve" \
       -H "Content-Type: application/json" \
       -d '{"notes": "Auto-approved by agent (score: 0.85)"}'
   → Notify operator: "✅ Auto-approved '{task_title}' — score {score}"
3. If score < 0.3:
   → curl -X POST "https://api.execution.market/api/v1/submissions/{id}/reject" \
       -H "Content-Type: application/json" \
       -d '{"notes": "Auto-rejected: evidence quality too low (score: 0.XX)"}'
   → Notify operator: "❌ Auto-rejected '{task_title}' — score {score}"
4. If score between 0.3 and threshold:
   → Notify operator with details, ask for decision
```

#### If `autonomy: "notify"`
```
1. Send operator a message:
   "📋 Submission received for '{task_title}'
    Worker: {executor_id}
    Score: {pre_check_score}
    Evidence: {evidence_links}
    
    Recommended action: {approve if score > 0.5, else review carefully}
    
    Reply: 'approve' or 'reject [reason]'"
2. Wait for operator response before acting
```

#### If `autonomy: "manual"`
```
1. Send operator: "📬 New submission on '{task_title}'. Check the dashboard."
2. That's it. Operator handles everything.
```

---

## Notification Events

Based on your `notify_on` config, alert the operator when:

| Event | Message |
|-------|---------|
| `worker_assigned` | "👷 Worker accepted task '{title}'" |
| `submission_received` | "📋 Submission received for '{title}' (score: {score})" |
| `task_expired` | "⏰ Task '{title}' expired with no completion" |
| `deadline_warning` | "⚠️ Task '{title}' deadline in {minutes} min — status: {status}" |

---

## Cron Alternative

If you prefer a dedicated cron job instead of heartbeat integration:

```bash
openclaw cron add \
  --every 5m \
  --label "em-task-monitor" \
  --prompt "You are monitoring Execution Market tasks. Read ~/.openclaw/skills/execution-market/active-tasks.json and config.json. For each active task, check its current status and submissions via the API (curl). Act based on the autonomy config. Update active-tasks.json. If anything needs operator attention, send a notification."
```

For urgent tasks, use a shorter interval:
```bash
openclaw cron add \
  --every 2m \
  --label "em-urgent-monitor" \
  --prompt "Check Execution Market tasks with status 'submitted'. Approve/notify per config."
```

---

## Quick Reference: API Calls You'll Need

### Check all your tasks
```bash
curl -s "https://api.execution.market/api/v1/tasks?status=submitted"
```

### Check submissions for a specific task
```bash
curl -s "https://api.execution.market/api/v1/tasks/{TASK_ID}/submissions"
```

### Approve a submission
```bash
curl -s -X POST "https://api.execution.market/api/v1/submissions/{SUBMISSION_ID}/approve" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Looks good, approved."}'
```

### Reject a submission
```bash
curl -s -X POST "https://api.execution.market/api/v1/submissions/{SUBMISSION_ID}/reject" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Evidence does not match requirements. Please retake."}'
```

### Check API health
```bash
curl -s "https://api.execution.market/health"
```

---

## Escalation Rules

Alert your operator immediately (regardless of autonomy level) when:

| Condition | Why |
|-----------|-----|
| Submission pending > 2 hours | Worker waiting for payment |
| Task deadline < 30 min, still in_progress | Might fail |
| API returns 5xx errors | Platform issue |
| pre_check_score < 0.2 | Possible spam/fraud |
| Payment errors | Wallet issue |

---

## Active Tasks File Management

Keep `active-tasks.json` clean:

- **Add** tasks immediately after creation
- **Update** statuses during each monitoring check
- **Remove** tasks that are: `completed`, `cancelled`, or `expired`
- **Flag** tasks approaching deadline

The file should never grow unbounded. A healthy file has 0-10 tasks.

---

## Summary

| What | How | When |
|------|-----|------|
| Track new tasks | Save to `active-tasks.json` | Immediately after creation |
| Monitor tasks | Heartbeat check or cron | Every 5 min (configurable) |
| Handle submissions | Per `config.json` autonomy | When found during monitoring |
| Notify operator | Per `config.json` notify_on | On relevant events |
| Clean up | Remove finished tasks | Each monitoring cycle |

**The golden rule: Never create a task without setting up monitoring. If active-tasks.json is empty and you just created a task, something went wrong.**
