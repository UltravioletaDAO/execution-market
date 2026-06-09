---
date: 2026-05-20
tags:
  - type/guide
  - domain/agents
  - domain/infrastructure
status: active
aliases:
  - em-k1-mcp
  - K1 MCP Server
related-files:
  - src/em_k1_mcp/server.py
  - src/em_k1_mcp/backends/base.py
---

# em-k1-mcp-server

MCP server that lets Claude Code (and any other [Model Context Protocol](https://modelcontextprotocol.io) client) drive a **Booster K1 Professional** humanoid robot, with a built-in bridge to [Execution Market](https://execution.market) so the K1 can claim and complete real tasks on the marketplace.

The server ships three backends — **mock** (default, no hardware needed), **isaac_sim** (NVIDIA Isaac Sim stub), and **hardware** (real K1 via `booster_robotics_sdk`) — selected with one environment variable. Swap backends without touching tool code.

> Hardware status: K1 unit ordered, 3-4 week lead time. Until the robot lands, every tool runs end-to-end against the mock backend so MCP wiring, EM integration, and Claude registration can be validated today.

## Tools

| Category | Tool | What it does |
|----------|------|--------------|
| Locomotion | `k1_stand` | Stand the robot up (idempotent) |
| Locomotion | `k1_sit` | Sit the robot down (idempotent) |
| Locomotion | `k1_walk_to` | Navigate to `(x_m, y_m, heading_deg)` at a speed-capped pace |
| Locomotion | `k1_emergency_stop` | Halt every actuator. Safe to call any time. |
| Manipulation | `k1_pick` | Pick up an `object_id` at a clamped grip force |
| Manipulation | `k1_place` | Place the held object at `(x_m, y_m, z_m)` |
| Manipulation | `k1_grip` | Close the grippers at `force` for `duration_s` |
| Perception | `k1_observe` | Capture a head-camera frame + AI caption |
| Execution Market | `em_claim_task` | Apply to + claim an EM task |
| Execution Market | `em_submit_evidence` | Submit completed work to EM |

All tools accept a single `params` Pydantic model and return a typed result with `ok`, `backend`, and `message` fields.

## Installation

```bash
git clone https://github.com/ultravioleta-dao/execution-market.git
cd execution-market/em-k1-mcp-server

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

The `booster_robotics_sdk` is **not** on PyPI and is delivered with the K1 hardware. Install it manually when the robot arrives:

```bash
# When you receive the SDK from Booster Robotics:
pip install /path/to/booster_robotics_sdk-x.y.z-py3-none-any.whl
```

Until then, run with `K1_BACKEND=mock` (the default).

## Configuration

Copy `.env.example` to `.env` and fill in the values you actually have:

```bash
cp .env.example .env
# then edit .env in your favorite editor
```

Key variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `K1_HOST` | IP/hostname of the K1 on your LAN | `127.0.0.1` |
| `K1_BACKEND` | `mock` \| `isaac_sim` \| `hardware` | `mock` |
| `K1_MAX_LINEAR_VELOCITY_MPS` | Safety cap for `walk_to` speed | `0.6` |
| `K1_MAX_GRIP_FORCE_N` | Safety cap for `pick`/`grip` force | `40.0` |
| `K1_VISION_MODEL` | Model for `k1_observe` captions | `claude-opus-4-7` |
| `EM_API_URL` | Execution Market REST endpoint | `https://api.execution.market` |
| `EM_WALLET_KEY_PATH` | OWS-encrypted keystore path | placeholder |

The server will **never** read a raw private key — only a path to an encrypted OWS keystore that the OWS MCP server unlocks at runtime.

## Running locally (mock backend)

```bash
em-k1-mcp
# or equivalently
python -m em_k1_mcp.server
```

FastMCP defaults to the stdio transport, which is exactly what Claude Code wants.

## Running the tests

```bash
pytest
```

The test suite is fully self-contained: it patches the HTTP layer with `httpx.MockTransport` for the Execution Market integration tests, and it uses the `MockK1Backend` for everything else. No robot, no Isaac Sim, no network access required.

## Connecting to Claude Code

After installing the package in your virtualenv:

```bash
claude mcp add em-k1 -- python -m em_k1_mcp.server
```

Then ask Claude something like *"Stand up, walk to (1, 0) heading 0, observe what you see, and submit the result as evidence for task abc-123 on Execution Market."*

## Switching backends

```bash
# Default — no hardware needed
K1_BACKEND=mock em-k1-mcp

# Isaac Sim (NotImplementedError on every call until we wire it up)
K1_BACKEND=isaac_sim em-k1-mcp

# Real robot — needs booster_robotics_sdk installed and K1 powered on
K1_BACKEND=hardware K1_HOST=192.168.1.50 em-k1-mcp
```

The hardware backend currently raises `NotImplementedError` on every method. Each one has a `TODO` comment pointing at the matching `booster_robotics_sdk` call — when the K1 arrives, the only file that needs filling in is `src/em_k1_mcp/backends/hardware.py`. Everything else (tools, Pydantic models, EM REST integration, Claude registration, tests) is done.

## Project layout

```
em-k1-mcp-server/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/em_k1_mcp/
│   ├── server.py              # FastMCP entry point
│   ├── config.py              # .env loader
│   ├── models.py              # Pydantic input/output models
│   ├── backends/
│   │   ├── base.py            # BaseK1Backend abstract interface
│   │   ├── mock.py            # MockK1Backend — default, no hardware
│   │   ├── isaac_sim.py       # IsaacSimK1Backend — stub
│   │   └── hardware.py        # HardwareK1Backend — wraps booster_robotics_sdk
│   └── tools/
│       ├── locomotion.py      # k1_stand / k1_sit / k1_walk_to / k1_emergency_stop
│       ├── manipulation.py    # k1_pick / k1_place / k1_grip
│       ├── perception.py      # k1_observe
│       └── em_integration.py  # em_claim_task / em_submit_evidence
└── tests/
    ├── conftest.py
    ├── test_tools.py
    └── test_em_integration.py
```

## Reference

* Hardware procurement, ROS topics, and acceptance checklist live in the parent project's **Anexo D** (Execution Market K1 procurement plan).
* Main Execution Market server: [`mcp_server/`](../mcp_server/) — shares the FastMCP + `register_*_tools` pattern.
* OWS MCP Server (wallet management for AI agents): [`ows-mcp-server/`](../ows-mcp-server/) — provides `ows_sign_eip3009` for gasless EM payments.
