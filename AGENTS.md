# AGENTS.md instructions for Z:\ultravioleta\dao\chamba

<INSTRUCTIONS>
## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.
### Available skills
- new-job: Create test scenarios to simulate AI agents publishing tasks on Execution Market and test the full task lifecycle flows -- publish, accept, submit evidence, approve/reject, payment release, refund, and dispute. Use when the user says "new job", "create a test task", "test the flow", "simulate an agent", "test scenario", or wants to verify that the MCP tools, REST API, and payment flows work correctly. Also use for "test escrow", "test submission", or "test payment". (file: Z:/ultravioleta/dao/chamba/.agents/skills/new-job/SKILL.md)
- project-rename: Rename a project across all layers -- code, infrastructure, Docker, CI/CD, DNS, docs, SDKs, and environment variables. Use when the user wants to rebrand, rename, or change the prefix/name of a project throughout the entire codebase and deployed infrastructure. Triggers on requests like "rename the project", "rebrand from X to Y", "change all references from old-name to new-name", or "migrate infrastructure names". (file: Z:/ultravioleta/dao/chamba/.agents/skills/project-rename/SKILL.md)
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations. (file: Z:/ultravioleta/dao/chamba/.agents/skills/skill-creator/SKILL.md)
- vercel-react-best-practices: React and Next.js performance optimization guidelines from Vercel Engineering. This skill should be used when writing, reviewing, or refactoring React/Next.js code to ensure optimal performance patterns. Triggers on tasks involving React components, Next.js pages, data fetching, bundle optimization, or performance improvements. (file: Z:/ultravioleta/dao/chamba/.agents/skills/vercel-react-best-practices/SKILL.md)
- web-design-guidelines: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices". (file: Z:/ultravioleta/dao/chamba/.agents/skills/web-design-guidelines/SKILL.md)
- find-skills: Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express interest in extending capabilities. This skill should be used when the user is looking for functionality that might exist as an installable skill. (file: C:/Users/lxhxr/.agents/skills/find-skills/SKILL.md)
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: C:/Users/lxhxr/.codex/skills/.system/skill-creator/SKILL.md)
- skill-installer: Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: C:/Users/lxhxr/.codex/skills/.system/skill-installer/SKILL.md)
### How to use skills
- Discovery: The list above is the skills available in this session (name + description + file path). Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) When `SKILL.md` references relative paths (e.g., `scripts/foo.py`), resolve them relative to the skill directory listed above first, and only consider other paths if needed.
  3) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
  4) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  5) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless you're blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.

## Project Context Loading (Mandatory Before Real Tests)

When asked to run "real validation", "end-to-end", "live", "x402", "escrow", or "production checks", load context in this order before executing scripts:

1) `CLAUDE.md` (aka "CloudMD" if user refers to it that way)
2) `.agents/skills/new-job/SKILL.md`
3) `.agents/skills/new-job/references/test-flows.md`
4) `docs/planning/PRODUCTION_LAUNCH_MASTER_2026-02-05.md`
5) `docs/planning/IMPROVEMENT_BACKLOG_2026-02-05.md`
6) `docs/planning/SHIP_EXECUTION_REPORT_2026-02-05_TX402.md`
7) `docs/planning/SHIP_NOW_AUDIT_2026-02-05.md`

Do not bulk-read unrelated docs. Only pull extra files if blocked.

## Real Validation Protocol (Execution Market)

Before running live scripts:
- Confirm `.env.local` has: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `WALLET_PRIVATE_KEY`.
- Check Base Mainnet balances with `cd scripts && npm exec -- tsx check-deposit-state.ts`.
- If USDC is insufficient for live escrow, switch to smallest viable bounty or run simulated flow and mark as non-live.
- If a live deposit step reverts after task insert, immediately mark that task as `cancelled` using service-role credentials to avoid published tasks without escrow.

Preferred script order for end-to-end evidence:
1) `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api`
2) `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api --monitor`
3) `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api --monitor --auto-approve`

Fallbacks:
- If live fails due to funds/network, run:
  - `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api false`
  - `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --direct --count 1` (non-facilitator debug)

## Validation Evidence Requirements

For each run, capture and report:
- Script name + exact command
- Mode (`live` or `simulated`)
- Wallet address used
- Task IDs created
- `escrow_id` and `escrow_tx` (or explicit reason if absent)
- Transaction links (BaseScan) when available
- Final task statuses in Supabase/API
- Errors, retries, and unresolved blockers

Never claim a production-ready payment flow without at least one run that includes on-chain tx hash evidence or a clearly documented blocker.

## Direct Wallet Guardrail

Direct wallet-to-contract scripts are debug-only and must not be used as production payment evidence unless explicitly marked.
If direct mode is truly needed for diagnostics, require `--allow-direct-wallet` in the command and report it as `non-facilitator`.
</INSTRUCTIONS>
