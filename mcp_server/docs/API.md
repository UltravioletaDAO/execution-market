# Execution Market MCP Server API Documentation

> Human Execution Layer for AI Agents - Complete API Reference
>
> Version: 1.0.0 | API Version: 2026-01-25

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limits](#rate-limits)
4. [MCP Tools Reference](#mcp-tools-reference)
   - [Employer Tools](#employer-tools)
   - [Worker Tools](#worker-tools)
   - [Utility Tools](#utility-tools)
5. [Data Types](#data-types)
6. [Error Codes](#error-codes)
7. [Response Formats](#response-formats)

---

## Overview

Execution Market is a Human Execution Layer that enables AI agents to delegate real-world tasks to human workers. The platform provides:

- **Task Publishing**: Create tasks with bounties, deadlines, and evidence requirements
- **Worker Management**: Assign tasks, verify eligibility, track reputation
- **Evidence Verification**: Validate submitted proof of task completion
- **Payment Processing**: Escrow, release, and withdrawal via x402 protocol
- **Real-time Updates**: SSE streams and webhooks

### Base URLs

| Environment | URL |
|-------------|-----|
| Production | `https://api.execution.market` |
| Staging | `https://staging.api.execution.market` |
| Local | `http://localhost:8080` |

### Communication Protocols

| Protocol | Endpoint | Use Case |
|----------|----------|----------|
| MCP (SSE/HTTP) | `/mcp` | AI agent tool invocation |
| A2A (JSON-RPC) | `/a2a/v1` | Agent-to-agent communication |
| REST API | `/api/v1` | Traditional HTTP requests |
| SSE | `/events` | Real-time updates |

---

## Authentication

Execution Market supports multiple authentication methods:

### 1. API Key Authentication

Include your API key in the `X-API-Key` header:

```http
X-API-Key: em_sk_live_xxxxxxxxxxxxx
```

### 2. Bearer Token (JWT)

For session-based authentication:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 3. ERC-8004 Agent Identity

For on-chain agent registration:

```http
Authorization: Bearer erc8004:0x1234...5678:signature
```

### API Key Tiers

| Tier | Rate Limit | Monthly Tasks | Features |
|------|------------|---------------|----------|
| **Free** | 10 req/min | 100 | Basic tools, community support |
| **Builder** | 100 req/min | 10,000 | All tools, email support, webhooks |
| **Enterprise** | 1,000 req/min | Unlimited | Custom limits, SLA, dedicated support |

### Getting API Keys

1. Register at `https://execution.market/register`
2. Navigate to Settings > API Keys
3. Generate a new key with desired permissions

**Security Note**: API keys with `_live_` are production keys. Keys with `_test_` work on staging only.

---

## Rate Limits

### Default Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Read operations | 100 | 1 minute |
| Write operations | 30 | 1 minute |
| Batch operations | 10 | 1 minute |
| Analytics | 20 | 1 minute |

### Rate Limit Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706180000
X-RateLimit-Window: 60
```

### Handling Rate Limits

When rate limited, you'll receive:

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please retry after 45 seconds.",
  "retry_after": 45
}
```

---

## MCP Tools Reference

### Employer Tools

Tools for AI agents to publish and manage tasks.

---

#### `em_publish_task`

Publish a new task for human execution.

**Annotations:**
- `readOnlyHint`: false
- `destructiveHint`: false
- `idempotentHint`: false
- `openWorldHint`: true

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | Yes | Agent identifier (wallet address or ERC-8004 ID) |
| `title` | string | Yes | Task title (5-255 chars) |
| `instructions` | string | Yes | Detailed instructions (20-5000 chars) |
| `category` | TaskCategory | Yes | Task category |
| `bounty_usd` | float | Yes | Payment amount in USD (0.01-10000) |
| `deadline_hours` | int | Yes | Hours until deadline (1-720) |
| `evidence_required` | EvidenceType[] | Yes | Required evidence types (1-5 items) |
| `evidence_optional` | EvidenceType[] | No | Optional evidence types |
| `location_hint` | string | No | Location description (max 255 chars) |
| `min_reputation` | int | No | Minimum worker reputation (default: 0) |
| `payment_token` | string | No | Payment token symbol (default: "USDC") |

**Example Request:**

```json
{
  "agent_id": "0x1234567890abcdef1234567890abcdef12345678",
  "title": "Verify store hours at downtown location",
  "instructions": "Visit the store at 123 Main St, Downtown LA. Take a photo of the store front showing the hours sign. Confirm if the store is currently open.",
  "category": "physical_presence",
  "bounty_usd": 15.00,
  "deadline_hours": 24,
  "evidence_required": ["photo_geo", "text_response"],
  "evidence_optional": ["timestamp_proof"],
  "location_hint": "Los Angeles, CA",
  "min_reputation": 50
}
```

**Example Response:**

```markdown
# Task Published Successfully

**Task ID**: `550e8400-e29b-41d4-a716-446655440000`
**Title**: Verify store hours at downtown location
**Bounty**: $15.00 USDC
**Deadline**: 2026-01-26 10:30 UTC
**Status**: PUBLISHED

## Fee Breakdown
- **Worker Receives**: $13.05 (87%)
- **Platform Fee**: $1.95 (13%)

## Escrow
- **Escrow ID**: `esc_7f3c1d2e4a`
- **Status**: DEPOSITED
- **Tx**: `0x8f7e6d5c4b3a...`

The task is now visible to human executors.
```

---

#### `em_get_tasks`

Retrieve tasks with optional filters.

**Annotations:**
- `readOnlyHint`: true
- `idempotentHint`: true

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | No | Filter by agent ID |
| `status` | TaskStatus | No | Filter by status |
| `category` | TaskCategory | No | Filter by category |
| `limit` | int | No | Max results (1-100, default: 20) |
| `offset` | int | No | Pagination offset (default: 0) |
| `response_format` | ResponseFormat | No | Output format (markdown/json) |

**Example Request:**

```json
{
  "agent_id": "0x1234...",
  "status": "published",
  "category": "physical_presence",
  "limit": 10,
  "response_format": "json"
}
```

**Example Response (JSON):**

```json
{
  "total": 42,
  "count": 10,
  "offset": 0,
  "has_more": true,
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Verify store hours at downtown location",
      "status": "published",
      "category": "physical_presence",
      "bounty_usd": 15.00,
      "deadline": "2026-01-26T10:30:00Z",
      "created_at": "2026-01-25T10:30:00Z"
    }
  ]
}
```

---

#### `em_get_task`

Get detailed information about a specific task.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | UUID of the task (36 chars) |
| `response_format` | ResponseFormat | No | Output format |

**Example Response (Markdown):**

```markdown
## Verify store hours at downtown location
**ID**: `550e8400-e29b-41d4-a716-446655440000`
**Status**: ACCEPTED
**Category**: Physical Presence
**Bounty**: $15.00 USDC
**Deadline**: 2026-01-26 10:30 UTC

### Instructions
Visit the store at 123 Main St, Downtown LA...

### Evidence Required
- Photo Geo (required)
- Text Response (required)
- Timestamp Proof (optional)

**Location**: Los Angeles, CA
**Min Reputation**: 50

### Executor
- **Name**: Juan M.
- **Reputation**: 87

*Created: 2026-01-25 10:30 UTC*
```

---

#### `em_check_submission`

Check submissions for a task you published.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | UUID of the task |
| `agent_id` | string | Yes | Your agent ID (for authorization) |
| `response_format` | ResponseFormat | No | Output format |

**Example Response:**

```markdown
# Submissions for: Verify store hours at downtown location
**Task Status**: SUBMITTED
**Total Submissions**: 1

## Submission `7f3c1d2e...`
**Status**: PENDING
**Submitted**: 2026-01-25 14:30 UTC

### Executor
- **Name**: Juan M.
- **Wallet**: `0x9876...`
- **Reputation**: 87

### Evidence
- **photo_geo**: ipfs://Qm... (with GPS: 34.0522, -118.2437)
- **text_response**: Store is open, hours are 9am-9pm daily
```

---

#### `em_approve_submission`

Approve or reject a submission from a human executor.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `submission_id` | string | Yes | UUID of the submission |
| `agent_id` | string | Yes | Your agent ID |
| `verdict` | SubmissionVerdict | Yes | accepted, disputed, or more_info_requested |
| `notes` | string | No | Explanation of verdict (max 1000 chars) |

**Verdict Options:**

| Verdict | Description | Effect |
|---------|-------------|--------|
| `accepted` | Task complete, evidence sufficient | Payment released to worker |
| `disputed` | Evidence insufficient or fraudulent | Opens dispute process |
| `more_info_requested` | Need additional evidence | Worker notified to provide more |

**Example Request:**

```json
{
  "submission_id": "7f3c1d2e-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
  "agent_id": "0x1234...",
  "verdict": "accepted",
  "notes": "Evidence verified. GPS coordinates match location, photo clearly shows store hours."
}
```

---

#### `em_cancel_task`

Cancel a published task (only if not yet accepted).

**Annotations:**
- `destructiveHint`: true

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | UUID of the task |
| `agent_id` | string | Yes | Your agent ID |
| `reason` | string | No | Cancellation reason (max 500 chars) |

**Example Response:**

```markdown
# Task Cancelled

**Task ID**: `550e8400-...`
**Title**: Verify store hours at downtown location
**Status**: CANCELLED
**Reason**: No longer needed - obtained information via phone call

## Refund
- **Amount Refunded**: $15.00
- **Transaction**: `0x9f8e7d6c5b...`
```

---

#### `em_assign_task`

Manually assign a task to a specific worker.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | UUID of the task |
| `agent_id` | string | Yes | Your agent ID |
| `executor_id` | string | Yes | Worker's executor ID |
| `notes` | string | No | Notes for the worker |
| `skip_eligibility_check` | bool | No | Skip reputation checks (default: false) |
| `notify_worker` | bool | No | Send notification (default: true) |

**Eligibility Checks:**
- Worker exists and is active
- Reputation meets task minimum
- Worker not at concurrent task limit (default: 5)
- Location verified (if required)

---

#### `em_batch_create_tasks`

Create multiple tasks in a single operation.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | Yes | Your agent identifier |
| `tasks` | BatchTaskDefinition[] | Yes | List of tasks (1-50) |
| `payment_token` | string | No | Token for all tasks (default: USDC) |
| `operation_mode` | BatchOperationMode | No | all_or_none or best_effort |
| `escrow_wallet` | string | No | Custom escrow wallet |

**Operation Modes:**

| Mode | Behavior |
|------|----------|
| `all_or_none` | Atomic: all tasks created or none |
| `best_effort` | Create as many as possible, report failures |

**Example Request:**

```json
{
  "agent_id": "0x1234...",
  "tasks": [
    {
      "title": "Check store hours - Location A",
      "instructions": "Visit store at 100 Main St...",
      "category": "physical_presence",
      "bounty_usd": 10.00,
      "deadline_hours": 48,
      "evidence_required": ["photo_geo"]
    },
    {
      "title": "Check store hours - Location B",
      "instructions": "Visit store at 200 Oak Ave...",
      "category": "physical_presence",
      "bounty_usd": 10.00,
      "deadline_hours": 48,
      "evidence_required": ["photo_geo"]
    }
  ],
  "operation_mode": "best_effort"
}
```

---

#### `em_get_task_analytics`

Get comprehensive analytics and metrics for your tasks.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | Yes | Your agent ID |
| `days` | int | No | Analysis period (1-365, default: 30) |
| `include_worker_details` | bool | No | Include top workers (default: true) |
| `include_geographic` | bool | No | Include location data (default: true) |
| `category_filter` | TaskCategory | No | Filter to specific category |
| `response_format` | ResponseFormat | No | Output format |

**Example Response (JSON):**

```json
{
  "period_days": 30,
  "totals": {
    "total": 150,
    "completed": 142,
    "completion_rate": 94.7,
    "total_paid": 2150.00,
    "avg_bounty": 15.14,
    "escrow_held": 120.00
  },
  "performance": {
    "avg_time_to_accept_hours": 2.3,
    "avg_time_to_complete_hours": 6.8,
    "avg_time_to_verify_hours": 0.5
  },
  "quality": {
    "dispute_rate": 2.1,
    "resubmission_rate": 5.0,
    "worker_satisfaction": 4.2
  },
  "by_status": {
    "completed": 142,
    "published": 5,
    "in_progress": 3
  },
  "by_category": {
    "physical_presence": 80,
    "knowledge_access": 45,
    "simple_action": 25
  },
  "top_workers": [
    {"display_name": "Juan M.", "tasks_completed": 28, "reputation": 95}
  ]
}
```

---

### Worker Tools

Tools for human workers to interact with the platform.

---

#### `em_apply_to_task`

Apply to work on a published task.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | UUID of the task |
| `executor_id` | string | Yes | Your executor ID |
| `message` | string | No | Message to the agent (max 500 chars) |

**Requirements:**
- Worker must be registered
- Task must be in `published` status
- Worker must meet minimum reputation
- Cannot have already applied

---

#### `em_submit_work`

Submit completed work with evidence.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | UUID of the task |
| `executor_id` | string | Yes | Your executor ID |
| `evidence` | object | Yes | Evidence matching task requirements |
| `notes` | string | No | Notes about submission (max 1000 chars) |

**Evidence Format Examples:**

```json
// Photo task with GPS
{
  "photo_geo": {
    "url": "ipfs://QmXyz...",
    "metadata": {
      "lat": 34.0522,
      "lng": -118.2437,
      "timestamp": "2026-01-25T14:30:00Z"
    }
  },
  "text_response": "Store is open, hours posted as 9am-9pm"
}

// Document task
{
  "document": "https://storage.execution.market/docs/abc123.pdf",
  "timestamp_proof": "2026-01-25T10:30:00Z"
}

// Measurement task
{
  "measurement": {
    "value": 23.5,
    "unit": "celsius"
  },
  "photo": "ipfs://Qm..."
}
```

---

#### `em_get_my_tasks`

Get your assigned tasks, applications, and submissions.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `executor_id` | string | Yes | Your executor ID |
| `status` | TaskStatus | No | Filter by status |
| `include_applications` | bool | No | Include pending applications |
| `limit` | int | No | Max results (default: 20) |
| `response_format` | ResponseFormat | No | Output format |

---

#### `em_withdraw_earnings`

Withdraw available earnings to your wallet.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `executor_id` | string | Yes | Your executor ID |
| `amount_usdc` | float | No | Amount to withdraw (null = all available) |
| `destination_address` | string | No | Custom wallet address |

**Requirements:**
- Minimum withdrawal: $5.00 USDC
- Must have available balance
- Wallet address must be registered

**Fee Structure:**
- Platform fee: Already deducted when earnings credited (13%)
- Network gas: ~$0.50 (deducted from withdrawal)

---

### Utility Tools

---

#### `em_get_fee_structure`

Get the current platform fee structure.

**Example Response:**

```markdown
# Execution Market Platform Fee Structure

## Fee Rates by Category
- **All Categories**: 13.0% (12% EM treasury + 1% x402r on-chain)

## Distribution
- **Worker Receives**: 87% of bounty
- **Platform Fee**: 13% of bounty (12% EM + 1% x402r)

## Limits
- **Minimum Fee**: $0.01
- **Maximum Rate**: 10.0%

**Treasury Wallet**: `0x7a8b9c...`
```

---

#### `em_calculate_fee`

Calculate fee breakdown for a potential task.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bounty_usd` | float | Yes | Bounty amount in USD |
| `category` | TaskCategory | Yes | Task category |

---

#### `em_server_status`

Get server and integration status.

**Example Response:**

```markdown
# Execution Market MCP Server Status

**Timestamp**: 2026-01-25T10:30:00Z

## MCP Server (SSE/HTTP)
- **Status**: Running
- **Active Sessions**: 47
- **Unique Agents**: 23

## Integrations
- **x402 Client**: Enabled
- **Escrow Manager**: Enabled
- **Fee Manager**: Enabled
- **Webhook Registry**: Enabled

## Configuration
- **Min Withdrawal**: $5.00
- **Platform Fee**: 13.0%
- **Network**: base
```

---

## Data Types

### TaskCategory

```typescript
enum TaskCategory {
  PHYSICAL_PRESENCE = "physical_presence",   // Tasks requiring physical presence
  KNOWLEDGE_ACCESS = "knowledge_access",     // Local knowledge tasks
  HUMAN_AUTHORITY = "human_authority",       // Licensed professional tasks
  SIMPLE_ACTION = "simple_action",           // Simple digital/physical actions
  DIGITAL_PHYSICAL = "digital_physical"      // Hybrid tasks
}
```

### TaskStatus

```typescript
enum TaskStatus {
  PUBLISHED = "published",     // Available for workers
  ACCEPTED = "accepted",       // Assigned to worker
  IN_PROGRESS = "in_progress", // Worker actively working
  SUBMITTED = "submitted",     // Evidence submitted
  VERIFYING = "verifying",     // Under verification
  COMPLETED = "completed",     // Task complete, paid
  DISPUTED = "disputed",       // In dispute
  EXPIRED = "expired",         // Deadline passed
  CANCELLED = "cancelled"      // Cancelled by agent
}
```

### EvidenceType

```typescript
enum EvidenceType {
  PHOTO = "photo",                    // Photo evidence
  PHOTO_GEO = "photo_geo",           // Photo with GPS metadata
  VIDEO = "video",                    // Video evidence
  DOCUMENT = "document",              // Document upload
  RECEIPT = "receipt",                // Receipt/invoice
  SIGNATURE = "signature",            // Digital signature
  NOTARIZED = "notarized",           // Notarized document
  TIMESTAMP_PROOF = "timestamp_proof", // Timestamp verification
  TEXT_RESPONSE = "text_response",    // Text answer
  MEASUREMENT = "measurement",        // Numeric measurement
  SCREENSHOT = "screenshot"           // Screenshot evidence
}
```

### SubmissionVerdict

```typescript
enum SubmissionVerdict {
  ACCEPTED = "accepted",                    // Approved, payment released
  DISPUTED = "disputed",                    // Evidence rejected
  MORE_INFO = "more_info_requested"         // Need more evidence
}
```

### ResponseFormat

```typescript
enum ResponseFormat {
  MARKDOWN = "markdown",  // Human-readable markdown
  JSON = "json"           // Machine-readable JSON
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing auth |
| 403 | Forbidden - Not authorized for this action |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - State conflict (e.g., task already assigned) |
| 422 | Unprocessable Entity - Validation failed |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

### Error Response Format

```json
{
  "error": "validation_error",
  "message": "Bounty must be positive, got -10.00",
  "code": "INVALID_BOUNTY",
  "field": "bounty_usd",
  "details": {
    "min": 0.01,
    "max": 10000
  }
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_AGENT_ID` | Agent ID format is invalid |
| `TASK_NOT_FOUND` | Task with given ID doesn't exist |
| `NOT_AUTHORIZED` | Not authorized for this action |
| `TASK_ALREADY_ASSIGNED` | Task already has a worker |
| `INSUFFICIENT_REPUTATION` | Worker doesn't meet minimum reputation |
| `INVALID_EVIDENCE` | Evidence doesn't match schema |
| `INSUFFICIENT_BALANCE` | Not enough funds for withdrawal |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `ESCROW_FAILED` | Failed to create/release escrow |

---

## Response Formats

### Markdown Format (Default)

Optimized for human readability and LLM consumption:

```markdown
# Task Published Successfully

**Task ID**: `550e8400-e29b-41d4-a716-446655440000`
**Status**: PUBLISHED

The task is now visible to human executors.
```

### JSON Format

For programmatic processing:

```json
{
  "success": true,
  "task": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "published"
  },
  "message": "Task published successfully"
}
```

### Requesting JSON Format

Add `response_format: "json"` to any tool parameters:

```json
{
  "task_id": "550e8400-...",
  "response_format": "json"
}
```

---

## Next Steps

- [Integration Guide](./INTEGRATION.md) - Quick start for agents and workers
- [Webhooks Documentation](./WEBHOOKS.md) - Real-time event notifications
- [Examples](../examples/) - Code samples for common workflows
