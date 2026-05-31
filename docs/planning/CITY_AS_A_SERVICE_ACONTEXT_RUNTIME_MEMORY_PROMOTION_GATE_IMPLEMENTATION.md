# City-as-a-Service — Acontext Runtime-Memory Promotion Gate

> Date: 2026-05-31 05:25 UTC
> Scope: Execution Market AAS / City-as-a-Service only
> Status: internal/admin promotion gate; runtime/customer/dispatch/reputation/payment claims still blocked

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first. It overrides the stale cron payload and keeps dream work on Execution Market AAS / City-as-a-Service. AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 were not pulled, analyzed, expanded, edited, tested, or committed.

## Why this slice exists

The previous slice proved a very narrow live-local fact: one sanitized IRC-session-shaped memory candidate was written to and retrieved from the local Acontext API, while bearer values, session IDs, message IDs, private context, GPS/raw metadata, and raw logs stayed out of persisted artifacts.

That proof is useful, but it is easy to overclaim. This slice adds a deterministic fail-closed promotion gate between:

```text
one redacted local runner succeeded
```

and any future claim like:

```text
runtime memory is ready for IRC/session-manager integration
```

The gate preserves the success while blocking promotion until separate cleanup/quarantine, multi-fixture replay, opt-in runtime seam, and human/operator product gates pass.

## Landed files

```text
mcp_server/city_ops/acontext_runtime_memory_promotion_gate.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_runtime_memory_promotion_gate.json
mcp_server/tests/city_ops/test_acontext_runtime_memory_promotion_gate.py
```

Exports were added in:

```text
mcp_server/city_ops/__init__.py
```

## Source artifact

The gate consumes only:

```text
acontext_internal_irc_session_adapter_runner_fixture.json
```

It does not contact Acontext, rerun live probes, use root/project tokens, print or persist secrets, record runtime IDs, mutate IRC runtime state, touch external services, create routes, launch dispatch, emit reputation, or reverify production/payments.

## Safe claim added

```text
admin_acontext_runtime_memory_promotion_gate_landed
```

Meaning: the single redacted local runner success is now wrapped in a fail-closed promotion board that keeps all runtime/product claims blocked unless separate gates pass.

## Preserved promotable facts

```text
source_adapter_contract_defined=true
single_local_runner_fixture_executed=true
sanitized_session_create_status_201=true
sanitized_message_store_status_201=true
sanitized_message_retrieve_status_200=true
retrieved_message_text_matched=true
retrieved_message_meta_matched=true
root_token_or_bearer_recorded=false
session_or_message_id_recorded=false
private_context_or_gps_recorded=false
```

## Promotion gates

| Gate | Status | Meaning |
| --- | --- | --- |
| internal_adapter_contract | passed | Source contract remained valid. |
| single_redacted_local_runner | passed | One sanitized 201/201/200 write/retrieve runner succeeded. |
| cleanup_or_quarantine_policy | blocked | Need separate proof that cleanup/quarantine behavior is safe without persisting IDs. |
| multi_fixture_replay | blocked | Need more than one reviewed sanitized fixture before generalized sink claims. |
| opt_in_irc_runtime_adapter_seam | blocked | Need disabled-by-default runtime seam before touching IRC session management. |
| external_product_surfaces | blocked | Need separate human/operator approval for customer/public, dispatch, reputation, or payment claims. |

## Still blocked / not safe to claim

Do not infer any of the following:

```text
irc_runtime_session_manager_mutation_ready
cross_project_autorouting_ready
customer_copy_ready
customer_delivery_approved
publication_approved
public_or_catalog_route_ready
pricing_or_customer_quote_ready
operator_queue_launch_ready
autonomous_dispatch_ready
erc8004_reputation_ready
worker_skill_dna_ready
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
private_operator_context_release_allowed
worker_copyable_doctrine_ready
general_acontext_sink_ready
runtime_parity_proven
cleanup_or_quarantine_ready
multi_fixture_replay_ready
```

## Next separate gate

Design an opt-in runtime adapter seam with:

1. disabled-by-default behavior;
2. cleanup/quarantine semantics that do not persist sensitive IDs;
3. replay over more than one reviewed sanitized fixture;
4. explicit false defaults for customer/public, dispatch, reputation, payment, GPS/raw metadata, private-context, and worker-doctrine claims;
5. no customer copy or worker instructions unless a separate human/operator gate authorizes them.

## Verification

Targeted verification passed:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_runtime_memory_promotion_gate.py
# 8 passed
```

Full city-ops verification should run before the 6 AM final wrap/merge decision.
