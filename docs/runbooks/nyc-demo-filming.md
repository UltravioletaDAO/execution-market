---
date: 2026-05-20
tags:
  - type/runbook
  - domain/operations
  - status/active
status: active
aliases:
  - NYC demo cinematography
  - NYC filming checklist
related-files:
  - docs/runbooks/nyc-demo-runbook.md
  - docs/planning/MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO.md
---

# NYC Demo — Cinematography Setup Checklist

> **Phase 6.3 deliverable.** Equipment, framing, and on-site procedure for the
> 4K capture at MoonPay NYC. This file pairs with [[nyc-demo-runbook]] (the
> playbook) — that one tells Saul what to do on camera, this one tells the
> camera operator what to do behind it.

## Goal of the capture

One **5–8 minute** master take in 4K (UHD, 3840×2160, 24fps) that can be cut
into:

- A **30-second hero clip** for X/LinkedIn (taxímetro tick + settlement reveal)
- A **2-minute case study** for the MoonPay BD team
- A **8-minute long-form** for YouTube / the docs site

Strict brand canonical: **black and white only**, no LUT trickery (per
memory `brand-canonical` and the existing TaskExecutionScene B&W styling).

## Equipment shopping list

### Camera

| Item | Why | Owned / Rent / Buy |
|------|-----|--------------------|
| Primary body — Sony A7S III or Canon R5C | 4K60 internal, low-light tolerance for office windows | Rent in NYC |
| Backup body — same model OR a Sony FX3 | If primary dies, we don't restart the trip | Rent in NYC |
| 24-70mm f/2.8 zoom | Covers wide office shot + tight digit close-up | Rent with body |
| 50mm prime f/1.4 | Beat 6 close-up on taxímetro digits — shallow DoF sells the "magic" | Rent with body |
| Two 256GB CFexpress / SDXC V90 cards | One per body, plus a spare | Owned (Saul) + rent backup |

### Support

| Item | Why |
|------|-----|
| Manfrotto carbon tripod + fluid head | The Beat 6 close-up needs to be **rock solid** — no handheld jitter on the digits |
| Handheld gimbal (DJI RS3 or RS4) | The robot-walking shot in Beat 6 |
| Slider rail (24" min) | Optional. Adds production value to the settlement reveal in Beat 8 |
| Two C-stands | Light placement + reflectors |

### Lighting

| Item | Why |
|------|-----|
| Aputure 300X (or equivalent) — bi-color LED | Key light for Saul + the 4K monitor |
| Aputure MC mini × 2 | Edge / fill on the monitor (avoid screen glare) |
| 5×7 silk + black flag | Soften key, control spill |
| Reflector (silver / white) | Bounce for Saul's face when shooting toward the monitor |

**Critical**: office windows will produce **mixed daylight**. Either shoot
during a known cloudy window, or block the windows with the available
curtains/blinds. The 4K monitor must not have any natural light reflecting on it.

### Audio

| Item | Why |
|------|-----|
| Lavalier mic — Rode Wireless GO II × 2 | One on Saul, one on the robot's frame (if it's a humanoid) or near the robot dog body |
| Shotgun mic (boom) | Ambient room tone + redundancy on Saul |
| Field recorder — Zoom F3 | Records two-track redundantly |
| Slate / clapboard | Sync, but also gives the editor a clean cut marker |

### Other

| Item | Why |
|------|-----|
| External 4K reference monitor (Atomos Ninja or SmallHD 702) | Lets the camera op confirm the digits are sharp on the 4K monitor |
| Wireless follow-focus | Optional — manual focus on the close-up is fine if the operator is solid |
| Drone (DJI Mavic 3 Pro) | **Only if MoonPay permits.** Establishing shot of the building exterior + lobby. Confirm filming permit covers airborne. |
| Two USB-C hubs + HDMI cables × 4 | Wires fail. Bring spares of everything. |
| Gaffer tape, black + matte | Cable management on camera; also covers any inadvertent logos in frame |

## Shot list

