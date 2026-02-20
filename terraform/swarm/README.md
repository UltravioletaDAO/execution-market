# KarmaCadabra Swarm 🪄

**Deploy 5 to 200 autonomous OpenClaw AI agents on AWS with a single command.**

Each agent gets its own personality, identity, and workspace. The only input you need is an Anthropic API key.

## Quick Start

```bash
# Deploy 5 agents (Phase 0, ~$62/mo)
./scripts/deploy.sh --api-key sk-ant-your-key-here

# Check status
./scripts/deploy.sh --status

# Scale to 55 agents
./scripts/deploy.sh --api-key sk-ant-your-key-here --agents 55

# Scale to 200 agents
./scripts/deploy.sh --api-key sk-ant-your-key-here --agents 200 --batch 10

# Tear down
./scripts/deploy.sh --destroy
```

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- [Docker](https://docs.docker.com/get-docker/)
- [jq](https://jqlang.github.io/jq/)

## Architecture

```
AWS ECS Fargate (Spot)
├── Agent aurora  (Explorer personality)
├── Agent blaze   (Builder personality)
├── Agent cipher  (Connector personality)
├── Agent drift   (Analyst personality)
└── Agent echo    (Creator personality)
```

Each agent runs OpenClaw in a container with:
- **SOUL.md** — Unique personality (8 archetypes)
- **IDENTITY.md** — Name, index, metadata
- **AGENTS.md** — Swarm instructions
- **S3 sync** — Memory persists across restarts

## Cost Estimates

| Phase | Agents | Monthly Cost |
|-------|--------|-------------|
| 0 | 5 | ~$62 |
| 1 | 55 | ~$258 |
| 2 | 200 | ~$827 |

Using Fargate Spot (70% savings) and Haiku (cheapest Claude model).

## Documentation

- [Full Architecture](../../docs/KARMACADABRA_SWARM_ARCHITECTURE.md)
- [KK v2 Vision](../../docs/KARMACADABRA_V2_ARCHITECTURE.md)
- [Personality Templates](./templates/README.md)

## Structure

```
terraform/swarm/
├── main.tf                    # VPC, ECS, IAM, S3, Secrets
├── variables.tf               # All variables (1 required)
├── outputs.tf                 # Deployment info
├── Dockerfile                 # Agent container
├── modules/agent/             # Per-agent Terraform module
├── templates/                 # SOUL.md personality templates
└── scripts/
    ├── deploy.sh              # Main deployment script
    ├── entrypoint.sh          # Container entrypoint
    ├── bootstrap-workspace.sh # Workspace generator
    └── sync-state.sh          # S3 state sync
```

## Part of

[Execution Market](https://execution.market) by [Ultravioleta DAO](https://ultravioletadao.xyz)
