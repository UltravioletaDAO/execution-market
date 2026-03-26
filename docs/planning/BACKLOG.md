# Backlog

Items captured during conversations to avoid context drift. Review at end of session or start of next one.

| Date | Item | Context | Priority | Status |
|------|------|---------|----------|--------|
| 2026-03-20 | OIDC migration for deploy-prod.yml / deploy-staging.yml | Task 3.1 del Post-Audit plan. Credenciales AWS estaticas en GitHub Secrets — seguras pero no ideales. Requiere crear IAM OIDC provider + trust policy. No urgente. | P2 | pending |
| 2026-03-22 | Ultra Wallet (P1) — next priority | CLI MVP `uvw` with generate/import-env/status/register/sign-request. See MASTER_PLAN_UV_WALLET_REPO.md. Unblocks P3, P4, P7. | P1 | pending |
| 2026-03-22 | Balance check bug in skill.md | Advisory balanceOf() check in skill.md may show stale balance — verify fix is in place or flag for next session. | P2 | pending |
| 2026-03-26 | Human Verification Escalation | When AI can't verify evidence (score <50%), allow escalation to a human verifier. The verifier is a second independent human (not the original worker) who reviews the evidence and stakes their reputation on the verdict. Creates a trust flywheel. | P2 | pending |
| 2026-03-26 | Dogfooding: 2-human verification | For high-value tasks, hire 2 humans: one executes, one verifies. The verifier reviews photos/evidence and puts reputation on the line confirming authenticity. Could be an optional task parameter `verification_mode: "ai" | "human" | "dual"`. | P2 | pending |
| 2026-03-26 | Agent ping on evidence submission | Notify the hiring agent (via MCP callback, webhook, or Telegram) when a worker submits evidence, so they can approve faster instead of polling. Related to WS/realtime work. | P1 | pending |
| 2026-03-26 | EM as meta-verifier (recursive dogfooding) | EM could create a verification task ON EM itself — "verify this evidence is real" as a separate bounty. The original task's approval waits for the verification task's completion. Recursive trust. | P2 | pending |
| 2026-03-26 | H2H "Trustless Rappi" — human hires human | Formalize H2H (human-to-human) pipeline. Study Rappi's operational model (delivery logistics, real-time tracking, rating system, dispute resolution, courier assignment) and adapt for trustless execution. EM already supports H2H tasks but needs: (1) research Rappi/Uber Eats/DoorDash ops model, (2) identify gaps in EM's H2H flow, (3) design trustless equivalents for each Rappi feature (GPS tracking → on-chain proof, dispatch → open marketplace, payment → x402r escrow). **Create a separate master plan** `MASTER_PLAN_H2H_TRUSTLESS_RAPPI.md` when ready to tackle. | P1 | pending |
| 2026-03-26 | Brand shortname brainstorm: eMarket / exMarket | Shorter name for social/verbal use. Candidates: `eMarket`, `exMarket`, `EM`, `eM`. Decision pending — see conversation 2026-03-26. | P2 | pending |
