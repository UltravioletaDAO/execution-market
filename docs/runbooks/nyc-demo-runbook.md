---
date: 2026-05-20
tags:
  - type/runbook
  - domain/operations
  - chain/solana
  - status/active
status: active
aliases:
  - NYC demo runbook
  - MoonPay NYC demo day
related-files:
  - docs/planning/MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO.md
  - docs/runbooks/payshell-ops.md
  - docs/runbooks/mpp-scenarios-runbook.md
  - docs/runbooks/surfpool-payshell-dev-env.md
  - dashboard/src/pages/NycDemoPage.tsx
  - dashboard/src/pages/TaskExecutionScene.tsx
  - scripts/demo/prefund-demo-wallets.ts
---

# NYC Demo Runbook — MoonPay Office, 2026-06-02 → 2026-06-16

> **Phase 6.2 deliverable.** Step-by-step playbook for the cinematic demo at the
> MoonPay NYC office. This document is **the** source of truth on demo day. If
> Claude is unavailable, anyone on the team should be able to execute this
> from top to bottom without further context.
>
> Pairs with [[nyc-demo-filming]] (cinematography) and [[payshell-ops]] (backend
> operations). Decisions and architecture live in [[MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO]].

## Demo window

- **Earliest dry-run on-site**: 2026-06-02 (Saul starts at MoonPay 2026-06-01)
- **Latest filming day**: 2026-06-16
- **Hard backup**: pre-recorded 4K MP4 produced during dry-run #2 (step 22)

## Cast and roles

| Role | Person | Wallet | Function |
|------|--------|--------|----------|
| Publisher | Saul (on-camera) | `SAUL_SOLANA_PUBKEY` (OWS hot) | Publishes the `physical_presence` task |
| Worker | Robot dog OR humanoid (D-20 open) | `ROBOT_SOLANA_PUBKEY` (OWS skill) | Accepts task, signs vouchers, scans barcode |
| Operator | Felipe / FDE (off-camera) | n/a | Drives ops laptop, reads channel ID, runs fallbacks |
| Camera | NYC freelancer or in-house (TBD per [[nyc-demo-filming]]) | n/a | 4K capture + B-roll |
| Sound | Same as camera | n/a | Lavalier mic on Saul |
| MoonPay liaison | Halsey or designate | n/a | Office access, filming permit |

## The cinematic flow (one sentence per beat)

```
1. wallet empty           ──▶  Saul opens /demo/nyc on the stage laptop
2. MoonPay headless       ──▶  $20 USDC lands on Saul's Solana wallet in <90s
3. task published         ──▶  bounty $5–$20, paymentNetwork=solana
4. robot accepts          ──▶  OWS skill opens MPP channel via pay.sh
5. barcode scan           ──▶  robot verifies task ID match
6. vouchers tick          ──▶  taxímetro live on the 4K monitor
7. delivery complete      ──▶  channel closes, settleAndFinalize fires
8. dramatic reveal        ──▶  87/13 split animation, txHash visible
```

Every beat has a fallback. Every fallback is **<60s** to execute. See "Contingency
matrix" below.

---

## Pre-departure checklist (T-72h)

1. **Local dry-run #1 ($20 mainnet)** — execute Phase 4.11 in Saul's home office
   against production pay.sh + MoonPay Headless. Record the result as MP4.
   See task #47 in the master plan.

2. **Pre-fund all demo wallets** — run
   `npx tsx scripts/demo/prefund-demo-wallets.ts --network solana-mainnet --dry-run`
   first, then re-run without `--dry-run` once balances look right.
   Expected end-state:
   - Saul wallet: **$0 USDC** (the on-ramp is part of the demo), `0.05 SOL` (gas dust for emergencies)
   - Robot wallet: **$0 USDC**, **$0 SOL** (fee-sponsorship is the cinematic point)
   - Backup buyer wallet: `$40 USDC` reserve for second take, separate Ledger seed
   - Treasury: existing balance is fine, no top-up needed

