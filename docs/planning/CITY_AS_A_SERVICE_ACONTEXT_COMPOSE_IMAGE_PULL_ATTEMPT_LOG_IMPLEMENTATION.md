# City-as-a-Service — Acontext compose image-pull attempt log

Date: 2026-05-16 23:04 EDT

Status: internal/admin prerequisite evidence only.

## What landed

- `mcp_server/city_ops/acontext_compose_image_pull_attempt_log.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_compose_image_pull_attempt_log.json`
- `mcp_server/tests/city_ops/test_acontext_compose_image_pull_attempt_log.py`

Safe claim added:

```text
admin_acontext_compose_image_pull_attempt_log_landed
```

## What was checked

After the 22:01 prerequisite probe, a second local-only Acontext compose image-pull attempt was run from `~/clawd/infra/acontext`:

```text
docker compose -f .docker-compose-1411407133.yaml --env-file .env pull --ignore-pull-failures
```

The compose config requires nine images:

- `ghcr.io/memodb-io/acontext-ui:latest`
- `chrislusf/seaweedfs:4.02`
- `pgvector/pgvector:pg16`
- `redis:7.4`
- `rabbitmq:4-management`
- `ghcr.io/memodb-io/acontext-api:latest`
- `amazon/aws-cli:2.32.6`
- `ghcr.io/memodb-io/acontext-core:latest`
- `jaegertracing/all-in-one:1.75.0`

The attempt emitted initial `Pulling` lines for all images, then no layer progress. It was stopped after a quiet window. A post-attempt local image inventory still showed only `pgvector/pgvector:pg16` from the required set.

## What this does **not** claim

This does not improve runtime readiness. It does not authorize or claim:

- completed compose image pull;
- all required Acontext images present;
- compose services started;
- localhost API/dashboard reachability;
- empty rebuilt readiness gate;
- live Acontext write/retrieve parity;
- customer/public AAS packaging, route readiness, queue launch, or dispatch;
- ERC-8004 reputation;
- payment or production infrastructure reverification;
- exact GPS/raw metadata exposure;
- worker-copyable doctrine.

## Remaining blockers

```text
compose_image_pull_not_completed
required_acontext_images_missing
acontext_compose_services_not_started
local_acontext_api_not_rechecked_reachable
local_acontext_dashboard_not_rechecked_reachable
readiness_gate_not_rebuilt_empty
```

## Next safe action

Pre-pull each required Acontext image individually with visible progress and a per-image timeout, recording image name, exit code, duration, and last progress line. Only after all nine images are present locally should compose services be started and health checked. A live write/retrieve parity attempt remains blocked until a read-only preflight and readiness gate rebuild return empty blockers.
