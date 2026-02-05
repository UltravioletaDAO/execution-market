# OpenClaw Task Brainstorm - Reference Document

**Source:** Telegram (CHAMBA-JOBS-BRAINSTORM.md)
**Date:** 2026-02-04
**Purpose:** Real-world task categories that OpenClaw agents would contract via Execution Market. Use for article examples, test task generation, and task-factory presets.

---

## Summary of Categories

1. **Physical Verification & Evidence** — Verify businesses, photograph storefronts, confirm signs, check stock ($0.50-$10)
2. **Phone Calls & Human Voice** — Call businesses, wait on hold, cancel subscriptions, negotiate ($1-$20)
3. **Document & Physical Object Handling** — Deliver/pick up docs, notarize, mail, return products ($5-$100)
4. **In-Person Attendance** — Attend meetings, stand in line, property viewings, mystery shopping ($10-$60)
5. **Validator/Infra Tasks** — Check servers, press reset buttons, swap USBs, datacenter audits ($5-$60)
6. **Creative & Content** — Record voice, take photos, handwritten notes, film videos ($2-$30)
7. **Monitoring & Recurring** — Daily construction photos, P.O. box checks, route inspections ($2-$15/session)
8. **Social Engineering & Human-Only Access** — Ask questions at counters, get business cards, test service ($1-$30)
9. **"Weird But Real" Sensory** — Smell, touch, listen, read body language, describe vibes ($2-$30)

## Key Patterns (for architecture)

1. **Senses Gap** — Agents can see/hear digitally but can't touch, smell, taste, or move
2. **Identity Gap** — Many transactions require human ID, signature, or voice
3. **Patience Gap** — Agents can't wait in physical lines
4. **Trust Gap** — Some interactions only work human-to-human
5. **Last Mile** — Digital processes solved; physical last mile is the bottleneck

## Usage

- **Article:** Use realistic examples from these categories
- **Task Factory:** Create test presets matching these categories
- **Tests:** Use as realistic test scenarios for E2E and integration tests
- **Marketing:** These categories communicate the value proposition clearly
