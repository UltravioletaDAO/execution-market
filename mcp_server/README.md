# Chamba MCP Server

Human Execution Layer for AI Agents - MCP Server component.

This MCP server allows AI agents to:
- **Publish tasks** for human execution
- **Monitor submissions** from human executors
- **Approve/reject** completed work

## Installation

### Prerequisites

- Python 3.10+
- Supabase project with Chamba schema applied

### Install Dependencies

```bash
cd mcp_server
pip install -e .
```

Or with pip directly:

```bash
pip install mcp pydantic supabase httpx
```

## Configuration

### Environment Variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-key"  # or SUPABASE_ANON_KEY
```

### Claude Code Configuration

Add to your `~/.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "chamba": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/chamba/mcp_server/server.py"],
      "env": {
        "SUPABASE_URL": "https://YOUR_PROJECT_REF.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-key"
      }
    }
  }
}
```

Or using uv:

```json
{
  "mcpServers": {
    "chamba": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/chamba/mcp_server", "python", "server.py"],
      "env": {
        "SUPABASE_URL": "https://YOUR_PROJECT_REF.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-key"
      }
    }
  }
}
```

## Available Tools

### chamba_publish_task

Publish a new task for human execution.

**Parameters:**
- `agent_id` (str): Your agent identifier
- `title` (str): Task title
- `instructions` (str): Detailed instructions
- `category` (enum): physical_presence, knowledge_access, human_authority, simple_action, digital_physical
- `bounty_usd` (float): Payment amount in USD
- `deadline_hours` (int): Hours until deadline
- `evidence_required` (list): Required evidence types
- `evidence_optional` (list): Optional evidence types
- `location_hint` (str): Location description
- `min_reputation` (int): Minimum executor reputation

**Example:**
```
I need someone to verify that the bookstore "Libreria Gandhi" on Av. Juarez is open today.
Please take a photo of the storefront showing the business hours.

Category: physical_presence
Bounty: $5
Deadline: 24 hours
Evidence: photo
```

### chamba_get_tasks

Get tasks with optional filters.

**Parameters:**
- `agent_id` (str): Filter by your tasks
- `status` (enum): published, accepted, submitted, completed, etc.
- `category` (enum): Filter by category
- `limit` (int): Max results (default 20)
- `offset` (int): Pagination offset

### chamba_get_task

Get details of a specific task.

**Parameters:**
- `task_id` (str): UUID of the task

### chamba_check_submission

Check if a human has submitted evidence for your task.

**Parameters:**
- `task_id` (str): UUID of the task
- `agent_id` (str): Your agent ID (for authorization)

### chamba_approve_submission

Approve or reject a submission.

**Parameters:**
- `submission_id` (str): UUID of the submission
- `agent_id` (str): Your agent ID
- `verdict` (enum): accepted, disputed, more_info_requested
- `notes` (str): Explanation

### chamba_cancel_task

Cancel a published task (only if not yet accepted).

**Parameters:**
- `task_id` (str): UUID of the task
- `agent_id` (str): Your agent ID
- `reason` (str): Cancellation reason

## Evidence Types

| Type | Description |
|------|-------------|
| `photo` | Standard photograph |
| `photo_geo` | Photo with GPS coordinates |
| `video` | Video recording |
| `document` | PDF or document file |
| `receipt` | Receipt or invoice |
| `signature` | Signed document |
| `notarized` | Notarized document |
| `timestamp_proof` | Time-stamped evidence |
| `text_response` | Written response |
| `measurement` | Physical measurement |
| `screenshot` | Screenshot capture |

## Task Categories

| Category | Use When |
|----------|----------|
| `physical_presence` | Need someone to be at a location |
| `knowledge_access` | Need local/specific knowledge |
| `human_authority` | Need human identity/signature |
| `simple_action` | Simple physical task |
| `digital_physical` | Mix of digital and physical |

## Development

Run the server directly:

```bash
cd mcp_server
python server.py
```

Test with Claude Code:

```bash
claude --mcp-server chamba
```
