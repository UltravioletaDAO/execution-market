---
date: 2026-04-14
tags:
  - type/concept
  - domain/security
  - domain/infrastructure
status: active
aliases: [magika-flow, verification-pipeline]
related-files:
  - mcp_server/verification/magika_validator.py
  - mcp_server/verification/background_runner.py
  - mcp_server/verification/ai_review.py
  - mcp_server/integrations/arbiter/consensus.py
  - mcp_server/integrations/arbiter/service.py
---

# Magika → Ring 1 → Ring 2: Flujo Completo de Verificación de Evidencia

Diagrama completo del pipeline de verificación de evidencia en Execution Market,
desde la detección de tipo de archivo (Magika) hasta el veredicto final del árbitro dual.

---

## Diagrama

```mermaid
flowchart TD
    %% ── Entrada ──────────────────────────────────────────────────────────
    SUB([Submission recibida\nsubmission_id + evidence URLs])

    SUB --> DL

    subgraph PHASE_B ["PHASE B — Background Runner (async, post-HTTP-response)"]
        direction TB

        %% ── Download ─────────────────────────────────────────────────────
        DL["📥 download_images_to_temp()\nDescarga cada URL a /tmp/\nGuarda extensión del Content-Type"]

        DL --> FLAG

        %% ── Magika Step ──────────────────────────────────────────────────
        subgraph MAGIKA ["🔍 Magika — Content-Type Validation (Fase 2)"]
            direction TB
            FLAG{"platform_config\nfeature.magika\n.enabled?"}
            FLAG -- "false (default)" --> SKIP["⏭ Skip Magika\nskipped_reason=feature_disabled\nTodos los archivos pasan"]
            FLAG -- "true" --> LOAD["MagikaValidator.get_instance()\nModelo ONNX cargado en startup\n~300ms warmup amortizado"]
            LOAD --> LOOP

            subgraph LOOP ["Por cada archivo descargado"]
                direction LR
                BYTES["Leer bytes del archivo\n(no extensión, no header)"]
                DETECT["magika.identify_bytes()\ndetected_mime\nconfidence = res.score"]
                SCORE["_compute_fraud_score()"]
                BYTES --> DETECT --> SCORE
            end

            SCORE --> FRAUD_TABLE

            subgraph FRAUD_TABLE ["Tabla de Fraud Score"]
                direction TB
                F00["0.0 — Clean match + confidence ≥ 0.85"]
                F03["0.3 — Benign mismatch\n(ej: WebP declarado como JPEG)"]
                F05["0.5 — Match pero baja confianza\n(posible polyglot < 0.85)"]
                F08["0.8 — Mismatch peligroso\n(ej: PDF renombrado como .jpg)"]
                F10["1.0 — Tipo fuera del whitelist\n(ejecutable, script, ZIP)"]
            end

            FRAUD_TABLE --> BLOCK_CHECK{"fraud_score\n≥ 0.8?"}
            BLOCK_CHECK -- "Sí" --> REJECTED["❌ Archivo RECHAZADO\nExcluido de verificación\nNo llega al LLM"]
            BLOCK_CHECK -- "No" --> VALIDATED["✅ Archivo VALIDADO\n(incluso con benign mismatch)"]

            VALIDATED --> MAGIKA_CTX["magika_context: Dict[url → MagikaResult]\nInyectado al prompt LLM"]
            REJECTED --> MAGIKA_PAYLOAD
            MAGIKA_CTX --> MAGIKA_PAYLOAD["magika_detections payload\n→ submissions.magika_detections JSONB\n→ CloudWatch MagikaRejectionRate"]

            CIRCUIT["⚡ Circuit Breaker\nCualquier excepción → imagen pasa\n(fail open, nunca bloquea verificación)"]
        end

        %% ── Ring 1 ───────────────────────────────────────────────────────
        MAGIKA_CTX --> RING1

        subgraph RING1 ["💎 Ring 1 — PHOTINT Verification (5 checks paralelos)"]
            direction TB

            AI["🤖 ai_semantic\nLLM multimodal (GPT-4o / Claude / Gemini)\nPrompt PHOTINT por categoría\n+ sección Magika forensic inline"]
            TAMP["🔬 tampering\nAnálisis de píxeles\nELA / clone stamp / inconsistencias"]
            GENAI["🤖 genai_detection\nDetección de imagen generada por IA\nTexturas imposibles / geometría"]
            SRC["📸 photo_source\nCámara directa vs. screenshot vs. descargada"]
            DUP["🔁 duplicate\nHash perceptual contra submissions previas"]

            AI & TAMP & GENAI & SRC & DUP --> MERGE["merge_check_results()\nPeso A=0.50 + B=0.50\nScore combinado 0.0–1.0"]
        end

        %% ── Ring 2 ───────────────────────────────────────────────────────
        MERGE --> RING2

        subgraph RING2 ["⚖️ Ring 2 — Arbiter Dual-Ring Consensus"]
            direction TB

            BUILD_R1["_build_ring1_score(submission)\nExtrae scores de Phase A + Phase B\nScore combinado + confidence"]

            EXTRACT["_extract_magika_signals(submission)\nLee submission.magika_detections\nFiltra entries con fraud_score > 0"]

            BUILD_R1 --> RING_SCORE["RingScore(ring1)\n.score = combined\n.magika_fraud_signals = [...]"]
            EXTRACT --> RING_SCORE

            RING_SCORE --> PENALTY

            subgraph PENALTY ["🔻 _apply_magika_penalty()"]
                direction LR
                P_CHECK{"max_fraud_score\nen signals?"}
                P_CHECK -- "≥ 0.8" --> P30["score × 0.70\n−30% penalty\nnota en reason"]
                P_CHECK -- "≥ 0.4" --> P15["score × 0.85\n−15% penalty\nnota en reason"]
                P_CHECK -- "< 0.4 o vacío" --> P0["Sin cambio"]
                NOTE["⚠️ REGLA CRÍTICA\nMagika NUNCA causa FAIL directo\nSolo penaliza el score\nDecisión final es del consensus"]
            end

            PENALTY --> TIER["TierRouter\nbounty_usd → cheap/standard/max"]

            TIER -- "cheap\n(bounty bajo)" --> CHEAP["Solo Ring 1\nUmbral de score"]
            TIER -- "standard\n(bounty medio)" --> STD["Ring 1 + 1 LLM Ring 2\nAcuerdo → PASS/FAIL\nDesacuerdo → INCONCLUSIVE"]
            TIER -- "max\n(bounty alto / disputado)" --> MAX["Ring 1 + 2 LLMs Ring 2\n3/3 → decisión firme\n2/3 → conservador"]

            CHEAP & STD & MAX --> CONSENSUS["DualRingConsensus.decide()"]
        end

        CONSENSUS --> VERDICT
    end

    %% ── Veredicto ────────────────────────────────────────────────────────
    subgraph VERDICT ["📋 Veredicto Final"]
        direction LR
        PASS["✅ PASS\nLiberar escrow → worker"]
        FAIL["❌ FAIL\nRefundar escrow → agent"]
        INCON["⚠️ INCONCLUSIVE\nEscalar a árbitro humano (L2)"]
    end

    %% ── Persistencia ─────────────────────────────────────────────────────
    MAGIKA_PAYLOAD --> DB1[(submissions\n.magika_detections JSONB\n.magika_max_fraud_score computed)]
    MAGIKA_PAYLOAD --> CW[("☁️ CloudWatch\nMagikaRejectionRate\nAlarma si > 5% en 10 min")]

    VERDICT --> DB2[(submissions\n.arbiter_verdict\n.arbiter_grade\n.arbiter_summary)]

    %% ── Estilos ──────────────────────────────────────────────────────────
    classDef magika fill:#1a1a2e,stroke:#e94560,color:#fff
    classDef ring1 fill:#16213e,stroke:#0f3460,color:#fff
    classDef ring2 fill:#0f3460,stroke:#533483,color:#fff
    classDef pass fill:#1b4332,stroke:#40916c,color:#fff
    classDef fail fill:#641220,stroke:#e63946,color:#fff
    classDef warn fill:#5c4a00,stroke:#ffd60a,color:#fff
    classDef db fill:#2d2d2d,stroke:#888,color:#ccc

    class MAGIKA magika
    class RING1 ring1
    class RING2 ring2
    class PASS pass
    class FAIL fail
    class INCON warn
    class DB1,DB2 db
```

