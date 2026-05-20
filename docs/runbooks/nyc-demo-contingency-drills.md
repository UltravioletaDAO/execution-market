---
date: 2026-05-20
tags:
  - type/runbook
  - domain/operations
  - chain/solana
  - status/active
status: active
aliases:
  - Contingency drills
  - 30-min fault-injection practice
related-files:
  - docs/runbooks/nyc-demo-runbook.md
  - docs/runbooks/nyc-demo-filming.md
  - docs/runbooks/payshell-ops.md
  - docs/runbooks/mpp-scenarios-runbook.md
  - docs/runbooks/nyc-demo-dry-run-checklist.md
  - docs/planning/MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO.md
---

# Contingency Drills — 30-min Practice Script

> **Phase 6.7 prep deliverable.** A timed drill script that walks Saul (and
> whoever else is on the stage laptop) through each contingency in the
> `[[nyc-demo-runbook]]` contingency matrix. The point isn't to read the
> matrix — it's to *practice the muscle memory* of recovery so that on
> demo day the operator reaches for the cellular hotspot or the simulator
> reflex, not for the documentation.
>
> Run this once at the office (T-7 days) and once at the NYC stage (T-1 day).
>
> The drill execution itself is HITL — the value of this doc is the exact
> scenario, fault injection command, and recovery target time per drill,
> so that whoever runs the practice doesn't have to invent it.

## Setup (T-5 min)

- Stage laptop in normal operating mode: `/demo/nyc` loaded, OWS skill running, pay.sh proxy up
- Stopwatch / phone timer ready
- Pen + paper to record actual recovery times per drill
- Drill should fail-safe: if a recovery overruns its budget by 2x, pause and document instead of guessing
- Pre-flight passes (`docs/runbooks/nyc-demo-dry-run-checklist.md` runs clean)

## Drills

Six drills, ~5 min each. Total 30 min including reset between drills.

### Drill 1 — Wifi drops mid-demo (5 min)

| Phase | Time | Action |
|-------|------|--------|
| Setup | 0:00 | `/demo/nyc` open, paused at beat 5 (taxímetro live) |
| Fault | 0:30 | Toggle the laptop's wifi off (System Settings, not just disable) |
| Expected | 0:31 | SSE stream emits `error` within ~2s, taxímetro freezes (last known value) |
| Recovery | 0:35 | Enable cellular hotspot on phone, switch laptop to it |
| Recovery | 1:10 | Re-open `/demo/nyc?channel=<CHANNEL_ID>` — taxímetro restores from server |
| Budget | — | Total recovery ≤ **60s** |
| Reset | 4:00 | Restore wifi, close drill |

**What to watch for**: did the taxímetro restore from URL params, or did it
restart from zero? If the latter, the URL-param restoration is broken and
needs a fix before NYC — file as P0.

---

### Drill 2 — MoonPay overlay won't load (5 min)

| Phase | Time | Action |
|-------|------|--------|
| Setup | 0:00 | Stage laptop fresh, `/demo/nyc` open at beat 1 (empty wallet) |
| Fault | 0:15 | DevTools → Network → block `*.moonpay.com` |
| Expected | 0:30 | MoonPay Headless overlay either hangs or shows error |
| Recovery | 1:00 | Operator presses fallback button or operator narrates: "Pre-funded for demo" |
| Recovery | 1:15 | Skip to beat 3, manually use backup wallet pre-funded with $40 |
| Budget | — | Total recovery ≤ **90s** narration + action |
| Reset | 4:00 | Unblock MoonPay, close drill |

**What to watch for**: does the operator remember to narrate over the
fallback? Silent fallbacks look like bugs on camera. Practice the line.

---

### Drill 3 — Robot fails to accept the task (5 min)

| Phase | Time | Action |
|-------|------|--------|
| Setup | 0:00 | Task published, robot wallet has 0 USDC + 0 SOL (correct baseline) |
| Fault | 0:30 | Kill the robot's OWS process: `pkill -f em-robot-skill` |
| Expected | 0:35 | Beat 4 never advances; the dashboard shows no acceptance |
| Recovery | 0:50 | Operator runs simulator fallback in another terminal: `npx tsx scripts/dev/worker-sim.ts --task-id <ID> --duration 30` |
| Recovery | 1:30 | Simulator opens MPP channel via pay.sh, vouchers begin flowing, beat 5 advances |
| Budget | — | Total recovery ≤ **90s** |
| Reset | 4:00 | Restart robot OWS process, close drill |

