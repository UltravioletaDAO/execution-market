# Evidence Verification Layer — Status & Architecture

**Date**: 2026-02-24
**Status**: Phase 1 + Phase 2 + Phase 3 COMPLETE — Two-Phase Pipeline in Production

---

## What's Live Now

The evidence verification pipeline runs **automatically on every worker submission**. No configuration needed — it's wired into `POST /api/v1/tasks/{id}/submit`.

### Flow

```
Worker submits evidence
        |
        v
+---------------------------------------------+
|  PHASE A — Sync (<100ms)                    |
|                                             |
|  1. Schema       (15%)  Required fields?    |
|  2. GPS          (15%)  Near task location?  |
|  3. Timestamp    (10%)  Before deadline?     |
|  4. Hash         ( 5%)  Integrity hash?      |
|  5. Metadata     ( 5%)  Device info?         |
|                                             |
|  Subtotal: 50% of final score              |
|  Instant result → API response              |
+-------------+-------------------------------+
              |
              v (asyncio.create_task)
+---------------------------------------------+
|  PHASE B — Async (3-10s)                    |
|                                             |
|  6. AI Semantic  (25%)  Does photo match?    |
|  7. Tampering    (10%)  ELA, EXIF, edits?    |
|  8. GenAI Det.   ( 5%)  AI-generated?        |
|  9. Photo Source ( 5%)  Camera vs gallery?    |
| 10. Duplicate    ( 5%)  Seen this before?    |
|                                             |
|  Subtotal: 50% of final score              |
|  Merges into auto_check_details (phase=AB)  |
|  Auto-approve if score >= 0.95 + conditions  |
+---------------------------------------------+
              |
              v
    Saved to submissions table:
    - auto_check_passed (BOOLEAN)
    - auto_check_details (JSONB, phase "A" → "AB")
    - perceptual_hashes (JSONB)
    - ai_verification_result (JSONB)
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
  (or auto-approved if score >= 0.95)
```

### What Each Check Does

| Check | Weight | Phase | What It Verifies | When It Runs |
|-------|--------|-------|-----------------|--------------|
| **Schema** | 15% | A (sync) | Required evidence fields present | Always |
| **GPS proximity** | 15% | A (sync) | Worker near task location (500m/1000m) | When task has coordinates |
| **Timestamp** | 10% | A (sync) | Submitted before deadline (5min grace) | When task has deadline |
| **Evidence hash** | 5% | A (sync) | SHA-256 integrity hash present | Always (0.5 if absent) |
| **Metadata** | 5% | A (sync) | Device info, timestamps, files, notes | Always |
| **AI Semantic** | 25% | B (async) | Gemini vision: does photo match task? | When images present |
| **Tampering** | 10% | B (async) | ELA, EXIF, compression, resolution | When images present |
| **GenAI Detection** | 5% | B (async) | C2PA, watermarks, AI artifacts | When images present |
| **Photo Source** | 5% | B (async) | Camera vs gallery vs screenshot | When images present |
| **Duplicate** | 5% | B (async) | Perceptual hash dedup | When images present |

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
| `mcp_server/api/routers/workers.py` | Wired Phase A+B pipeline into `submit_work()` |
| `mcp_server/verification/background_runner.py` | **NEW** — Phase B async runner (~300 lines) |
| `mcp_server/verification/image_downloader.py` | **NEW** — Image download utility (~120 lines) |
| `mcp_server/verification/providers.py` | Added `GeminiProvider`, updated fallback chain |
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

### Phase 3: Multimodal AI Verification — COMPLETE
- Google Gemini 2.5 Flash for semantic evidence analysis (~$0.25/1K)
- AI-generated content detection (C2PA, watermarks, artifacts, EXIF)
- Image tampering detection (ELA, compression, software tags)
- Photo source verification (camera vs gallery vs screenshot)
- Perceptual hash dedup across submissions
- Auto-approve at score >= 0.95 (all conditions must pass)
- Commitment hashes for AI decision auditability

**Env vars**: `GOOGLE_API_KEY`, `AI_VERIFICATION_PROVIDER=gemini` (default),
`VERIFICATION_AI_ENABLED=true`, `VERIFICATION_AI_MAX_IMAGES=2`,
`VERIFICATION_AUTO_APPROVE=true`

**Migration**: `039_verification_phase3.sql` (perceptual_hashes, ai_verification_result)

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
mcp_server/tests/test_verification_pipeline.py — 60 tests
  Phase A pipeline: schema, GPS, timestamp, hash, metadata, aggregation

mcp_server/tests/test_verification_phase3.py — ~45 tests
  TestGeminiProvider         (5 tests)  — Availability, analyze, model override, fallback
  TestImageDownloader        (9 tests)  — URL extraction, dedup, download, cleanup
  TestPhaseAWeights          (4 tests)  — Weight sums, backward compat
  TestPhaseBChecks          (10 tests)  — All 5 async checks (pass/fail)
  TestAutoApprove            (5 tests)  — Threshold, already reviewed, missing checks
  TestMergePhaseB            (4 tests)  — Merge, recompute, preserve, phase indicator
  TestCommitmentHash         (2 tests)  — Computed, deterministic
  TestBackgroundRunner       (5 tests)  — Disabled, no photos, download fail, cleanup, phase
```
