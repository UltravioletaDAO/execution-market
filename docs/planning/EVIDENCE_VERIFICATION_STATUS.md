# Evidence Verification Layer — Status & Architecture

**Date**: 2026-02-24
**Status**: Phase 1 + Phase 2 COMPLETE — Functional in Production

---

## What's Live Now

The evidence verification pipeline runs **automatically on every worker submission**. No configuration needed — it's wired into `POST /api/v1/tasks/{id}/submit`.

### Flow

```
Worker submits evidence
        |
        v
+---------------------------+
|  Verification Pipeline    |    <-- Runs automatically, non-blocking
|                           |
|  1. Schema     (30%)      |    Are required fields present?
|  2. GPS        (25%)      |    Is worker near task location?
|  3. Timestamp  (20%)      |    Submitted before deadline?
|  4. Hash       (15%)      |    Evidence integrity hash present?
|  5. Metadata   (10%)      |    Device info, timestamps, files?
|                           |
|  Weighted score: 0.0-1.0  |
|  Pass: score >= 0.5       |
|  + schema check must pass |
+-------------+-------------+
              |
              v
    Saved to submissions table:
    - auto_check_passed (BOOLEAN)
    - auto_check_details (JSONB)
              |
     +--------+--------+
     |                 |
     v                 v
  MCP Tool         Dashboard
  em_check_        Review Modal
  submission       (score bars)
     |                 |
     v                 v
  Agent decides: APPROVE or REJECT
```

### What Each Check Does

| Check | Weight | What It Verifies | When It Runs |
|-------|--------|-----------------|--------------|
| **Schema** | 30% | Required evidence fields are present (photo, GPS, receipt, etc.) | Always |
| **GPS proximity** | 25% | Worker's GPS coordinates are within threshold of task location (500m for physical, 1000m for delivery) | Only when task has `location_lat/lng` |
| **Timestamp** | 20% | Submission was made before deadline with 5-minute grace period | Only when task has `deadline` |
| **Evidence hash** | 15% | Frontend computed SHA-256 hash is present (integrity marker) | Always (neutral 0.5 if absent) |
| **Metadata** | 10% | Presence of forensic metadata, device info, photo files, timestamps, notes | Always |

### Key Design Decisions

1. **Non-blocking**: Pipeline NEVER rejects a submission. It scores and flags — the agent makes the final call.
2. **Weighted scoring**: Each check contributes proportionally. A submission can pass even if one check fails (as long as aggregate >= 0.5 and schema passes).
3. **Category-aware**: GPS check behavior adapts to task category. Physical tasks require GPS; digital tasks don't.
4. **No external dependencies**: Phase 1 uses zero external APIs. Everything runs in-process with existing code.

### Where Results Are Visible

| Surface | What's Shown |
|---------|-------------|
| **API Response** (`POST /submit`) | `verification: {passed, score, checks, warnings}` |
| **MCP Tool** (`em_check_submission`) | Per-check PASS/FAIL with scores and reasons |
| **REST API** (`GET /tasks/{id}/submissions`) | `pre_check_score` field |
| **Dashboard Review Modal** | Score %, progress bars per check, warnings, metadata badges |

---

## Frontend UX Improvements (Phase 2)

### Category-Aware Evidence Collection

The submission form adapts based on task category:

| Task Category | Photo Mode | GPS Required | Guidance |
|--------------|-----------|-------------|----------|
| `physical_presence` | Camera + GPS | Yes (for `photo_geo`) | "Usa la camara y GPS para verificar tu ubicacion" |
| `simple_action` | Camera + GPS | Optional | "Documenta la accion con fotos o video" |
| `knowledge_access` | **File upload** | No | "Sube capturas, documentos o texto desde tu computador" |
| `research` | **File upload** | No | "Envia tu investigacion como texto o documentos" |
| `code_execution` | **File upload** | No | "Envia el output del codigo o archivos resultantes" |
| `digital_physical` | **File upload** | No | "Puedes subir fotos o archivos desde cualquier dispositivo" |
| `content_generation` | **File upload** | No | "Sube el contenido como archivo, texto o enlace" |

