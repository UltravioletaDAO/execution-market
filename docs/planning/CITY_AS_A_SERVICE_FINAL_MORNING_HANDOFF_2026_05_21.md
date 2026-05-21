# City-as-a-Service — Final Morning Handoff (2026-05-21)

## Priority decision

`~/clawd/DREAM-PRIORITIES.md` won over the stale cron payload. AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 were not touched.

## Repo state

- Repo: `projects/execution-market`
- Branch: `feat/operator-route-regret-panel`
- Synced with `git pull --ff-only`: already up to date
- Pre-existing untracked file left untouched: `scripts/sign_req.mjs`

## What landed overnight

Tonight advanced only internal/admin AAS proof and claim-control surfaces:

1. **AAS cross-family approval-state matrix**
   - Safe claim: `admin_aas_cross_family_approval_state_matrix_landed`
   - Meaning: compact portfolio view across Compliance Desk, Document / Handoff, and Incident Verification approval posture; no delivery authorization.

2. **AAS claim quarantine board**
   - Safe claim: `admin_aas_claim_quarantine_board_landed`
   - Meaning: launch/customer/runtime/payment/reputation/GPS/domain-authority claims are grouped into quarantined buckets with named smallest-proof requirements.

3. **AAS claim quarantine read surface**
   - Safe claim: `admin_aas_claim_quarantine_read_surface_landed`
   - Meaning: deterministic internal/admin read payload over the quarantine board for a future operator surface; no route registered.

4. **AAS strength-connection control packet**
   - Safe claim: `admin_aas_strength_connection_control_packet_landed`
   - Meaning: connects coordination metrics and intelligence-flow discipline into a handoff packet; declared strengths remain distinct from verified proof.

5. **Pre-dawn synthesis**
   - File: `docs/planning/CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_21.md`
   - Meaning: compresses the night's claim-control pattern and daytime recommendations.

## Strategic synthesis

The AAS system now has a clearer launch-control grammar:

```text
approval request is not approval
approval record is not delivery authorization
quarantined claim is not launch readiness
declared strength is not current verification
runtime prerequisite evidence is not runtime parity
```

The strongest new idea is the **claim quarantine loop**. Instead of debating whether AAS is “ready,” the board names every tempting claim and demands the next smallest proof before it can leave quarantine.

This should become the default daytime review posture for all AAS packaging: if a claim sounds customer-visible, public, dispatch-related, reputation-related, runtime-related, payment/production-related, location-related, legal/domain-authority-related, or worker-doctrine-related, it belongs in quarantine until a specific proof artifact exists.

## Recommended daytime fork

### Best product move

Build the fail-closed internal/admin route preflight or mount manifest for:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_claim_quarantine_read_surface.json
```

The preflight should prove:

- internal/admin access only;
- source fixture digest parity;
- pass-through response semantics;
- no public/customer/worker route registration;
- safe and blocked claims remain adjacent;
- all readiness/access/authority flags stay false.

### Best operator-learning move

Build an operator regret / prevented-claim panel over the quarantine read surface. It should record which quarantined claims were prevented in a review pass and what exact proof would be needed next.

### If customer exposure is explicitly desired

Use a separate explicit human operator decision for a named delivery path. Do not infer customer delivery or publication from the Compliance Desk approval record, because it still says:

```text
authorized_delivery_path=none_no_customer_delivery_authorized
```

### If runtime-memory is the target

Fix Acontext prerequisites first. No live Acontext write/retrieve parity is authorized until Docker image pulls/cache or mirror, compose startup, localhost API/dashboard, and a rebuilt empty readiness gate are clean.

## Hard no-claims list

Still false/blocked:

```text
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
public_route_ready
controlled_pilot_ready
public_pricing_or_customer_quote_ready
operator_queue_launch_ready
autonomous_dispatch_ready
erc8004_reputation_ready
worker_skill_dna_ready
live_acontext_runtime_parity
acontext_sink_ready
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
raw_transcript_authority
domain_or_legal_or_regulator_or_notarial_or_custody_authority
emergency_or_safety_or_repair_or_insurance_or_sla_or_official_report_or_fault_liability_authority
worker_copyable_aas_doctrine
```

## Verification state before handoff

Final city-ops gate after the doc-only synthesis:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
1058 passed
```

If daytime changes code, rerun the full city-ops suite from the repo venv.
