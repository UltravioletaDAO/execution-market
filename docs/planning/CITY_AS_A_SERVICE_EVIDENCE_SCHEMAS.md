# City as a Service — Evidence Schemas

> Last updated: 2026-04-25
> Parent plan: `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> Companion doc: `CITY_AS_A_SERVICE_TEMPLATE_SPECS.md`
> Status: implementation-oriented draft

## 1. Why this document exists

Execution Market already collects evidence.
City as a Service needs a stricter layer: not just files, but normalized municipal outcomes.

The point of these schemas is to make city interactions:
- reviewable by operators
- analyzable across jurisdictions
- chainable into next-step automation
- useful as long-term municipal memory

## 2. Evidence design principles

### 2.1 Evidence must answer a business question
The schema should always help answer:
- what happened?
- how do we know?
- what should happen next?

### 2.2 Preserve provenance
Every important field should trace back to one of:
- observed in person
- heard from staff
- documented on paper/signage/receipt

### 2.3 Normalize the outcome, not just the attachment
A photo without a structured conclusion creates operator toil.
A receipt without a normalized result is hard to replay.

### 2.4 Allow uncertainty explicitly
City workflows often produce ambiguous answers.
The schema must support inconclusive outcomes instead of pressuring workers to invent certainty.

## 3. Shared top-level schema

Every CaaS evidence payload should include a common envelope.

```json
{
  "vertical": "city_ops",
  "workflow_template": "counter_question",
  "jurisdiction_name": "[jurisdiction]",
  "office_name": "[office]",
  "outcome_status": "completed",
  "source_type": "mixed",
  "confidence_score": 0.82,
  "captured_at": "2026-04-25T04:35:00Z",
  "attachments": [],
  "structured_result": {},
  "next_step_recommendation": "resubmit_packet",
  "worker_notes_structured": {}
}
```

## 4. Canonical enums

### 4.1 `outcome_status`
- `completed`
- `accepted`
- `rejected`
- `redirected`
- `blocked`
- `inconclusive`

### 4.2 `source_type`
- `observed`
- `heard`
- `documented`
- `mixed`

### 4.3 `attachment_type`
- `wide_photo`
- `closeup_photo`
- `receipt_photo`
- `stamped_copy`
- `signage_photo`
- `document_scan`
- `text_summary`
- `audio_summary`
- `timestamp_proof`

### 4.4 `next_step_recommendation`
- `none`
- `resubmit_packet`
- `ask_followup_question`
- `reroute_office`
- `fix_posting`
- `schedule_revisit`
- `prepare_for_inspection`
- `human_review_required`

## 5. Attachment object

Every attachment should carry minimal semantic metadata.

```json
{
  "attachment_type": "receipt_photo",
  "evidence_type": "photo",
  "label": "submission receipt",
  "path_or_url": "[stored file]",
  "is_primary": true,
  "legibility_score": 0.93,
  "captured_at": "2026-04-25T04:35:00Z"
}
```

Recommended fields:
- `attachment_type`
- `evidence_type`
- `label`
- `path_or_url`
- `is_primary`
- `legibility_score` when relevant
- `captured_at`

## 6. Schema: Counter Question

### 6.1 Structured result shape

```json
{
  "question": "Which form version is currently required?",
  "answer_text": "Staff said the April 2026 version is required.",
  "answer_confidence": 0.79,
  "answer_origin": "heard",
  "redirect_target": null,
  "office_open": true,
  "secondary_notes": "Counter signage matched the answer."
}
```

### 6.2 Required fields
- `question`
- `answer_text`
- `answer_confidence`
- `answer_origin`

### 6.3 Optional fields
- `redirect_target`
- `office_open`
- `secondary_notes`
- `quoted_language`

### 6.4 Review heuristics
A Counter Question result is high quality when:
- the exact question is preserved
- the answer provenance is clear
- redirects are machine-readable
- office reality (open/closed/renovated/moved) is captured separately

## 7. Schema: Packet Submission

### 7.1 Structured result shape

```json
{
  "submission_result": "rejected",
  "receipt_present": false,
  "receipt_unavailable_reason": "no receipt issued for rejected packets",
  "rejection_reasons": [
    "missing_signature",
    "outdated_form_version"
  ],
  "redirect_target": "Licensing Window B",
  "fee_payment_status": "not_collected",
  "next_required_step": "Update form version and obtain wet signature."
}
```

### 7.2 Required fields
- `submission_result`
- `receipt_present`
- `rejection_reasons` or empty array
- `redirect_target` nullable
- `next_required_step`

### 7.3 Optional fields
- `receipt_unavailable_reason`
- `fee_payment_status`
- `stamped_copy_present`
- `counter_notes`

### 7.4 Suggested rejection reason enum
Initial taxonomy:
- `missing_signature`
- `outdated_form_version`
- `missing_attachment`
- `wrong_office`
- `fee_required`
- `appointment_required`
- `insufficient_identity_documentation`
- `not_accepting_walk_ins`
- `requires_supervisor_review`
- `other`

### 7.5 Review heuristics
A Packet Submission result is strong when it fully answers:
- Did the office accept it?
- If not, what specifically broke?
- Is the next move repair, reroute, or wait?

## 8. Schema: Posting Proof

### 8.1 Structured result shape

```json
{
  "posting_present": true,
  "posting_legible": true,
  "posting_visible_from_required_vantage": true,
  "obstruction_present": false,
  "notice_type": "permit_posting",
  "checklist_results": {
    "mounted": true,
    "legible": true,
    "publicly_visible": true
  }
}
```

### 8.2 Required fields
- `posting_present`
- `posting_legible`
- `notice_type`
- `checklist_results`

### 8.3 Optional fields
- `posting_visible_from_required_vantage`
- `obstruction_present`
- `obstruction_notes`
- `recommended_remediation`

## 9. Schema: Site Audit

### 9.1 Structured result shape

```json
{
  "site_condition_summary": "2 failures, 5 passes",
  "checklist_results": [
    {
      "item_code": "ada_signage",
      "status": "pass",
      "severity": "low",
      "note": "Signage visible from entry."
    },
    {
      "item_code": "permit_display",
      "status": "fail",
      "severity": "high",
      "note": "Required permit not visible at entrance."
    }
  ],
  "urgent_issue_present": true,
  "recommended_next_action": "fix_posting"
}
```

### 9.2 Required fields
- `checklist_results`
- `urgent_issue_present`
- `recommended_next_action`

### 9.3 Optional fields
- `site_condition_summary`
- `severity_rollup`
- `follow_on_template`

## 10. Schema: Queue Wait + Handoff

### 10.1 Structured result shape

```json
{
  "arrival_confirmed": true,
  "wait_minutes": 94,
  "handoff_result": "completed",
  "handoff_target": "intake counter",
  "blocked_reason": null,
  "redirect_target": null
}
```

### 10.2 Required fields
- `arrival_confirmed`
- `wait_minutes`
- `handoff_result`

### 10.3 Optional fields
- `handoff_target`
- `blocked_reason`
- `redirect_target`
- `closure_or_cutoff_observed`

## 11. Worker notes schema

Freeform notes should be constrained into a few product-useful buckets.

```json
{
  "observed_notes": "Office signage says permit intake moved upstairs.",
  "heard_notes": "Staff said new form version became mandatory last week.",
  "risk_flags": ["process_drift", "redirect_likely"],
  "operator_attention_needed": false
}
```

Recommended `risk_flags`:
- `process_drift`
- `office_closed_unexpectedly`
- `photo_restricted`
- `redirect_likely`
- `repeat_rejection_pattern`
- `unclear_instruction`
- `customer_doc_issue`

## 12. Replay and analytics fields

These fields make the evidence useful beyond the immediate task.

### 12.1 Replay keys
- `jurisdiction_name`
- `office_name`
- `workflow_template`
- `outcome_status`
- `rejection_reasons[]`
- `redirect_target`
- `next_step_recommendation`

### 12.2 Analytics fields
- `queue_minutes`
- `acceptance_rate_signal`
- `redirect_frequency_signal`
- `document_issue_frequency`
- `office_reliability_signal`

## 13. Storage recommendation

Store the original evidence files plus a normalized JSON summary.
Do not force future operators to reconstruct municipal outcomes from image galleries.

Recommended pattern:
- raw attachments remain immutable
- normalized evidence summary is versioned
- later operator corrections append, not overwrite provenance

## 14. Minimal validation rules

### Hard validation
- every CaaS task must emit `outcome_status`
- every CaaS task must emit at least one provenance indicator (`source_type` or attachment proving it)
- every rejected/redirected packet submission must include `next_required_step` or `redirect_target`

### Soft validation
- confidence score expected for heard/mixed answers
- legibility score expected for notice/receipt imagery
- structured checklist expected for posting proof and site audit

## 15. Sharp recommendation

If EM only implements one evidence improvement for CaaS first, it should be this:

**Require normalized `outcome_status`, `source_type`, `rejection_reasons[]`, and `next_step_recommendation` on all city workflows.**

That single move upgrades CaaS from attachment collection to true municipal execution memory.