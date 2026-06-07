# City-as-a-Service — AAS Local Data Collection Measurement-Uncertainty Rubric

> Date: 2026-06-06 23:00 America/New_York
> Safe claim: `internal_admin_aas_local_data_collection_measurement_uncertainty_rubric_landed`
> Scope: internal/admin AAS planning only — no operator answer, no approval, no answer receipt, no customer/public/worker copy, no collection authorization, no dataset publication, no measurement certification, no dispatch, no runtime movement.

## Why this slice exists

`/Users/clawdbot/clawd/DREAM-PRIORITIES.md` is the active dream authority. It keeps dream work inside Execution Market AAS / City-as-a-Service and explicitly blocks AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2. This pass intentionally did not analyze, edit, expand, test, commit, or use those stopped projects as active sources, even though the stale cron payload requested them.

The latest board showed rank-6 Incident Verification already landed at 22:00. The next single low-authority roadmap row is rank 7:

```text
local_data_collection -> measurement_uncertainty_rubric_outline_no_dataset_publication
```

This implementation expands only that planning action. It treats Local Data Collection as a measurement-uncertainty grammar, not a collection authorization, dataset product, statistical certification, customer report, worker instruction, dispatch route, or runtime adapter.

## Files added

- `mcp_server/city_ops/aas_local_data_collection_measurement_uncertainty_rubric.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_local_data_collection_measurement_uncertainty_rubric.json`
- `mcp_server/tests/city_ops/test_aas_local_data_collection_measurement_uncertainty_rubric.py`
- `docs/planning/CITY_AS_A_SERVICE_AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_IMPLEMENTATION.md`

`mcp_server/city_ops/__init__.py` now exports the builder, loader, and writer.

## Source consumed

The rubric consumes `aas_concept_gap_implementation_roadmap.json` by digest and requires the rank-7 roadmap row:

```text
aas_family: local_data_collection
planning_sequence_rank: 7
roadmap_next_planning_slice: measurement_uncertainty_rubric_outline_no_dataset_publication
next_allowed_without_human_answer: planning_only_no_fixture_promotion
```

If the source roadmap promotes operator state, changes rank/action, drops blocked claims, or weakens the stopped-project firewall, the builder fails closed.

## What the artifact records

The artifact records an internal/admin measurement-uncertainty rubric for Local Data Collection only:

- measurement subject placeholder without private location or parties;
- collection window placeholder without private context;
- measurement unit placeholder with expected precision band;
- instrument/source type placeholder after redaction review;
- sample count placeholder without dataset publication;
- known missingness or coverage-gap statement;
- uncertainty range or confidence caveat requirement;
- photo/screenshot/log/text placeholder after redaction review;
- explicit unknowns and unresolved measurement questions.

Safe internal language is limited to statements like:

- `local data collection measurement uncertainty rubric only`
- `dataset publication and measurement certification blocked`
- `observed values require uncertainty and missingness context`
- `collection authorization and statistical authority not claimed`
- `future answer receipt required before dataset delivery or customer use`

Forbidden language remains blocked:

- `dataset published`
- `measurement certified`
- `accuracy guaranteed`
- `sample complete`
- `sensor calibrated`
- `statistically valid`
- `regulatory ready`
- `dispatch ready`

## What it does not do

This is not:

- Saúl's operator answer;
- operator approval;
- an answer receipt;
- selected future answer;
- customer/public/worker copy;
- data-collection site access authorization;
- sensor deployment, survey, sampling, or worker collection authorization;
- measurement accuracy, completeness, calibration, statistical validity, or regulatory claim;
- dataset/report/dashboard/benchmark publication;
- catalog/pricing/quote/route/queue/dispatch readiness;
- ERC-8004 reputation or Worker Skill DNA;
- payment/production reverification;
- live Acontext/IRC/session-manager mutation;
- exact GPS/raw metadata/private-context/PII release;
- worker-copyable doctrine;
- AutoJob, Frontier Academy, KK v2, or KarmaCadabra integration.

## Connection insight

Local Data Collection becomes useful only when the system refuses to hide uncertainty. The productive AAS primitive is not “collect data”; it is “carry the shape of a measurement with its precision, missingness, source limitations, redaction status, and unresolved questions.”

That lets future AAS surfaces price or route data work from truth-preserving evidence packets rather than pretending that one observation is a certified dataset. Any customer/worker movement still needs a separate explicit operator answer receipt.

## Next gate

Before any Local Data Collection customer, worker, dataset, route, queue, dispatch, or runtime movement:

```text
separate_explicit_operator_answer_receipt_then_local_data_collection_customer_or_dispatch_gate
```

Until that exists, the recommended posture stays:

```text
planning_only_no_fixture_promotion
```

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_local_data_collection_measurement_uncertainty_rubric.py
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
```
