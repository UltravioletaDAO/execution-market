# Evidence Verification Layer — Comprehensive Research Report

**Date**: 2026-02-24
**Author**: Claude Code Research Team (4 parallel agents)
**Status**: Research Complete — Ready for Architecture Design

---

## Executive Summary

Evidence verification is the **most critical missing module** in Execution Market. Without it, task completion relies entirely on manual agent review — unscalable and trust-dependent. This report synthesizes research from 4 parallel investigations:

1. **x402r-arbiter-eigencloud** analysis (BackTrack's dispute resolution system)
2. **Open-source verification tools** catalog (GitHub, 80+ tools evaluated)
3. **AI verification services & protocols** (centralized + decentralized)
4. **Current EM evidence system** audit (code analysis of existing implementation)

### Key Finding

**EM already has ~3,500 lines of verification code that is NOT connected to the live submission flow.** Modules for AI review, GPS anti-spoofing, genAI detection, image tampering, and fraud detection exist but are standalone. The highest-impact work is **wiring existing modules**, not building new ones.

### The Problem Space

```
                           EVIDENCE TYPES
                    +--------------------------+
                    |  Photos (geo-tagged)     |  physical_presence
                    |  Screenshots             |  digital_physical
                    |  Documents/Receipts      |  simple_action, knowledge_access
                    |  GPS coordinates         |  physical_presence
                    |  Text/Measurements       |  research, data_processing
                    |  Videos                  |  any category
                    |  API responses           |  api_integration
                    |  Code output             |  code_execution
                    +--------------------------+

                          VERIFICATION NEEDS
                    +--------------------------+
                    |  Is this photo real?      |  (not AI-generated, not stock)
                    |  Was worker there?        |  (GPS matches task location)
                    |  Was it done on time?     |  (timestamp within deadline)
                    |  Is evidence complete?    |  (all required types present)
                    |  Does it match the task?  |  (semantic verification)
                    |  Is it tampered?          |  (EXIF consistency, ELA)
                    |  Is it unique?            |  (not reused from other tasks)
                    |  Who disputes?            |  (dispute resolution protocol)
                    +--------------------------+
```

---

## Table of Contents

1. [Current State of EM Evidence System](#1-current-state-of-em-evidence-system)
2. [x402r Arbiter Analysis](#2-x402r-arbiter-eigencloud-analysis)
3. [Open-Source Verification Tools Catalog](#3-open-source-verification-tools-catalog)
4. [AI Verification Services & APIs](#4-ai-verification-services--apis)
5. [Decentralized Verification Protocols](#5-decentralized-verification-protocols)
6. [Attestation & Proof Protocols](#6-attestation--proof-protocols)
7. [Dispute Resolution Protocols](#7-dispute-resolution-protocols)
8. [Content Authenticity Standards](#8-content-authenticity-standards)
9. [Industry Benchmarks (How Others Do It)](#9-industry-benchmarks)
10. [UX Issues & Desktop Worker Support](#10-ux-issues--desktop-worker-support)
11. [Recommended Architecture](#11-recommended-architecture)
12. [Implementation Roadmap](#12-implementation-roadmap)

---

## 1. Current State of EM Evidence System

### Architecture (As-Is)

```
Worker (Dashboard)                    Backend (MCP Server)                    Agent/Publisher
-----------------                    -------------------                    ---------------
SubmissionForm.tsx                   POST /tasks/{id}/submit                ReviewSubmission.tsx
  |-- EvidenceUpload.tsx             (workers.py:submit_work)               (RAW JSON display)
  |   |-- CameraCapture.tsx              |
  |   |-- GPSCapture.tsx                 |-- db.submit_work()
  |   |-- EvidenceVerification.tsx       |-- instant payout check
  |                                      |-- webhook dispatch
  |-- File upload (evidence.ts)
  |   |-- S3 presigned URL (primary)
  |   |-- Supabase Storage (fallback)
  |
  |-- Text/measurement input          Verification modules (MOSTLY STANDALONE):
                                       |-- ai_review.py              (partially integrated)
                                       |-- gps_antispoofing.py       (NOT integrated)
                                       |-- checks/gps.py             (NOT integrated)
                                       |-- checks/genai.py           (NOT integrated)
                                       |-- checks/timestamp.py       (NOT integrated)
                                       |-- checks/tampering.py       (NOT integrated)
                                       |-- checks/photo_source.py    (NOT integrated)
                                       |-- checks/duplicate.py       (NOT integrated)
                                       |-- checks/schema.py          (NOT integrated)
                                       |-- security/fraud_detection.py (NOT integrated)
```

### Key Files

| File | Purpose | Status |
|------|---------|--------|
| `dashboard/src/components/SubmissionForm.tsx` | Main submission orchestrator | Active, L104-106: forensic metadata on mount |
| `dashboard/src/components/evidence/EvidenceUpload.tsx` | Camera/GPS/file for photo types | Active, L352-374: client-side GPS check |
| `dashboard/src/components/evidence/CameraCapture.tsx` | Camera via getUserMedia() | Active, mobile detection via UA regex |
| `dashboard/src/components/evidence/GPSCapture.tsx` | Geolocation API | Active, Yandex static maps preview |
| `dashboard/src/components/evidence/EvidenceVerification.tsx` | Display-only verification badges | **Cosmetic only** — client-side, easily bypassed |
| `dashboard/src/pages/publisher/ReviewSubmission.tsx` | H2A review page | **Raw JSON display** — no image previews |
| `mcp_server/verification/ai_review.py` | Multi-provider AI image review | **Partially integrated** via `/api/v1/evidence/verify` |
| `mcp_server/verification/gps_antispoofing.py` | 5-method GPS spoofing detection | **NOT integrated** — standalone, in-memory profiles |
| `mcp_server/verification/checks/gps.py` | Haversine distance check | **NOT integrated** — available but never called |
| `mcp_server/verification/checks/genai.py` | AI-generated image detection | **NOT integrated** — requires local file paths |
| `mcp_server/security/fraud_detection.py` | Multi-signal fraud detection | **NOT integrated** — standalone, in-memory data |
| `mcp_server/models.py` | 17 EvidenceTypes, 11 TaskCategories | `SubmitWorkInput.evidence` is generic Dict |

### Critical Issues Found

| # | Issue | Impact | File:Line |
|---|-------|--------|-----------|
| 1 | **ReviewSubmission renders raw JSON** | Agent can't visually review photos | `ReviewSubmission.tsx:86-88` |
| 2 | **Payment auth uses placeholder strings** | H2A approval can't trigger real payments | `ReviewSubmission.tsx:47-48` |
| 3 | **Camera-only blocks desktop users** | Remote/digital workers can't submit | `EvidenceUpload.tsx` (requireCamera default) |
| 4 | **GPS blocks camera access** | Workers in weak GPS areas can't capture | `EvidenceUpload.tsx:549` |
| 5 | **No server-side evidence schema validation** | Empty/garbage evidence accepted | `models.py` (Dict type) |
| 6 | **No server-side GPS validation** | GPS spoofing undetected | `workers.py:submit_work()` |
| 7 | **Verification badges are cosmetic** | False sense of security | `EvidenceVerification.tsx` |
| 8 | **No EXIF extraction from uploaded files** | Metadata lost on file upload | `evidence.ts` |
| 9 | **EvidenceType enum mismatch** | 6 types missing from frontend | `database.ts` vs `models.py` |
| 10 | **Fraud profiles in-memory only** | Lost on restart | `gps_antispoofing.py`, `fraud_detection.py` |
| 11 | **No automated verification on submission** | Everything relies on manual review | `workers.py:submit_work()` |
| 12 | **auto_check_passed column never populated** | DB fields exist but unused | `submissions` table |

### Evidence Type Coverage by Task Category

| Category | Required Evidence | Frontend Support | Backend Validation |
|----------|-------------------|------------------|-------------------|
| `physical_presence` | photo_geo, timestamp | Camera + GPS works | **None** |
| `knowledge_access` | photo, document, text | Camera + text works | **None** |
| `human_authority` | notarized, signature, document | File upload works | **None** |
| `simple_action` | photo, receipt, video | Camera + file works | **None** |
| `digital_physical` | photo, screenshot, document | Camera + file works | **None** |
| `data_processing` | json_response, structured_data | **No frontend support** | **None** |
| `api_integration` | api_response, json_response | **No frontend support** | **None** |
| `content_generation` | text_response, file_artifact | Partial (text only) | **None** |
| `code_execution` | code_output, file_artifact | Partial (text only) | **None** |
| `research` | text_response, url_reference, document | Partial (text + doc) | **None** |

---

## 2. x402r Arbiter (EigenCloud) Analysis

### Overview

| Field | Value |
|-------|-------|
| **Repo** | [BackTrackCo/x402r-arbiter-eigencloud](https://github.com/BackTrackCo/x402r-arbiter-eigencloud) |
| **Language** | TypeScript (97.8%) |
| **License** | MIT |
| **Status** | Hackathon demo ("not for production") |
| **Created** | 2026-02-15 |
| **Infrastructure** | EigenCloud TEE + EigenAI (deterministic LLM inference) |

### Architecture

The arbiter is a **verifiable AI-powered dispute resolver** running inside an EigenCloud Trusted Execution Environment (TEE). It uses EigenAI for deterministic LLM inference to adjudicate payment disputes.

```
1. WATCH   --> Monitor blockchain for RefundRequested events
2. FETCH   --> Retrieve evidence from RefundRequestEvidence contract (IPFS CIDs)
3. DECIDE  --> EigenAI inference with fixed seed (deterministic, reproducible)
4. COMMIT  --> Record decision hash on-chain (promptHash + seed + responseHash)
5. EXECUTE --> Approve or deny refund via x402r SDK
```

**Commitment Hash (Verifiability Core)**:
```
commitmentHash = keccak256(encodePacked(
  keccak256(prompt),
  keccak256(response),
  BigInt(seed)
))
```
Anyone can replay the same prompt + seed on EigenAI and verify the ruling matches the on-chain hash.

### 5 Components

| Component | Purpose |
|-----------|---------|
| **Arbiter Server** (`src/index.ts`) | Express API, watches chain events, evaluates disputes |
| **EigenAI Client** (`src/eigenai-client.ts`) | Authenticated client for deterministic inference |
| **Facilitator Server** (`src/facilitator-server.ts`) | Verifies/settles x402r escrow payments |
| **Merchant Bot** (`src/merchant-bot.ts`) | Auto-submits counter-evidence on disputes |
| **Court UI** (`court-ui/`) | Next.js dashboard for dispute visualization |

### Integration Assessment

| Capability | x402r Arbiter | EM Needs | Gap |
|------------|---------------|----------|-----|
| Payment dispute (refunds) | Yes | Yes | **Aligned** |
| Evidence storage | IPFS CIDs on-chain | S3 + CloudFront | Different, bridgeable |
| Evidence types | Text/JSON blobs | Photos, GPS, documents, EXIF | **Major gap** (text-only) |
| AI evaluation | Text-only (`gpt-oss-120b-f16`) | Needs multimodal (vision) | **Major gap** |
| Verifiability | Commitment hash on-chain | Desired | **Strong match** |
| On-chain execution | x402r escrow refund | x402r escrow (Fase 5) | **Same infrastructure** |
| Multi-chain | 3 chains (Base, Sepolia) | 8 mainnets | Needs expansion |
| Dispute categories | Generic (delivered or not) | 9 categories with rubrics | Needs richer taxonomy |
| Arbitration panel | Single AI | EM has 3-arbitrator panel | EM is more sophisticated |
| Reputation integration | None | Bayesian scoring + ERC-8004 | Missing |

### What to Adopt

1. **Commitment hash pattern** (high value, low effort) — Store keccak256(prompt + seed + response) for every automated verification decision
2. **AI pre-screening layer** (high value, medium effort) — Screen disputes with AI before human escalation
3. **Evidence format** (useful reference) — Chronological timeline with roles and timestamps

### What NOT to Adopt

- Do NOT use as-is for production (hackathon quality)
- Do NOT depend on EigenAI availability for critical payment decisions
- Do NOT replace S3/CloudFront with IPFS-only evidence storage

---

## 3. Open-Source Verification Tools Catalog

### 3.1 Image Tampering & Forensics

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[Sherloq](https://github.com/GuidoBartoli/sherloq)** | ~2.8k | GPL-3.0 | Python | ELA, copy-move detection, EXIF consistency, noise analysis, JPEG ghost | **Primary** forensics suite |
| **[Imago Forensics](https://github.com/redaelli/imago-forensics)** | ~500 | GPL-3.0 | Python | ELA, hash inconsistencies, CLI batch processing | Batch evidence analysis |
| **[forensic](https://github.com/esimov/forensic)** | ~400 | MIT | Go | Copy-move forgery via invariant features | Fast processing alternative |

### 3.2 Deepfake / AI-Generated Detection

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[DeepSafe](https://github.com/siddharthksah/DeepSafe)** | ~200 | — | Python/Docker | Ensemble deepfake detection, microservices | Catch AI-generated evidence |
| **[DeepfakeBench](https://github.com/SCLBD/DeepfakeBench)** | ~1k | — | Python/PyTorch | 15+ detection methods benchmark | Model selection reference |
| **[Awesome-Deepfakes-Detection](https://github.com/Daisy-Zhang/Awesome-Deepfakes-Detection)** | ~1.5k | — | — | Curated list of all detection papers/tools | Master reference |

### 3.3 Image Deduplication & Reverse Search

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[imagededup](https://github.com/idealo/imagededup)** | ~5.2k | Apache-2.0 | Python | Perceptual hashing + CNN dedup | Detect recycled evidence |
| **[ImageHash](https://github.com/JohannesBuchner/imagehash)** | ~3.2k | BSD-2 | Python | aHash, pHash, dHash, wHash | Fast duplicate detection |
| **[TinEye API](https://services.tineye.com)** | — | Commercial | REST | Reverse image search (billions indexed) | Detect stock photos |

### 3.4 OCR & Document Understanding

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[Tesseract](https://github.com/tesseract-ocr/tesseract)** | ~72.5k | Apache-2.0 | C++ | 100+ language OCR, LSTM engine | Receipt/document text extraction |
| **[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)** | ~50k+ | Apache-2.0 | Python | SOTA accuracy, PP-OCRv5, table extraction | Best for structured documents |
| **[EasyOCR](https://github.com/JaidedAI/EasyOCR)** | ~28.9k | Apache-2.0 | Python/PyTorch | 80+ languages, 3 lines to use | Scene text (signs, labels) |
| **[Donut](https://github.com/clovaai/donut)** | ~6.5k | MIT | Python/PyTorch | OCR-free document understanding, structured JSON | Receipt/invoice parsing |

### 3.5 Scene & Object Verification

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[CLIP](https://github.com/openai/CLIP)** | ~26k+ | MIT | Python/PyTorch | Zero-shot image-text similarity | "Does photo match task?" |
| **[Grounding DINO](https://github.com/IDEA-Research/GroundingDINO)** | ~7k+ | Apache-2.0 | Python/PyTorch | Open-set object detection by text | "Is there a receipt in this photo?" |
| **[Places365](https://github.com/CSAILVision/places365)** | ~2.7k | — | Python/PyTorch | 365 scene categories | Verify scene matches task |

### 3.6 Image Quality Assessment

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[IQA-PyTorch](https://github.com/chaofengc/IQA-PyTorch)** | ~2k | Apache-2.0 | Python/PyTorch | BRISQUE, NIMA, MUSIQ, NIQE | Reject blurry/dark photos |

### 3.7 GPS & Geospatial

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[Tile38](https://github.com/tidwall/tile38)** | ~8.6k | MIT | Go | Geospatial DB with real-time geofencing | Task location verification |
| **[PostGIS](https://postgis.net/)** | — | GPL-2.0 | C/SQL | Spatial extension for PostgreSQL | `ST_DWithin` on Supabase |
| **[Shapely](https://github.com/shapely/shapely)** | ~4k+ | BSD-3 | Python | Geometric operations | Point-in-polygon checks |
| **[FIND3](https://github.com/schollz/find3)** | ~5k+ | MIT | Go+Python | WiFi fingerprint indoor positioning | Indoor task verification |

### 3.8 Proof-of-Location Protocols

| Protocol | Token | License | What It Does | EM Use |
|----------|-------|---------|-------------|--------|
| **[XYO Network](https://github.com/XYOracleNetwork)** | XYO | Various | Bound Witness location proofs | Physical co-location proof |
| **[FOAM](https://www.foam.space/)** | FOAM | Open | Radio beacon triangulation | GPS-independent verification |
| **POLP** | — | — | ZK location proofs (snarkjs) | Privacy-preserving location |

### 3.9 Content Provenance (C2PA)

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[c2pa-rs](https://github.com/contentauth/c2pa-rs)** | ~276 | MIT+Apache | Rust | Create/validate Content Credentials | Cryptographic photo provenance |
| **[c2pa-python](https://github.com/contentauth/c2pa-python)** | ~100 | MIT+Apache | Python | Python bindings for c2pa-rs | Integrate into MCP server |

### 3.10 Crowdsource Quality Control

| Tool | Stars | License | Language | What It Does | EM Use |
|------|-------|---------|----------|-------------|--------|
| **[Crowd-Kit](https://github.com/Toloka/crowd-kit)** | ~200 | Apache-2.0 | Python | Dawid-Skene, GLAD, MACE algorithms | Multi-worker consensus |

---

## 4. AI Verification Services & APIs

### Cost Comparison (per 1,000 image verifications)

| Provider | Model | Input Cost | Est. Cost/1K | Best For |
|----------|-------|-----------|-------------|----------|
| Google | Gemini 2.5 Flash Lite | $0.10/1M tokens | ~$0.05 | Budget verification |
| Google | Gemini 3 Flash | $0.50/1M tokens | ~$0.25 | Best cost/quality |
| Anthropic | Claude Haiku 4.5 | $1/1M tokens | ~$0.50 | Fast reasoning |
| OpenAI | GPT-4o (low detail) | $2.50/1M tokens | ~$0.85 | General purpose |
| Anthropic | Claude Sonnet 4.5 | $3/1M tokens | ~$1.50 | Strong reasoning |
| AWS | Rekognition | $0.001/image | ~$1.00 | Label/object detection |
| Google | Cloud Vision API | $1.50/1K images | ~$1.50 | Landmark + web detection |

### Specialized Detection Services

| Service | What It Does | Pricing | AI-Gen Detection? |
|---------|-------------|---------|-------------------|
| **[Sightengine](https://sightengine.com)** | Moderation + AI detection | $29-399/mo | Yes |
| **[Hive AI](https://thehive.ai)** | 25+ moderation classes | Usage-based | Yes |
| **[Sensity AI](https://sensity.ai)** | Forensic deepfake detection | $29/mo+ | Yes (98% accuracy) |
| **[AWS Rekognition](https://aws.amazon.com/rekognition/)** | Labels, OCR, faces, moderation | $0.001/image | No |

### Open-Source VLMs (Self-Hosted)

| Model | Parameters | GPU Needed | Monthly Cost | Quality |
|-------|-----------|-----------|-------------|---------|
| Qwen 2.5 VL 72B | 72B | 2x A100 80GB | ~$2,160 | SOTA open-source |
| Qwen 2.5 VL 7B | 7B | 1x A100 40GB | ~$1,080 | Good for basic tasks |
| LLaVA-OneVision 1.5 | 7B-72B | Varies | Varies | Competitive |
| Phi-4 Multimodal | 14B | 1x A100 | ~$1,080 | Efficient |

---

## 5. Decentralized Verification Protocols

### Comparison Matrix

| Protocol | Mechanism | Maturity | EM Relevance | Integration |
|----------|-----------|----------|-------------|-------------|
| **EigenCloud/EigenVerify** | TEE + restaked ETH ($17B+) | Alpha (mainnet June 2025) | **10/10** — x402r Arbiter built on this | High effort, natural path |
| **Ritual (Infernet)** | 8K+ nodes, ZK/TEE/optimistic | Production (8K nodes) | **8/10** — on-chain verifiable AI | Medium-High |
| **ORA (opML)** | Optimistic ML + fraud proofs | Production (Ethereum) | **7/10** — pragmatic approach | Medium |
| **Hyperbolic (PoSP)** | Proof-of-Sampling + EigenLayer | Production (funded $20M) | **7/10** — decentralized GPU for VLMs | Medium |
| **Giza (ZKML)** | STARK proofs on Starknet | Beta | **5/10** — Starknet only, not EVM | High |
| **Modulus Labs (ZKML)** | ZK proofs for ML (18M params max) | Research | **4/10** — too small for vision models | Very High |

### Recommended Path

```
Near-term:  Centralized AI (Gemini/Claude) with commitment hashes for transparency
Mid-term:   ORA opML or Ritual Infernet for on-chain verifiable inference
Long-term:  EigenCloud AVS with x402r Arbiter for full trustlessness
```

---

## 6. Attestation & Proof Protocols

### Ethereum Attestation Service (EAS) — Top Recommendation

| Field | Value |
|-------|-------|
| **URL** | [attest.org](https://attest.org/) |
| **Chains** | Ethereum, Base, Optimism, Polygon, Arbitrum (all EM chains) |
| **Cost** | Gas only (no protocol fee) |
| **License** | MIT |
| **EM Relevance** | **9/10** |

**Proposed Schema**:
```
TaskCompletionAttestation {
  bytes32 taskId,
  address worker,
  bytes32 evidenceHash,
  uint8 verificationScore,    // 0-100
  uint8 verificationMethod,   // 0=manual, 1=AI, 2=oracle, 3=consensus
  bool approved
}
```

Every completed task creates an on-chain attestation on Base. Workers accumulate attestations as **portable, composable, trustless reputation** — complementing ERC-8004.

### Other Attestation Protocols

| Protocol | Difference from EAS | EM Fit |
|----------|-------------------|--------|
| **[Sign Protocol](https://sign.global/)** | Omni-chain (Solana, TON) | 6/10 — less established |
| **[Verax](https://ver.ax/)** | Curated attesters (whitelisted) | 5/10 — Linea-focused |

### Proof-of-Personhood

| Protocol | What It Does | EM Use |
|----------|-------------|--------|
| **[World ID](https://worldcoin.org/)** | Iris-scan proof of unique human | Prevent Sybil attacks on worker side |

---

## 7. Dispute Resolution Protocols

### Comparison

| Protocol | Mechanism | Cost/Dispute | Maturity | EM Relevance |
|----------|-----------|-------------|----------|-------------|
| **[Kleros Court](https://kleros.io/)** | Staked jurors, sortition, appeals | 0.03-0.1 ETH | Production (V2 on Arbitrum) | **9/10** |
| **[UMA Optimistic Oracle](https://uma.xyz/)** | Assume true, dispute with bonds | Bond-based | Production (powers Polymarket) | **7/10** |
| **[Reality.eth](https://reality.eth.limo/)** | Bond escalation + external arbitrator | Bond-based | Production | **6/10** |
| **x402r Arbiter** | AI in TEE + commitment hash | TBD | Hackathon alpha | **10/10** (native) |
| **[Aragon Court](https://github.com/aragon/aragon-court)** | ANT-staked jurors, sortition | Varies | Less active | **3/10** |

### Recommended Strategy: Layered Dispute Resolution

```
Dispute Filed
    |
    v
[Layer 1: AI Pre-Screening] ---- x402r Arbiter or Claude/Gemini
    |                              Confidence > 0.8 --> Auto-resolve
    |                              Confidence < 0.8 --> Escalate
    v
[Layer 2: Mutual Resolution] ---- Both parties submit evidence, negotiate
    |                              Agreement --> Resolve
    |                              No agreement --> Escalate
    v
[Layer 3: Decentralized Court] --- Kleros Court (human jurors, staked)
    |                              Majority verdict --> Enforce
    |                              Appeal --> Larger jury
    v
[Layer 4: On-Chain Execution] ---- x402r escrow refund/release
```

---

## 8. Content Authenticity Standards

### C2PA (Coalition for Content Provenance and Authenticity)

**The future of image authenticity.** Backed by Adobe, Microsoft, Intel, Truepic. ISO standardization expected.

- Cryptographic proof of: capture device, time, location, modification history
- Increasingly supported by smartphones (Samsung, Google Pixel)
- `c2pa-python` library can validate Content Credentials on evidence submission
- If photo has valid C2PA manifest: **auto-boost verification confidence significantly**

### Numbers Protocol

- Blockchain-based photo provenance (67M+ assets registered)
- Used by Reuters for election photo validation
- Workers could use Capture App for provenance-registered evidence
- Seal API for developer integration

### Truepic Lens SDK (Commercial, Premium)

- World's first C2PA-compliant camera SDK
- 35 authenticity tests per capture
- Detects screen re-captures, location spoofing, device tampering
- **Gold standard** for controlled capture — ideal for EM mobile app (future)

---

## 9. Industry Benchmarks

### How Existing Platforms Verify Work

| Platform | Verification Method | Evidence Types | Dispute Resolution |
|----------|-------------------|----------------|-------------------|
| **Uber** | Continuous GPS + periodic face verification + delivery photo + PIN | GPS trail, photo, biometric | Customer support escalation |
| **DoorDash** | Delivery photo (mandatory) + GPS at address + timestamp | GPS, photo, timestamp | Support mediation |
| **TaskRabbit** | Client-side approval (subjective) + chat photos + reviews | Chat, photos, reviews | Support mediation |
| **Fiverr** | Client reviews deliverables + Resolution Center | Digital deliverables | Mutual -> Platform mediation |
| **Amazon MTurk** | Statistical consensus (N workers/task) + approval rates | Task output | Requester rejects |
| **Helium (DePIN)** | Proof-of-Coverage via radio beacons | Radio signals | Slashing |

### Key Insight

> **Human physical task verification remains largely unsolved in web3.** DePIN verifies machine work (hotspots, GPUs, sensors). Gig platforms use centralized verification. EM can be the first to combine decentralized dispute resolution (Kleros/x402r) with AI-powered evidence analysis (multimodal VLMs) for physical task verification.

---

## 10. UX Issues & Desktop Worker Support

### Current Blockers for Remote/Desktop Workers

1. **Camera-only mode** (`EvidenceUpload.tsx`) blocks file upload when `requireCamera=true` (default)
2. **GPS required before camera** (`EvidenceUpload.tsx:549`) for `photo_geo` — desktop has no GPS
3. **No gallery/file upload path** for photo evidence types
4. **No screenshot submission flow** for digital tasks
5. **6 EvidenceTypes missing from frontend** (`json_response`, `api_response`, `code_output`, `file_artifact`, `url_reference`, `structured_data`)
6. **Yandex maps dependency** for GPS preview — unusual for Western product

### Proposed Solution: Task Category-Aware Evidence Collection

```
Task Category          Evidence Requirements         Submission Mode
--------------         ----------------------        ---------------
physical_presence  --> GPS + geo-tagged photo     --> Mobile camera REQUIRED
knowledge_access   --> Document photo/scan        --> Camera OR file upload
human_authority    --> Notarized document          --> File upload (PDF/photo)
simple_action      --> Photo proof + receipt       --> Camera OR file upload
digital_physical   --> Photo + screenshot          --> Mixed (camera + file)
data_processing    --> JSON/structured data        --> Text input + file upload
api_integration    --> API response screenshot     --> File upload + paste
content_generation --> Text/file output            --> Text + file upload
code_execution     --> Code output + artifacts     --> Text + file upload
research           --> Text report + URLs          --> Text + file + URL input
```

**Key change**: Evidence requirements should be **adaptive** based on task category, not one-size-fits-all. Remote/digital tasks should never require GPS or camera.

---

## 11. Recommended Architecture

### Verification Pipeline (To-Be)

```
                                 SUBMISSION
                                     |
                                     v
                        +------------------------+
                        | Layer 0: Schema Check  |  <-- Validate required evidence types present
                        | (checks/schema.py)     |      Reject if missing required types
                        +------------------------+
                                     |
                                     v
                        +------------------------+
                        | Layer 1: Metadata      |  <-- EXIF extraction (GPS, timestamp, device)
                        | Extraction & Validation|      GPS proximity check (haversine)
                        | (checks/gps.py,        |      Timestamp within deadline window
                        |  checks/timestamp.py)  |      Store results in auto_check_details
                        +------------------------+
                                     |
                                     v
                        +------------------------+
                        | Layer 2: Duplicate &   |  <-- Perceptual hash (imagehash/imagededup)
                        | Integrity Check        |      Compare against all previous submissions
                        | (checks/duplicate.py,  |      Reverse image search (optional, high-value)
                        |  checks/tampering.py)  |      Image quality assessment (BRISQUE)
                        +------------------------+
                                     |
                                     v
                        +------------------------+
                        | Layer 3: Authenticity   |  <-- C2PA manifest validation (c2pa-python)
                        | (checks/genai.py,      |      AI-generated detection (Sightengine/Hive)
                        |  checks/photo_source.py)|     Photo source (camera vs screenshot)
                        +------------------------+
                                     |
                                     v
                        +------------------------+
                        | Layer 4: Semantic       |  <-- Multimodal AI (Gemini Flash / Claude Haiku)
                        | Verification            |      "Does this evidence prove task completion?"
                        | (ai_review.py +         |      Structured JSON verdict with confidence score
                        |  CLIP similarity)       |      Task-category-specific prompts
                        +------------------------+
                                     |
                                     v
                        +------------------------+
                        | Layer 5: Fraud Signals  |  <-- GPS anti-spoofing (movement patterns)
                        | (fraud_detection.py,   |      Multi-device fingerprinting
                        |  gps_antispoofing.py)  |      Behavioral anomalies
                        +------------------------+
                                     |
                                     v
                        +------------------------+
                        | Aggregation & Decision  |  <-- Weighted score from all layers
                        +------------------------+      Confidence > 0.95: auto-approve option
                              |          |              Confidence 0.50-0.95: agent review + score
                              v          v              Confidence < 0.50: flag + require review
                         AUTO-APPROVE  MANUAL REVIEW
                              |          |
                              v          v
                        +------------------------+
                        | On-chain Attestation    |  <-- EAS attestation on Base
                        | (commitment hash)       |      Commitment hash for AI decisions
                        +------------------------+
                              |
                              v
                        +------------------------+
                        | DISPUTE (if filed)      |  <-- Layer 1: AI pre-screening (x402r arbiter)
                        |                         |      Layer 2: Mutual resolution
                        |                         |      Layer 3: Kleros Court
                        |                         |      Layer 4: Escrow refund/release
                        +------------------------+
```

### Technology Selection Summary

| Layer | Primary Tool | Fallback | Cost |
|-------|------------|----------|------|
| Schema validation | Custom Python | — | Free |
| EXIF extraction | Pillow + exifread | — | Free |
| GPS validation | PostGIS (Supabase) | Shapely (Python) | Free |
| Duplicate detection | imagehash (pHash) | imagededup | Free |
| Image quality | IQA-PyTorch (BRISQUE) | OpenCV BRISQUE | Free |
| C2PA validation | c2pa-python | — | Free |
| AI-generated detection | Sightengine API | checks/genai.py (local) | $29/mo |
| Semantic verification | Gemini 3 Flash | Claude Haiku 4.5 | ~$0.25/1K |
| Scene classification | CLIP | Places365-CNN | Free |
| Object detection | Grounding DINO | — | Free |
| OCR (receipts/docs) | EasyOCR / PaddleOCR | Tesseract | Free |
| Fraud detection | Enhanced fraud_detection.py | — | Free |
| Attestation | EAS (Base) | — | Gas only |
| Dispute resolution | x402r Arbiter + Kleros | UMA Optimistic Oracle | 0.03-0.1 ETH |
| Content provenance | Numbers Protocol | C2PA | Free-Freemium |

---

## 12. Implementation Roadmap

### Phase 1: Wire Existing Modules (P0 — Highest Impact, Lowest Effort)

No new dependencies. Pure plumbing — connect existing `verification/checks/` modules to `submit_work()`.

| Task | File | What to Do |
|------|------|-----------|
| 1.1 | `mcp_server/api/routers/workers.py` | Call `checks/schema.py` after `db.submit_work()` |
| 1.2 | `mcp_server/api/routers/workers.py` | Call `checks/gps.py` for physical_presence tasks |
| 1.3 | `mcp_server/api/routers/workers.py` | Call `checks/timestamp.py` for all submissions |
| 1.4 | `mcp_server/api/routers/workers.py` | Call `checks/duplicate.py` with SHA-256 comparison |
| 1.5 | `mcp_server/api/routers/workers.py` | Populate `auto_check_passed` + `auto_check_details` |
| 1.6 | `mcp_server/models.py` | Add Pydantic validation for `SubmitWorkInput.evidence` |
| 1.7 | `mcp_server/verification/gps_antispoofing.py` | Persist profiles to DB (not in-memory) |
| 1.8 | `mcp_server/security/fraud_detection.py` | Persist profiles to DB (not in-memory) |

**Validation**: Unit tests for each check + integration test for full pipeline.

### Phase 2: Frontend UX Fixes (P0 — Unblock Desktop Workers)

| Task | File | What to Do |
|------|------|-----------|
| 2.1 | `EvidenceUpload.tsx` | Add gallery/file upload alongside camera |
| 2.2 | `EvidenceUpload.tsx` | Make GPS optional for non-physical tasks |
| 2.3 | `SubmissionForm.tsx` | Task-category-aware evidence requirements |
| 2.4 | `database.ts` | Sync 6 missing EvidenceTypes from backend |
| 2.5 | `ReviewSubmission.tsx` | Replace raw JSON with image previews + map |
| 2.6 | `ReviewSubmission.tsx` | Show auto_check results from Phase 1 |
| 2.7 | `GPSCapture.tsx` | Replace Yandex maps with Mapbox/Leaflet |

### Phase 3: Multimodal AI Verification (P1 — Automated Quality)

| Task | What to Do |
|------|-----------|
| 3.1 | Integrate Gemini 3 Flash as primary verification AI |
| 3.2 | Build task-category-specific verification prompts |
| 3.3 | CLIP similarity scoring as fast pre-filter |
| 3.4 | Add imagehash (pHash) for cross-submission dedup |
| 3.5 | Image quality gate (BRISQUE) — reject blurry/dark |
| 3.6 | AI-generated detection via Sightengine API |
| 3.7 | Implement confidence-based auto-approve threshold |
| 3.8 | Store commitment hash for every AI decision |

### Phase 4: On-Chain Attestation + Dispute Framework (P1)

| Task | What to Do |
|------|-----------|
| 4.1 | Register EAS schema on Base for TaskCompletionAttestation |
| 4.2 | Create attestation on every approved task |
| 4.3 | Integrate x402r Arbiter as AI pre-screening for disputes |
| 4.4 | Implement mutual resolution flow (both parties submit evidence) |
| 4.5 | Kleros Court integration as final escalation |
| 4.6 | On-chain commitment hashes for all AI verification decisions |

### Phase 5: Advanced Verification (P2 — Future)

| Task | What to Do |
|------|-----------|
| 5.1 | C2PA validation via c2pa-python (auto-boost confidence for C2PA photos) |
| 5.2 | Receipt/document parsing via EasyOCR + Donut |
| 5.3 | Reverse image search for high-value tasks |
| 5.4 | Numbers Protocol integration for photo provenance |
| 5.5 | Decentralized AI verification via Ritual or ORA |
| 5.6 | ZK location proofs (privacy-preserving geofencing) |
| 5.7 | World ID for Sybil resistance |
| 5.8 | Truepic Lens SDK in native mobile app |

---

## Sources

### Repositories
- [x402r-arbiter-eigencloud](https://github.com/BackTrackCo/x402r-arbiter-eigencloud)
- [Sherloq](https://github.com/GuidoBartoli/sherloq) | [ImageHash](https://github.com/JohannesBuchner/imagehash) | [imagededup](https://github.com/idealo/imagededup)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | [EasyOCR](https://github.com/JaidedAI/EasyOCR) | [Donut](https://github.com/clovaai/donut)
- [CLIP](https://github.com/openai/CLIP) | [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO) | [Places365](https://github.com/CSAILVision/places365)
- [IQA-PyTorch](https://github.com/chaofengc/IQA-PyTorch) | [DeepSafe](https://github.com/siddharthksah/DeepSafe)
- [c2pa-rs](https://github.com/contentauth/c2pa-rs) | [c2pa-python](https://github.com/contentauth/c2pa-python)
- [Tile38](https://github.com/tidwall/tile38) | [FIND3](https://github.com/schollz/find3) | [Shapely](https://github.com/shapely/shapely)
- [EAS Contracts](https://github.com/ethereum-attestation-service/eas-contracts) | [EAS SDK](https://github.com/ethereum-attestation-service/eas-sdk)
- [Kleros](https://github.com/kleros) | [UMA Protocol](https://github.com/UMAprotocol/protocol)
- [XYO Network](https://github.com/XYOracleNetwork) | [Crowd-Kit](https://github.com/Toloka/crowd-kit)
- [Fleetbase](https://github.com/fleetbase/fleetbase) (proof-of-delivery reference)

### Services & APIs
- [OpenAI API](https://platform.openai.com/docs/pricing) | [Claude Vision](https://platform.claude.com/docs/en/build-with-claude/vision) | [Gemini API](https://ai.google.dev/gemini-api/docs/pricing)
- [AWS Rekognition](https://aws.amazon.com/rekognition/) | [Google Cloud Vision](https://cloud.google.com/vision) | [Sightengine](https://sightengine.com) | [Hive AI](https://thehive.ai)
- [TinEye](https://services.tineye.com) | [Sensity AI](https://sensity.ai) | [Truepic Lens](https://www.truepic.com/c2pa/capture)

### Protocols & Standards
- [EAS](https://attest.org/) | [C2PA](https://c2pa.org/) | [Numbers Protocol](https://numbersprotocol.io/)
- [Kleros](https://kleros.io/) | [UMA](https://uma.xyz/) | [Reality.eth](https://reality.eth.limo/)
- [EigenCloud](https://blog.eigencloud.xyz/) | [Ritual](https://ritual.net/) | [ORA](https://docs.ora.io/) | [Hyperbolic](https://hyperbolic.xyz/)
- [World ID](https://worldcoin.org/) | [FOAM](https://www.foam.space/) | [Sign Protocol](https://sign.global/)

### Articles & Research
- [DePIN: Proof of Physical Work](https://medium.com/technicity/proof-of-physical-work-protocol-encapsulates-real-world-use-cases-a41aee5f6741)
- [AI and the Blockchain Oracle Problem](https://www.frontiersin.org/journals/blockchain/articles/10.3389/fbloc.2025.1682623/full)
- [Decentralized Verification Reshaping Gig Economy](https://www.ainvest.com/news/future-work-decentralized-verification-reshaping-hr-gig-economy-markets-2507/)
- [zk-SNARKs for AI Verification](https://arxiv.org/html/2504.04794v1)
