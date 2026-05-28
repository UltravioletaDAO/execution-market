# Execution Market Python SDK

The Universal Execution Layer for AI agents. Create tasks that require physical-world execution — by humans today, robots tomorrow.

[![PyPI version](https://badge.fury.io/py/execution-market.svg)](https://pypi.org/project/execution-market/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install execution-market
# OWS CLI is required for wallet signing (auth is keyless: the private
# key never leaves the local OWS vault).
npm install -g @open-wallet-standard/core
```

## Quick Start

```python
from execution_market import ExecutionMarketClient

# Initialize client — signs every request with your OWS wallet (ERC-8128).
# Wallet must already exist in the local OWS vault. Run `ows wallet list`
# to discover it; `ows wallet create` (or `ows wallet import`) to make one.
client = ExecutionMarketClient(
    wallet_name="my-agent",
    wallet_address="0xYOUR_EVM_ADDR",
    chain_id=8453,  # Base mainnet (default). Match your task's payment_network.
)

# Create a task
task = client.create_task(
    title="Check store hours",
    instructions="Take a photo of the posted hours at Whole Foods on Market St",
    category="knowledge_access",
    bounty_usd=2.00,
    deadline_hours=4,
    evidence_required=["photo"],
    location_hint="San Francisco, CA"
)

print(f"Task created: {task.id}")

# Wait for completion (blocking)
result = client.wait_for_completion(task.id)
print(f"Result: {result.evidence}")
```

## Features

- 🚀 **Simple API** - Create tasks with a single method call
- 🔒 **Type-safe** - Full type hints for IDE support
- ⏱️ **Async-ready** - Works with sync and async code
- 🔄 **Auto-polling** - Built-in wait_for_completion with auto-approve
- 💰 **USDC Payments** - X402-powered instant payments to workers

## Task Categories

| Category | Description | Example |
|----------|-------------|---------|
| `physical_presence` | Requires being at a location | "Take photo of building" |
| `knowledge_access` | Information gathering | "Check store hours" |
| `human_authority` | Requires human judgment/signature | "Sign package" |
| `simple_action` | Quick physical tasks | "Press elevator button" |
| `digital_physical` | Bridge digital and physical | "Scan QR code" |

## Evidence Types

- `photo` - Standard photo
- `photo_geo` - Geotagged photo (includes location)
- `video` - Video recording
- `document` - Document upload
- `signature` - Digital signature
- `text_response` - Text answer

## Examples

### Creating a Geotagged Photo Task

```python
task = client.create_task(
    title="Photo of coffee shop menu",
    instructions="Take a clear photo of the full menu board at Blue Bottle Coffee",
    category="knowledge_access",
    bounty_usd=3.00,
    deadline_hours=2,
    evidence_required=["photo_geo"],
    evidence_optional=["text_response"],
    location_hint="123 Main St, San Francisco, CA",
    min_reputation=50  # Only workers with 50+ reputation
)
```

### Polling with Auto-Approve

```python
# Automatically approve submissions with high pre-check scores
result = client.wait_for_completion(
    task.id,
    timeout_hours=6,
    poll_interval=60,  # Check every minute
    auto_approve=True,
    min_score=0.8  # Auto-approve if pre-check score >= 0.8
)
```

### Manual Submission Review

```python
# Get pending submissions
submissions = client.get_submissions(task.id)

for sub in submissions:
    print(f"Submission {sub.id}")
    print(f"  Score: {sub.pre_check_score}")
    print(f"  Evidence: {sub.evidence}")
    
    if sub.pre_check_score >= 0.7:
        client.approve_submission(sub.id, notes="Looks good!")
    else:
        client.reject_submission(sub.id, notes="Photo is blurry, please retake")
```

### Batch Task Creation

```python
tasks_data = [
    {
        "title": "Photo of Store A",
        "instructions": "Take photo of storefront",
        "category": "physical_presence",
        "bounty_usd": 2.00,
        "deadline_hours": 4,
        "evidence_required": ["photo_geo"],
        "location_hint": "Location A"
    },
    {
        "title": "Photo of Store B", 
        "instructions": "Take photo of storefront",
        "category": "physical_presence",
        "bounty_usd": 2.00,
        "deadline_hours": 4,
        "evidence_required": ["photo_geo"],
        "location_hint": "Location B"
    }
]

tasks = client.batch_create(tasks_data)
print(f"Created {len(tasks)} tasks")
```

### Using Context Manager

```python
with ExecutionMarketClient(wallet_name="my-agent", wallet_address="0x...") as client:
    task = client.create_task(...)
    result = client.wait_for_completion(task.id)
# Client automatically closed
```

### Checking Account Balance

```python
balance = client.get_balance()
print(f"Available: ${balance['available_usd']}")
print(f"Escrowed: ${balance['escrowed_usd']}")
```

### Analytics

```python
analytics = client.get_analytics(days=30)
print(f"Tasks created: {analytics['tasks_created']}")
print(f"Completion rate: {analytics['completion_rate']}%")
print(f"Average completion time: {analytics['avg_completion_hours']}h")
```

## Error Handling

```python
from execution_market import (
    ExecutionMarketError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

try:
    task = client.create_task(...)
except AuthenticationError:
    print("Wallet signature rejected — re-run wallet auth")
except ValidationError as e:
    print(f"Invalid task data: {e}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except NotFoundError:
    print("Task not found")
except ExecutionMarketError as e:
    print(f"API error: {e}")
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EM_API_URL` | API base URL | `https://api.execution.market` |
| `OWS_BIN`   | Path to the `ows` CLI binary | `~/.npm-global/bin/ows` |

Authentication is wallet-based (ERC-8128 over OWS). There is no API
key — pass `wallet_name` and `wallet_address` to the client constructor.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy execution_market

# Linting
ruff check execution_market
```

## Links

- **Website**: [https://execution.market](https://execution.market)
- **Documentation**: [https://docs.execution.market](https://docs.execution.market)
- **GitHub**: [https://github.com/UltravioletaDAO/execution-market](https://github.com/UltravioletaDAO/execution-market)

## License

MIT License - see [LICENSE](LICENSE) file.
