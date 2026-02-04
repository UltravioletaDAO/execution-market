# TODO: Agent Verification Process

**Status**: Not started
**Priority**: High
**Created**: 2026-02-03
**Current state**: All submissions are auto-approved via DB trigger (`010_auto_approve_submissions.sql`)

## Context

Currently, every submission is auto-approved the moment a worker submits evidence. This is a temporary measure to unblock the MVP flow and demonstrate end-to-end task completion with payment. It must be replaced with proper agent-driven verification.

## Future Verification Flow

### 1. Agent Reviews Evidence via MCP Tool

When a submission arrives, the publishing agent should be notified (webhook or polling via `em_check_submission`) and review the evidence:

```
Worker submits evidence
  -> Submission created (status: pending)
  -> Webhook fires: submission.created
  -> Agent calls em_check_submission
  -> Agent reviews evidence
  -> Agent calls em_approve_submission (accepted / disputed / more_info_requested)
```

### 2. AI Vision Model for Auto-Checking Photos

For `photo` and `photo_geo` evidence types, run an AI vision model to verify:
- Photo matches task description (e.g., "photo of storefront" actually shows a storefront)
- GPS metadata matches `location_hint` within `location_radius_km`
- Photo is recent (EXIF timestamp within task acceptance window)
- No obvious manipulation (reverse image search, metadata consistency)

### 3. Reputation-Based Auto-Approval Thresholds

Workers with high reputation can be auto-approved for low-value tasks:

| Worker Reputation | Max Auto-Approve Bounty |
|-------------------|------------------------|
| < 50              | $0 (always manual)     |
| 50-100            | $5.00                  |
| 100-250           | $25.00                 |
| 250+              | $100.00                |

### 4. Dispute Resolution Flow

When an agent disputes a submission:
1. Funds remain in escrow
2. Arbitration panel reviews evidence (3 arbitrators)
3. Majority vote determines outcome
4. Winner receives funds, loser gets reputation penalty

### 5. Implementation Steps

- [ ] Remove `auto_approve_submission` trigger from Supabase
- [ ] Add submission webhook notifications to agents
- [ ] Implement AI vision verification service
- [ ] Add reputation-based auto-approval logic in MCP server
- [ ] Build arbitration panel UI in admin dashboard
- [ ] Add dispute resolution smart contract integration
- [ ] Write E2E tests for full verification flow

## Migration Plan

When implementing, create a new migration that:
1. Drops the `submissions_auto_approve` trigger
2. Adds a `verification_mode` column to tasks (values: `auto`, `agent`, `hybrid`)
3. Keeps the `auto_approve_submission` function as a fallback for `verification_mode = 'auto'`
