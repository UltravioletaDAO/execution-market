---
date: 2026-02-26
tags:
  - domain/security
  - verification/fraud
  - testing/security
status: active
aliases:
  - Anti-Fraud
  - GPS Antispoofing
  - Fraud Checks
related-files:
  - mcp_server/security/
  - mcp_server/verification/checks/
---

# Fraud Detection

Six modular verification checks that detect fraudulent or manipulated evidence submissions. Part of the VERIFYING stage in the [[task-lifecycle]].

## Check Modules

Located in `mcp_server/verification/checks/` and `mcp_server/security/`.

### 1. GPS Antispoofing

Detects spoofed GPS coordinates in geotagged evidence.

| Signal | Detection |
|--------|-----------|
| Impossible speed | Location change faster than physically possible |
| Altitude mismatch | GPS altitude inconsistent with known terrain |
| Accuracy anomaly | Reported accuracy too perfect (0.0m) or too poor |
| Known spoof apps | Metadata signatures from common GPS spoofing apps |
| Coordinate rounding | Fake coordinates often have suspiciously round numbers |

### 2. Timestamp Validation

Verifies evidence was created within the task's time window.

- EXIF `DateTimeOriginal` must fall between task creation and deadline
- Clock skew tolerance: +/- 5 minutes
- Missing timestamps flagged (not rejected -- some cameras strip EXIF)

### 3. Image Tampering (EXIF)

Analyzes image metadata for signs of editing.

| Red Flag | Description |
|----------|-------------|
| Software tags | `Photoshop`, `GIMP`, `AI` in EXIF software field |
| Missing EXIF | Original photos have EXIF; edited ones often lose it |
| Resolution mismatch | Reported vs actual pixel dimensions differ |
| Compression artifacts | Re-saved JPEGs show double-compression patterns |

### 4. Duplicate Detection (Hash)

SHA-256 + perceptual hash lookup against submissions table. Catches exact reuse and near-duplicates (cropped, resized, color-shifted).

### 5. Behavioral Analysis

Cross-submission patterns: rapid-fire submissions (seconds apart), same GPS for different task locations, identical file sizes, sequential filenames. Scored by suspicion level (high/medium/low).

### 6. AI Content Detection

Detects AI-generated images (DALL-E/Midjourney/SD artifacts) and text (perplexity analysis, repetition). Score 0-100, threshold configurable per task category.

## Test Coverage

61 security-focused tests (`pytest -m security`):
- GPS antispoofing edge cases
- Timestamp boundary conditions
- Known spoofing app signatures
- Duplicate detection with variations

## Related

- [[evidence-verification]] -- Full verification pipeline
- [[rls-policies]] -- Database-level access control
- [[task-lifecycle]] -- VERIFYING state where checks run
- [[chainwitness]] -- Complementary on-chain attestation