3. **Pin all dependencies** — verify in repo HEAD:
   - `@solana/mpp@0.5.2` (D-11 pin)
   - `pay-sh` Docker image tag matches the one ECS is running today
   - `mpp-sdk` commit SHA matches the vendored copy
   Run `git status` — the working tree **must** be clean before flying.

4. **Verify Supabase migration 108 is applied in production** — see
   [[payshell-ops]] §"Turn it on (first time)" step 1. SQL:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_name IN ('task_channel_bindings', 'mpp_session_events');
   -- Expect 2 rows.
   ```

5. **Flip `EM_PAYSHELL_ENABLED=true` in ECS** — force-new-deployment
   `mcp-server` service. Wait for `/health` to return 200 on **both** mainnet
   and the taxímetro route:
   ```
   curl https://api.execution.market/health
   curl https://api.execution.market/api/v1/taximetro/health
   ```
   Both must return `{"status":"ok"}`.

6. **MoonPay Production API keys live in AWS Secrets Manager** — verify
   without exposing the values:
   ```bash
   aws secretsmanager describe-secret --secret-id em/moonpay-prod --region us-east-2
   ```
   The `LastChangedDate` should be recent (post-Saul onboarding). If it shows
   the spike sandbox key, escalate to the MoonPay internal team.

7. **Run Golden Flow against staging** — `python scripts/e2e_golden_flow.py`.
   All steps must pass. If any chain fails, the demo is **NOT** ready.

8. **Pre-record the backup video** — see [[nyc-demo-filming]] §"Backup video".
   Upload the raw MP4 + a 1080p compressed copy to S3 + a local USB stick
   that travels in Saul's carry-on.

## Travel-day checklist (T-24h)

9. **Hardware** — pack the stage laptop, charger, USB-C hub, **two** 4K HDMI
   cables (one fails, the other saves the day), backup wifi hotspot (T-Mobile
   or cellular). See [[nyc-demo-filming]] for camera gear.

10. **Wallet seeds** — Saul's OWS hot wallet seed lives on hardware Ledger,
    **never** on the stage laptop. Robot OWS skill seed lives in AWS Secrets
    Manager (`em/robot-ows-solana`) and the robot loads it at boot. **Verify
    you can rotate the robot key** without redeploying the OWS MCP server.

11. **Env file for the stage laptop** — `.env.demo-nyc` (gitignored). Required
    keys (read these from password manager, never paste in chat):
    ```bash
    VITE_API_URL=https://api.execution.market
    VITE_MOONPAY_ENABLED=true
    VITE_MOONPAY_API_KEY=<read from 1Password>
    VITE_SUPABASE_URL=<read from 1Password>
    VITE_SUPABASE_ANON_KEY=<read from 1Password>
    EM_PAYSHELL_ENABLED=true
    EM_SOLANA_RPC_URL=<QuikNode Solana mainnet URL from 1Password>
    ```
    **Never** put `WALLET_PRIVATE_KEY` on the stage laptop. The stage laptop
    is a viewer only — OWS holds keys on the Ledger and the robot.

12. **Smoke test on the stage laptop** — `cd dashboard && npm run dev`. Open
    `http://localhost:5173/demo/nyc` and verify:
    - Beat 1 renders (the "Connect wallet" form)
    - Pasting `SAUL_SOLANA_PUBKEY` advances to Beat 2 (balance check)
    - Balance reads correctly (should be `0.00` USDC at this stage)
    - The "Open MoonPay" button does **not** open the live overlay yet
      (clicking it requires VITE_MOONPAY_ENABLED=true + key, which the dev
      build doesn't have)

## Demo-day setup (T-2h, on-site at MoonPay NYC)

13. **Office check-in** — confirm with Halsey (or designate) where filming
    happens. If the spot is glass-walled or has windows behind it, request a
    different angle to avoid glare on the 4K monitor.

14. **Power + network** — plug the stage laptop into wall power (battery
    will die mid-demo otherwise). Connect to **wired ethernet** if available;
    fallback is the cellular hotspot (step 9). MoonPay guest wifi is **not**
    trusted — corporate networks often block long-lived SSE connections.

15. **External monitor** — connect the 4K display via HDMI #1. Mirror or
    extend? **Extend.** The stage laptop screen is for the operator (Felipe),
    the 4K monitor is what the camera films. Set the laptop screen brightness
    to 100% and the monitor to **calibrated B&W** (per [[brand-canonical]] —
    no warm filters, no auto-dimming).

16. **Browser setup** — open Chrome in incognito mode. Go to
    `https://execution.market/demo/nyc` with **only** these flags in the URL:
    `?wallet=<SAUL_SOLANA_PUBKEY>&cap=5&rate=0.05&network=mainnet-beta`
    The page should land on Beat 2 (balance check) with `0.00` USDC.

17. **Open the ops terminal** — second tab in Chrome:
    `https://api.execution.market/docs` (Swagger). Open the
    `/api/v1/taximetro/{channel_id}/stream` endpoint stub so you can paste
    the channel ID into it when the robot opens the session (step 21).

18. **Camera and audio test** — see [[nyc-demo-filming]] §"On-site test".
    Confirm the 4K monitor is **the** primary frame, not the laptop screen.

## Demo execution (live, 5–8 minutes)

19. **Beat 1 → Beat 2 (camera rolls)** — Saul taps "Connect wallet" on the
    laptop, which auto-advances because the wallet is in the URL params. The
    4K monitor shows: `Wallet 0xABCD…  Balance: $0.00 USDC  Solana`.

20. **Beat 2: MoonPay on-ramp (the cinematic moment #1)** — Saul taps "Open
    MoonPay". The headless overlay appears on the 4K monitor. He uses Apple
    Pay on his phone (rehearsed flow). Within ~60–90s, the overlay closes
    and the dashboard re-reads the balance: `~$20 USDC` appears. If this
    takes >2 minutes, **abort to fallback A** (below).

21. **Beat 3: publish the task** — the dashboard auto-advances to Beat 3.
    Saul taps "Publish task" with the prefilled form:
    - Title: `Carry small package from lobby to executive area`
    - Bounty: `$5.00 USDC` (waiver internal, per D-13/D-17)
    - Deadline: `15 minutes`
    - Payment network: `Solana` (preset)
    The button calls `createTask`. On success, the operator (Felipe) reads
    the **channel ID** from the response in the laptop's network tab and
    pastes it into the binding beat input on the 4K monitor.

22. **Beat 4: robot accepts (cinematic moment #2)** — Felipe runs the OWS
    skill on the operator laptop:
    ```bash
    npx tsx ows-mcp-server/scripts/robot-accept.ts \
      --task-id <TASK_ID> --skill em-robot-skill
    ```
    The robot (dog or humanoid, per D-20) walks into frame with the package.
    Its on-board display (or the operator's tablet, framed in the shot) shows
    `Task accepted. Scanning barcode...`

23. **Beat 5: barcode scan** — Saul holds up the 4K monitor, which is now
    showing the QR rendered by `TaskExecutionScene.tsx` (480px square). The
    robot's camera scans it. The OWS skill verifies the encoded task ID
    matches what it accepted. The header on the 4K monitor flips from
    `Awaiting scan` to `Executing`.

24. **Beat 6: voucher ticks (cinematic moment #3, ~30s on camera)** — the
    robot starts walking with the package. Every ~1s the OWS skill signs a
    voucher and submits it to pay.sh. The taxímetro on the 4K monitor ticks
    up smoothly thanks to the rAF extrapolation in
    `TaximetroLive.tsx`. Camera should zoom in on the digits here — this is
    the central "magic" of the demo.

25. **Beat 7: delivery + channel close** — Saul receives the package. The
    robot closes the channel:
    ```bash
    npx tsx ows-mcp-server/scripts/robot-close.ts \
      --channel-id <CHANNEL_ID> --task-id <TASK_ID>
    ```
    The dashboard header flips to `Session closed`. The pay.sh server
    submits `settleAndFinalize` + `distribute` atomically on-chain.

26. **Beat 8: settlement reveal (cinematic moment #4)** — within 2–4s of
    the close, the `settlement_complete` SSE event lands. `SettlementAnimation.tsx`
    runs its three beats (total countup, 87/13 split, txHash). The camera
    holds on the final frame: txHash with an underlined link to
    `explorer.solana.com`. Saul reads the worker share aloud:
    *"$0.087 to the robot, $0.013 to treasury, the rest refunds to me."*

27. **End on-camera, keep recording B-roll** — operator stops recording the
    main shot but keeps a wide angle running for any post-demo reactions.

## Post-demo (T+30m)

28. **Verify on-chain** — pull up Solana Explorer with the txHash, screenshot
    the split, and save it to `vault/05-demo/nyc-2026-06/` for post.

29. **Post-mortem** — five-minute standup: what worked, what almost broke,
    what we'd cut. Write findings to
    `vault/05-demo/nyc-2026-06/post-mortem.md` before bed.

30. **Backups offload** — the camera SD card and the laptop's screen
    recording both upload to S3 (`s3://uv-demo-nyc-raw/2026-06-XX/`) and a
    local USB drive. **Two backups before the camera leaves the office.**

---

## Contingency matrix

| Failure mode | Detection | Fallback (<60s) |
|--------------|-----------|-----------------|
| **Wifi drops mid-demo** | SSE stream emits `error`, taxímetro freezes | Switch to cellular hotspot (already provisioned). Re-open `/demo/nyc?channel=<CHANNEL_ID>` — URL params restore state. |
| **MoonPay overlay won't load** | Beat 2 hangs >2min | **Fallback A**: skip the on-ramp on camera, claim "pre-funded for demo" and proceed to Beat 3. Saul has $40 reserve in the backup wallet. |
| **Robot fails to accept** | Beat 4 never advances | **Fallback B**: switch to robot-simulator (scenario D from [[mpp-scenarios-runbook]]). `npx tsx scripts/dev/worker-sim.ts --task-id <ID> --duration 30`. Same wire protocol, no hardware. |
| **pay.sh settle fails** | Beat 7 sits in `Session closed` >10s | Check `https://api.execution.market/api/v1/taximetro/<CHANNEL_ID>/history` — if vouchers landed but settlement didn't, manually trigger via the ops console. Worst case: the funds are recoverable, see [[payshell-ops]] §"Settlement stuck". |
| **Stage laptop dies** | Black screen | Reboot, restore from URL params (everything is in the URL). Worst case: switch to the pre-recorded backup video (step 8). |
| **Camera dies** | No footage | Restart with the backup body. Roll the pre-recorded video as B-roll if the second take fails. |
| **Robot dog runs into a wall** | Visual | Cut. Restart from Beat 4. The on-chain settlement is decoupled from the choreography — the previous run's channel can be closed silently from the ops terminal. |

## When to abort

Abort the live take and use the backup video if **two** of the following are
true simultaneously:

- Wifi has been unreliable for >5 minutes
- MoonPay Headless has failed once already
- The robot has needed a reset more than twice

Do **not** abort because of single-point failures — every beat has a <60s
recovery. Aborting is for cascading failures only.

## After the demo (T+24h)

- Re-fund the demo wallets back to baseline using
  `npx tsx scripts/demo/prefund-demo-wallets.ts --network solana-mainnet --reset`
- File an internal MoonPay BD post-demo write-up via the channel Halsey
  designates (D-17 internal flow)
- Publish the cut video to the standard distribution channels per the
  comms plan (not in this runbook — see `vault/18-content/`)

## What this runbook does **not** cover

- Cinematography setup → [[nyc-demo-filming]]
- pay.sh production ops → [[payshell-ops]]
- Local dev environment → [[surfpool-payshell-dev-env]]
- Multi-scenario validation logic → [[mpp-scenarios-runbook]]
- Master plan, decisions, open questions → [[MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO]]
