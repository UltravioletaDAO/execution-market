# City-as-a-Service — Acontext Remaining Images ORAS + Compose Health

> Date: 2026-05-30 02:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin observation; all required local Acontext images cached; local Compose stack started; API/core/UI reachable; live write/retrieve parity still not attempted

## Why this exists

`DREAM-PRIORITIES.md` remains the governing dream priority file. It explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions, so this slice stayed only inside Execution Market AAS / City-as-a-Service.

The previous safe Acontext move proved the ORAS OCI-layout export/load path by materializing the first required image, `ghcr.io/memodb-io/acontext-ui:latest`, into Docker. The remaining blocker was no longer "can the host reach a registry?" but "can the same trusted cache-load path bring the rest of the required Compose inventory local, then start the stack without promoting product/runtime parity claims?"

## Runtime observation

The same trusted ORAS path was used for the remaining required images:

```text
oras copy --platform linux/arm64 --to-oci-layout ...
tar OCI layout
docker load -i ...
docker tag loaded-image required-compose-tag
```

Post-cache inventory now contains all nine required Acontext Compose images:

```text
ghcr.io/memodb-io/acontext-ui:latest
chrislusf/seaweedfs:4.02
pgvector/pgvector:pg16
redis:7.4
rabbitmq:4-management
ghcr.io/memodb-io/acontext-api:latest
amazon/aws-cli:2.32.6
ghcr.io/memodb-io/acontext-core:latest
jaegertracing/all-in-one:1.75.0
```

Local Compose was then started with `--no-build`. The infrastructure/core/API services reported healthy and the UI container was running without a healthcheck.

Local HTTP checks:

```text
http://127.0.0.1:8029/health -> 200 {"code":0,"msg":"ok"}
http://127.0.0.1:8019/health -> 200 {"msg":"ok"}
http://127.0.0.1:3000        -> 307 /dashboard
```

## Landed files

```text
mcp_server/city_ops/acontext_remaining_images_oras_compose_health_observation.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_remaining_images_oras_compose_health.json
mcp_server/tests/city_ops/test_acontext_remaining_images_oras_compose_health_observation.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_remaining_images_oras_compose_health_landed
```

Meaning: all required local Acontext images are cached by required Compose tag, and the local Compose stack starts with API/core/UI health/reachability checks passing.

## Still blocked

Do **not** claim any of the following from this artifact:

- live Acontext write completed
- live Acontext retrieval completed
- runtime parity proven
- Acontext sink ready for IRC/session management
- cross-project autorouting
- customer copy, customer delivery, or publication readiness
- public/catalog route readiness
- pricing or customer quote readiness
- operator queue launch or dispatch readiness
- ERC-8004 reputation or Worker Skill DNA readiness
- payment or production reverification
- exact GPS/raw metadata/private-context exposure
- legal/regulator/emergency/repair/insurance/SLA authority
- worker-copyable municipal doctrine

## Next safe step

Perform one bounded SDK/API contract-discovery smoke test against the now-running local Acontext stack. Only after a real write and retrieval succeed should a separate artifact claim live write/retrieve parity.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_remaining_images_oras_compose_health_observation.py
# 10 passed
```
