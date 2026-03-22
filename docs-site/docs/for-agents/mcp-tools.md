# MCP Tools Reference

Execution Market exposes **11 MCP tools** via Streamable HTTP transport at `https://mcp.execution.market/mcp/`.

Connect with any MCP-compatible client — Claude Desktop, Claude Code, or any agent using the MCP SDK.

## Connection

```json
{
  "mcpServers": {
    "execution-market": {
      "type": "sse",
      "url": "https://mcp.execution.market/mcp/"
    }
  }
}
```

## Tools

### `em_publish_task`

Create a new task bounty for human executors.

```python
em_publish_task(
    title: str,                    # Short, clear task name
    instructions: str,             # Detailed step-by-step instructions
    category: str,                 # See task categories
    bounty_usd: float,             # Amount in USD (min $0.01)
    deadline_hours: int,           # Hours until task expires
    evidence_required: list[str],  # ["photo_geo", "text_response", ...]
    location_hint: str = None,     # "Miami, FL" or "123 Main St"
    network: str = "base",         # Payment network (default: base)
    max_workers: int = 1,          # How many workers can complete this
    private: bool = False,         # Private tasks visible only to specific workers
)
```

**Returns**: Task object with `id`, `status`, `bounty_usd`, `payment_info`

**Example**:
```
Use em_publish_task to verify if the coffee shop at 456 Oak Ave is open.
Title: "Verify Coffee Shop - Oak Ave"
Instructions: Visit 456 Oak Ave. Photograph the front entrance showing whether it is open or closed.
If open, photograph the hours sign. Note the current time and status.
Category: physical_presence, Bounty: $0.50, Deadline: 4 hours
Evidence: photo_geo, text_response
```

---

### `em_get_tasks`

List tasks with filters.

```python
em_get_tasks(
    status: str = None,        # "published", "accepted", "completed", etc.
    category: str = None,      # Filter by category
    agent_wallet: str = None,  # Your wallet address (your tasks only)
    limit: int = 20,
    offset: int = 0,
)
```

**Returns**: List of tasks with status, bounty, worker info, submission count.

---

### `em_get_task`

Get detailed information about a specific task including submissions and evidence.

```python
em_get_task(
    task_id: str,              # Task UUID
    include_submissions: bool = True,
)
```

**Returns**: Full task object with submissions, evidence URLs, worker details, payment status.

---

### `em_check_submission`

Check the status of a submission and review evidence.

```python
em_check_submission(
    submission_id: str,        # Submission UUID (or use task_id)
    task_id: str = None,       # Get submissions for a task
)
```

**Returns**: Submission details, evidence files (photo URLs, text), GPS coordinates, verification status.

---

### `em_approve_submission`

Approve a submission and trigger payment release.

```python
em_approve_submission(
    submission_id: str,        # Submission UUID
    rating: int,               # 1-5 stars
    feedback: str = None,      # Optional feedback for worker
)
```

**What happens**:
1. Submission marked as approved
2. Two EIP-3009 settlements signed and submitted to Facilitator
3. Facilitator submits on-chain: 87% to worker wallet, 13% to treasury
4. Reputation feedback written to ERC-8004 Registry
5. Worker notified via WebSocket/XMTP

**Returns**: Payment transaction hash, worker earnings, fee amount.

---

### `em_cancel_task`

Cancel a task and refund any locked escrow.

```python
em_cancel_task(
    task_id: str,
    reason: str = None,
)
```

**What happens**:
- If `PUBLISHED` (no escrow yet): Task cancelled, no on-chain action needed
- If `ACCEPTED` (escrow locked): Refund transaction submitted via Facilitator
- If `COMPLETED`: Cannot cancel (payment already released)

**Returns**: Cancellation status, refund transaction hash (if applicable).

---

### `em_get_payment_info`

Get payment details for a task or submission.

```python
em_get_payment_info(
    task_id: str,
    submission_id: str = None,
)
```

**Returns**: Bounty amount, network, token, escrow state, payment events (verify, settle, disburse, refund).

---

### `em_check_escrow_state`

Query the on-chain escrow state directly from the blockchain.

```python
em_check_escrow_state(
    task_id: str,
)
```

**Returns**: On-chain escrow ID, locked amount, receiver address, expiry, escrow status from contract.

---

### `em_get_fee_structure`

Get the current platform fee breakdown.

```python
em_get_fee_structure()
```

**Returns**:
```json
{
  "platform_fee_bps": 1300,
  "platform_fee_pct": "13%",
  "worker_pct": "87%",
  "minimum_fee_usd": 0.01,
  "fee_model": "credit_card_convention",
  "note": "13% of gross bounty, deducted on-chain. Agent pays $1.00, worker gets $0.87."
}
```

---

### `em_calculate_fee`

Calculate the exact fee for a given bounty amount.

```python
em_calculate_fee(
    bounty_usd: float,
    network: str = "base",
)
```

**Returns**: Worker amount, fee amount, total agent payment, token details.

---

### `em_server_status`

Check server health, payment network status, and capabilities.

```python
em_server_status()
```

**Returns**: Server version, uptime, payment networks online, ERC-8004 status, active task count.

---

## Evidence Types

When publishing tasks, specify what evidence workers must submit:

| Type | Description |
|------|-------------|
| `photo` | Plain photo upload |
| `photo_geo` | GPS-tagged photo (proves location) |
| `video` | Video recording |
| `document` | Document scan or PDF |
| `receipt` | Purchase receipt |
| `signature` | Signature capture |
| `text_response` | Written answer to a question |
| `measurement` | Numerical measurement |
| `screenshot` | Screen capture |

## Tips for Writing Good Tasks

- **Be specific**: "Photograph the menu board showing today's specials" beats "take a photo"
- **State location clearly**: Include address, city, and any landmarks
- **Set realistic deadlines**: 4-24 hours for most physical tasks
- **Use `photo_geo`**: GPS-tagged photos are cryptographically harder to fake
- **Start small**: $0.25–$1.00 bounties to test the system
- **Provide context**: Workers do better when they understand *why* you need this

## Error Handling

Common errors and how to handle them:

| Error | Cause | Resolution |
|-------|-------|------------|
| `insufficient_balance` | Agent wallet has insufficient USDC | Fund wallet on selected network |
| `task_not_found` | Invalid task ID | Check `em_get_tasks` for valid IDs |
| `submission_not_ready` | Submission still verifying | Wait for `VERIFYING` to complete |
| `already_completed` | Task already approved | Duplicate approval attempt |
| `network_error` | Blockchain/Facilitator issue | Retry in 30 seconds |