| # | Shot | Lens | Duration | Notes |
|---|------|------|----------|-------|
| 1 | Wide of MoonPay office exterior or lobby | 24mm | 5s | Establishing. Drone if permitted. |
| 2 | Medium of Saul at the laptop, empty wallet on the 4K monitor | 35mm | 8s | Frame the monitor over Saul's shoulder. |
| 3 | Tight on the MoonPay overlay → balance update | 50mm | 12s | Beat 2. Catch the moment the balance flips from `0.00` to `~$20`. |
| 4 | Saul publishes task — fingers on the keyboard | 50mm macro | 5s | Hands only. Voice-over later. |
| 5 | Wide — robot enters frame from the lobby | 24mm | 10s | Beat 4. Establishing the robot's physical presence. |
| 6 | Tight on the QR code as the robot scans | 35mm | 4s | Beat 5. Strict B&W contrast — the 480px QR fills the frame. |
| 7 | **HERO shot**: 50mm tight on the taxímetro digits as they tick | 50mm | 30s | Beat 6. Tripod. No camera move. Cut here in the hero clip. |
| 8 | Wide of the robot walking with the package | 24mm gimbal | 15s | Beat 6/7. Gimbal smooth. |
| 9 | Tight on Saul receiving the package + close gesture | 50mm | 8s | Beat 7. |
| 10 | Settlement animation — full screen of the 4K monitor | 35mm | 6s | Beat 8. The three-beat animation runs ~3s — give it headroom. |
| 11 | Wide reaction shot — Saul + room | 24mm | 5s | Beat 8 end. |
| 12 | B-roll: hands, MoonPay logo (if visible), robot details | varies | varies | For the editor. |

## Framing rules

- **The 4K monitor must always be in focus when it's on camera.** The whole
  point of the cinematic UI is to film it. If the monitor is soft, the take
  is unusable.
- **No on-screen overlays from the operating system.** The dashboard runs in
  Chrome **fullscreen** (F11). No bookmark bar, no taskbar, no notifications.
  Quit Slack, Notion, mail, everything.
- **No keyboard / trackpad in the hero shots.** The hero clip should feel
  like the digits update themselves. Saul's hands belong in shot #4 only.
- **Strict B&W on the monitor.** No accent colors will appear (the dashboard
  enforces this via `border-black bg-white text-black` in
  `dashboard/src/pages/TaskExecutionScene.tsx`). If you see any blue, green,
  or emerald artifact on screen, **stop the take** — there's a regression.

## On-site test (T-30 min before camera rolls)

1. Power on the camera, attach to the tripod, frame shot #7 (the hero close-up).
2. The operator (Felipe) opens `https://execution.market/demo/nyc?wallet=<TEST_WALLET>&cap=0.5&rate=0.001&network=mainnet-beta`
   in Chrome on the stage laptop, extends to the 4K monitor, presses F11.
3. From the laptop, the operator manually drives the demo flow to Beat 6
   (taxímetro ticking) using a `worker-sim.ts` channel — see
   [[mpp-scenarios-runbook]] §"Cell D".
4. Camera op confirms:
   - Digits are sharp at 100% pixel peep on the external 4K reference monitor
   - No moiré on the QR
   - No reflections on the monitor
   - White is white (not yellow / blue cast) — match to a known-neutral
     reference card if uncertain
5. Audio test — Saul says his rehearsed line (*"$0.087 to the robot..."*) at
   normal volume. Lav peaks at ~-12dB, no clipping.

## Backup video (pre-recorded — see [[nyc-demo-runbook]] step 8)

Before flying to NYC, record the **same** flow in Saul's home office in 4K.
Same lens, same lighting if possible. Upload:

- Raw MP4 → `s3://uv-demo-nyc-raw/backup/2026-06-XX-pre-recorded.mp4`
- Compressed 1080p mirror → same bucket, `pre-recorded-1080p.mp4`
- USB stick stays in Saul's carry-on

If the live take fails, the editor can splice the backup as B-roll — the
viewer doesn't need to know which footage came from which location.

## Post-production handoff

Editor receives:

1. All raw camera files (CFexpress / SDXC, both bodies)
2. Both audio tracks (Rode lav + Zoom F3 backup)
3. The screen recording from the stage laptop (OBS, full 4K, in case the
   camera shot of the monitor is soft on one beat)
4. A shot log (this file, filled in with timestamps)
5. The brand-canonical reference: **strict B&W, no LUTs**, type per
   `font-mono` in the dashboard. The editor must **not** color-grade beyond
   neutral exposure correction.

## Filming permit + legal

- **MoonPay office filming**: confirmed per [[nyc-demo-runbook]] step 13 (Halsey
  is the contact). NDA may apply — if so, **no exterior signage** in the cut
  without legal sign-off.
- **Drone**: NYC airspace requires FAA Part 107 for commercial. If the camera
  freelancer doesn't have it, **drop the drone shot** — don't try to wing it.
- **Releases**: anyone visible on-camera signs a one-page release before
  rolling. Templates in `vault/05-demo/releases/`.

## What this file does **not** cover

- The demo playbook itself → [[nyc-demo-runbook]]
- Backend operations during filming → [[payshell-ops]]
- Editorial / distribution plan → `vault/18-content/`