**Key UX fix**: Desktop workers doing digital tasks (research, code, content) now see a **file upload** interface instead of camera UI. No GPS required. They can drag-and-drop screenshots from their computer.

### Evidence Types (18 total, synced backend<->frontend)

Camera types: `photo`, `photo_geo`
File types: `video`, `document`, `receipt`, `signature`, `notarized`, `timestamp_proof`, `screenshot`, `file_artifact`, `structured_data`, `api_response`
Text types: `text_response`, `measurement`, `json_response`, `code_output`, `url_reference`, `text_report`

### Review Modal Enhancements

- Clickable image thumbnails (zoom on click)
- Video player for video evidence
- Metadata badges: GPS coordinates, capture timestamp, source (camera/gallery), device model, file size, checksum, AI verification status
- Auto-check section with score %, per-check progress bars, pass/fail icons

---

## Files Modified/Created

### Backend (Python)
| File | Change |
|------|--------|
| `mcp_server/verification/pipeline.py` | **NEW** — Pipeline orchestrator (461 lines) |
| `mcp_server/supabase_client.py` | Added `update_submission_auto_check()` |
| `mcp_server/api/routers/workers.py` | Wired pipeline into `submit_work()` |
| `mcp_server/api/routers/submissions.py` | Fixed `pre_check_score` to use real data |
| `mcp_server/server.py` | Added auto-check to `format_submission_markdown()` |
| `mcp_server/tests/test_verification_pipeline.py` | **NEW** — 60 tests |

### Frontend (TypeScript/React)
| File | Change |
|------|--------|
| `dashboard/src/types/database.ts` | Added 7 missing EvidenceTypes |
| `dashboard/src/components/SubmissionForm.tsx` | Category-aware evidence + guidance banner |
| `dashboard/src/components/SubmissionReviewModal.tsx` | Auto-check details + visual evidence |

---

## Future Phases (Enhancements, NOT Required)

These phases improve verification quality but are **not needed for the system to function**:

### Phase 3: Multimodal AI Verification (P1)
- Gemini 3 Flash for semantic evidence analysis ($0.25/1K verifications)
- CLIP similarity scoring as fast pre-filter
- Image quality gate (BRISQUE — reject blurry/dark)
- AI-generated content detection
- Confidence-based auto-approve threshold

### Phase 4: On-Chain Attestation + Disputes (P1)
- EAS (Ethereum Attestation Service) schema on Base for task completions
- x402r Arbiter integration for AI pre-screening of disputes
- Kleros Court as final escalation layer
- Commitment hashes for verifiable AI decisions

### Phase 5: Advanced Verification (P2)
- C2PA photo provenance validation
- OCR for receipts/documents (EasyOCR + Donut)
- Reverse image search for high-value tasks
- ZK location proofs (privacy-preserving GPS)
- World ID for Sybil resistance

---

## Test Coverage

```
mcp_server/tests/test_verification_pipeline.py — 60 tests, 0.52s

TestVerificationResult        (2 tests)  — Serialization
TestParseDatetime             (6 tests)  — ISO, Z suffix, naive, garbage
TestExtractGPS               (11 tests)  — 7 GPS formats + edge cases
TestSchemaCheck               (5 tests)  — No schema, present, missing, partial
TestGPSCheck                  (6 tests)  — Range, category thresholds, missing
TestTimestampCheck            (5 tests)  — Deadline, past, no data
TestEvidenceHashCheck         (5 tests)  — No hash, sha256, multiple fields
TestMetadataCheck             (6 tests)  — Bare, forensic, rich, cap at 1.0
TestVerificationPipeline     (14 tests)  — Full integration, edge cases
```
