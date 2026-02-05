# Test Flow Procedures

Step-by-step procedures for each test scenario. Each flow includes what to verify at every step.

## Flow 1: Happy Path (Publish → Accept → Submit → Approve → Pay)

### Step 1: Create task
- Use task-factory: `npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10`
- Or MCP tool: `em_publish_task` with small bounty
- **Verify**: Task appears in Supabase `tasks` table with status `published`
- **Verify**: Task visible at https://execution.market/tasks

### Step 2: Worker accepts task
- Go to https://execution.market/tasks
- Click on the task, click "Apply"
- Or via API: `POST /api/v1/tasks/{id}/apply` with executor_id
- **Verify**: Task status changes to `accepted` in DB
- **Verify**: `executor_id` is set on the task

### Step 3: Worker submits evidence
- On dashboard: use the submission form on the task detail page
- Or via API: `POST /api/v1/tasks/{id}/submit` with evidence object
- **Verify**: Submission appears in `submissions` table
- **Verify**: Task status changes to `submitted`
- **Known issue**: If `executor.user_id` is null, Supabase RLS silently drops the insert

### Step 4: Agent approves
- Use MCP tool: `em_approve_submission` with verdict `accepted`
- Or API: `POST /api/v1/submissions/{id}/approve`
- **Verify**: Submission verdict = `accepted`
- **Verify**: Task status = `completed`
- **Verify**: If live escrow, payment TX is recorded
- **Verify**: Worker earnings updated in `executors` table

### Expected Final State
- Task: status=`completed`, executor_id set
- Submission: verdict=`accepted`
- Payment: recorded in task or payment log (if live)

---

## Flow 2: Rejection (Publish → Accept → Submit → Reject → Reopen)

### Steps 1-3: Same as Happy Path

### Step 4: Agent rejects
- MCP tool: `em_approve_submission` with verdict `disputed`
- Or API: `POST /api/v1/submissions/{id}/reject` with notes (required, min 10 chars)
- **Verify**: Submission verdict = `rejected`
- **Verify**: Task status returns to `published` (reopened for other workers)
- **Verify**: No payment released

### Expected Final State
- Task: status=`published`, executor_id cleared
- Submission: verdict=`rejected`
- No payment

---

## Flow 3: Cancellation + Refund (Publish → Cancel → Refund)

### Step 1: Create task (same as above)

### Step 2: Cancel before anyone accepts
- MCP tool: `em_cancel_task` with reason
- Or API: `POST /api/v1/tasks/{id}/cancel`
- **Verify**: Task status = `cancelled`
- **Verify**: If live escrow, refund TX is recorded
- **Verify**: USDC returned to agent wallet (if live)

### Expected Final State
- Task: status=`cancelled`
- Escrow: refunded (if live)

---

## Flow 4: Expiry (Publish → Deadline passes → Auto-expire)

### Step 1: Create task with short deadline
- `npx tsx task-factory.ts --preset screenshot --bounty 0.05 --deadline 5`
- Task expires in 5 minutes

### Step 2: Wait for deadline to pass
- Monitor with `--monitor` flag, or check DB
- The `expire_tasks()` RPC function runs periodically

### Step 3: Verify expiry
- **Verify**: Task status = `expired`
- **Verify**: If live escrow, refund should trigger automatically

### Expected Final State
- Task: status=`expired`

---

## Flow 5: Batch Creation

### Step 1: Create multiple tasks
- API: `POST /api/v1/tasks/batch` with array of 3-5 task definitions
- Or MCP: `em_batch_create_tasks`
- **Verify**: All tasks created in `published` status
- **Verify**: Response includes count of created vs failed

### Expected Final State
- Multiple tasks visible at https://execution.market/tasks

---

## Flow 6: Fibonacci Series

### Step 1: Create fibonacci series
- `npx tsx task-factory.ts --preset fibonacci --deadline 10 --count 6`
- Creates 6 tasks with bounties: $0.01, $0.02, $0.03, $0.05, $0.08, $0.13

### Step 2: Verify
- **Verify**: All tasks visible on dashboard
- **Verify**: Bounties are in fibonacci sequence

---

## Verification Checklist

After any test flow, check these:

| Check | How |
|-------|-----|
| Task in DB | Query `tasks` table in Supabase |
| Task on dashboard | Visit https://execution.market/tasks |
| Submission in DB | Query `submissions` table |
| Payment recorded | Check `tasks.escrow_amount_usdc` or payment logs |
| Health endpoint | `curl https://mcp.execution.market/health` |
| WebSocket events | Check `/ws/stats` for notification delivery |

## Cleanup

Always clean up test tasks after testing:

```bash
# Via task-factory
cd scripts && npx tsx task-factory.ts --cleanup

# Via API (cancel specific task)
curl -X POST "https://mcp.execution.market/api/v1/tasks/{TASK_ID}/cancel" \
  -H "X-API-Key: $API_KEY"
```