**What to watch for**: does the simulator emit the same voucher cadence as
the real robot? If it ticks visibly faster or slower, the taxímetro will
look fake — adjust `--duration` to match the planned demo length.

---

### Drill 4 — pay.sh settle fails (5 min)

| Phase | Time | Action |
|-------|------|--------|
| Setup | 0:00 | Task in flight, vouchers landing |
| Fault | 0:30 | Stop the pay.sh control plane on the proxy host (Terraform-managed sidecar) |
| Expected | 0:30 | Beat 7 (`Session closed → settle`) hangs >10s |
| Detection | 1:00 | Operator hits `GET https://api.execution.market/api/v1/taximetro/<CHANNEL_ID>/history` and sees vouchers but no settlement |
| Recovery | 1:30 | Manually trigger settlement via ops console (`payshell-ops.md` §"Settlement stuck") |
| Recovery | 2:30 | Settlement lands, beat 8 reveal animation fires |
| Budget | — | Total recovery ≤ **150s** — this is the longest |
| Reset | 4:00 | Restart pay.sh, close drill |

**What to watch for**: this drill is too slow for a live demo recovery —
the budget here is "operator can still finish the take if it triggers
within the first 60s of beats 1-4." Past beat 5, abort to backup video
per `[[nyc-demo-runbook]]` §"When to abort".

---

### Drill 5 — Stage laptop dies (5 min)

| Phase | Time | Action |
|-------|------|--------|
| Setup | 0:00 | Beat 5, taxímetro live |
| Fault | 0:30 | Hard power off — hold the power button until shutdown |
| Expected | 0:31 | Black screen, off-camera panic acceptable |
| Recovery | 1:00 | Power on, login, restore browser session (auto-restore tab) |
| Recovery | 2:00 | URL params restore meter state; if a session was active, channel ID resumes from pay.sh history |
| Recovery | 2:30 | If meter doesn't restore in 30s after page load, switch to backup video |
| Budget | — | Total recovery ≤ **150s** before abort |
| Reset | 4:00 | Close drill |

**What to watch for**: does the laptop autoboot to the demo page without
prompting for full disk encryption / 2FA? If yes, fast restart works. If
no, **disable** disk encryption prompts and 2FA on this laptop for the
demo session only — it's a curated demo machine, not the daily driver.

---

### Drill 6 — Camera or sound dies mid-take (5 min)

| Phase | Time | Action |
|-------|------|--------|
| Setup | 0:00 | Stage running, camera rolling on B-roll |
| Fault | 0:30 | Camera op stops recording (or fakes a dead battery alert) |
| Expected | 0:31 | Audio operator catches it, signals Saul off-camera |
| Recovery | 1:00 | Pause the demo flow at the current beat (taxímetro will keep ticking, but cinematography pauses) |
| Recovery | 1:30 | Swap camera body, resume from current beat, no re-take of earlier beats |
| Recovery | 2:30 | Mic check + roll |
| Budget | — | Total recovery ≤ **150s** |
| Reset | 4:00 | Close drill |

**What to watch for**: does the demo flow handle a pause gracefully? The
taxímetro and pay.sh session don't care about cinematography, so they'll
keep accumulating. Plan the cinematography around "you can always cut a
chunk out in post" rather than "the live state has to match the cut."

## After all 6 drills

- Total time: ~30 min including resets
- Compare actual recovery times vs budgets; anything over budget is a P0 to fix before demo day
- Update the `[[nyc-demo-runbook]]` contingency matrix if a new failure mode surfaced
- Write a 3-line post-mortem in `docs/internal/` (gitignored) for the rehearsal

## What this drill script does **not** cover

- The contingency matrix itself — see `[[nyc-demo-runbook]]` §"Contingency matrix"
- Cinematography fault recovery (lighting, framing) — see `[[nyc-demo-filming]]`
- Decision to abort the live take — see `[[nyc-demo-runbook]]` §"When to abort"
- Backup video production — Phase 6.5, see `[[nyc-demo-filming]]` §"Backup video"

## Linked sub-tasks

- Phase 6.7 — Contingency drills (30-min practice) — this doc is the script for the practice itself
- Phase 6.5 — Backup video pre-grabado — produced separately, referenced as Drill 4/5 abort target