---

## Resumen del Flujo

### 1. Magika (Pre-verificación)

Corre **antes** de los 5 checks paralelos. Opera sobre bytes reales del archivo — no sobre extensión ni HTTP headers.

| Fraud Score | Significado | Acción |
|-------------|-------------|--------|
| `0.0` | Match limpio, alta confianza | Pasa |
| `0.3` | Benign mismatch (misma familia: WebP→JPEG) | Pasa con warning |
| `0.5` | Confianza baja (posible polyglot) | Pasa con nota al LLM |
| `0.8` | Mismatch peligroso (PDF→JPEG) | **Bloqueado** |
| `1.0` | Tipo fuera del whitelist (ejecutable, script) | **Bloqueado** |

**Circuit breaker**: cualquier excepción en Magika → imagen pasa (fail open). Nunca bloquea verificación.

**Feature flag**: `platform_config.feature.magika.enabled` — se puede desactivar en < 30s sin redeploy.

---

### 2. Ring 1 — PHOTINT

5 checks corren en paralelo. El check `ai_semantic` recibe el `magika_context` inyectado en el prompt como sección de forensics:

```
## FILE TYPE FORENSICS (Magika Content Analysis)
ALERT: File type mismatch detected for 'photo.jpg':
  - Declared: image/jpeg
  - Detected by content analysis: application/pdf
  - Fraud signal: HIGH (score: 0.8/1.0)
  This is strong evidence of deliberate file manipulation.
  Weight this heavily in your authenticity assessment.
```

---

### 3. Ring 2 — Arbiter Consensus

El árbitro recibe los scores de Ring 1 **penalizados** por Magika:

```
ring1.score = 0.85  →  después de penalización (fraud=0.8) → 0.85 × 0.70 = 0.595
```

Esto hace que el consensus sea más conservador sin llegar a un FAIL forzado.

**Tiers:**
- **CHEAP**: solo Ring 1 penalizado. Umbral de score.
- **STANDARD**: Ring 1 + 1 LLM Ring 2. Acuerdo → decisión. Desacuerdo → INCONCLUSIVE.
- **MAX**: Ring 1 + 2 LLMs Ring 2. Votación 3-way. Conservador en empates.

---

### 4. Persistencia y Monitoreo

- `submissions.magika_detections`: payload JSONB con detalle por archivo.
- `submissions.magika_max_fraud_score`: columna computada (B-tree indexable).
- `CloudWatch MagikaRejectionRate`: alerta si > 5% de archivos rechazados en 10 min.
- `platform_config.feature.magika`: toggle en tiempo real sin redeploy.
