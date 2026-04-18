---
date: 2026-04-17
tags:
  - type/runbook
  - domain/operations
  - domain/infrastructure
  - status/active
aliases:
  - Backup Runbook
  - DR Runbook
related-files:
  - scripts/verify_backup.py
  - supabase/migrations/
  - .env.example
---

# Backup & Disaster Recovery Runbook

> **Scope**: Supabase Postgres (the authoritative data store for Execution
> Market). Covers backup strategy, verification, restore procedures, and
> the quarterly DR drill. S3 evidence data is handled separately —
> versioning + CRR live under `infrastructure/terraform/s3.tf`.

**Owner**: Platform SRE (rotation)
**Paging**: `#em-sre` Slack channel. On-call defined in PagerDuty schedule.
**RTO target**: 60 minutes (from incident declared → reads restored).
**RPO target**: 1 minute (PITR tier, worst-case data loss window).

---

## 1. Backup strategy

| Layer | Mechanism | Retention | Frequency |
|-------|-----------|-----------|-----------|
| Supabase Postgres | Managed daily logical backup | 7 days (Pro) | Nightly |
| Supabase Postgres | **Point-in-Time Recovery (PITR)** | 7 days (Pro) | Continuous WAL |
| S3 evidence bucket | Versioning + lifecycle | 90 days | Per upload |
| S3 evidence bucket | Cross-region replication (CRR) | Same as source | Continuous |
| ECR images | Lifecycle policy (keep last 10) | Latest 10 | Per deploy |

**Tier confirmation**: Supabase project must be on **Pro or higher** for
PITR to be active. Verify at: Dashboard → Project Settings → Infrastructure
→ Backups. The dashboard should show "Point-in-time recovery: Enabled" and
the retention window (default 7 days).

**Upgrade path** if PITR is not enabled: this is P0 — file an incident
and upgrade the Supabase tier before proceeding with any release that
touches `tasks`, `submissions`, `escrows`, or `payment_events`.

---

## 2. Daily verification (automated)

A lightweight canary runs `scripts/verify_backup.py` which confirms the
data layer is healthy — backups can only be as good as the live DB they
mirror, so a broken DB means the nightly snapshot will be broken too.

```bash
# Run locally (reads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from env)
python scripts/verify_backup.py

# Expected: exit code 0 + JSON summary to stdout
# Failure: exit code 1 + stderr diagnostics, triggers PagerDuty via CI
```

**Checks performed**:
1. Connection to Supabase over the `postgrest` endpoint.
2. Presence of critical tables (`tasks`, `executors`, `submissions`,
   `escrows`, `payment_events`, `applications`).
3. Row counts > 0 for tables expected to have data.
4. Most-recent `created_at` per table — freshness proxy.

**Schedule**: CI nightly job at 02:00 UTC (after Supabase's own snapshot
window, 00:00–01:00 UTC).

---

## 3. Restore procedures

### 3.1 Full database restore (catastrophic loss)

1. **Declare incident** in `#em-sre` with `!incident start db_restore`.
2. **Put API in maintenance mode**: deploy ECS task def with
   `EM_MAINTENANCE_MODE=true` (returns 503 on all writes; reads pass
   through a read-replica if present, else also 503).
3. **Supabase Dashboard → Project → Backups**:
   - Click **Restore** next to the target snapshot (most recent unless
     incident window predates it).
   - For PITR: specify the exact timestamp (UTC) *just before* the
     data-loss event.
4. Wait for restore (~5–30 min depending on DB size; monitor dashboard).
5. **Verify**: run `scripts/verify_backup.py` against the restored DB.
   All checks must pass.
6. **Reconnect app**: deploy new ECS task with fresh `SUPABASE_URL` /
   `SUPABASE_SERVICE_ROLE_KEY` if they changed (they usually do not).
7. **Exit maintenance mode** by redeploying without the flag.
8. **Post-mortem**: within 48 hours, author `docs/reports/INC-YYYY-MM-DD-db-restore.md`.

### 3.2 Partial restore (accidental table drop / bad migration)

When only a subset of data is affected, do **not** full-restore — it
would overwrite legitimate writes made after the incident.

1. Spin up a **staging restore** from PITR to a side project:
   - Supabase Dashboard → Create new project `em-restore-YYYY-MM-DD`.
   - Restore PITR snapshot into the new project at the pre-incident time.
2. `pg_dump` just the affected table(s):
   ```bash
   pg_dump \
     "postgres://postgres:${RESTORE_PASSWORD}@${RESTORE_HOST}:5432/postgres" \
     --table=public.<affected_table> \
     --data-only \
     --on-conflict-do-nothing \
     --file=/tmp/<affected_table>.sql
   ```
3. Review the dump manually. Then apply to prod:
   ```bash
   psql "postgres://postgres:${PROD_PASSWORD}@${PROD_HOST}:5432/postgres" \
     --single-transaction \
     -f /tmp/<affected_table>.sql
   ```
4. Delete the staging project once reconciled.

### 3.3 Evidence bucket recovery

Evidence in S3 is versioned + replicated cross-region. For accidental
deletions:

```bash
aws s3api list-object-versions \
  --bucket em-evidence-prod \
  --prefix <deleted-key-prefix>

aws s3api delete-object \
  --bucket em-evidence-prod \
  --key <key> \
  --version-id <delete-marker-version>  # undo the delete marker
```

If the entire primary bucket is lost, promote the CRR replica in the
secondary region and update the CloudFront origin in Terraform.

---

## 4. Quarterly DR drill

**Cadence**: every 90 days (Q1/Q2/Q3/Q4). Block a 2-hour window.

**Objective**: Prove that we can go from "DB deleted" → "reads working
on restored DB" within the 60-minute RTO.

### Drill script

1. **Prep** (–30 min):
   - Create an isolated Supabase project (`em-dr-drill-YYYY-QN`).
   - Seed it with a synthetic copy of prod schema + a few rows.
   - Put drill project under PITR.
2. **T=0** — drop a critical table via SQL editor:
   ```sql
   DROP TABLE tasks;
   ```
3. Start timer.
4. Execute §3.1 against the drill project (skipping step 2 because this
   is the drill project, not prod).
5. Stop timer when `scripts/verify_backup.py --project <drill>` returns
   exit 0.

**Record the results** in `docs/reports/DR-DRILL-YYYY-QN.md`:

| Metric | Target | Actual |
|--------|--------|--------|
| Time to first action | 5 min | _ |
| Time to restore complete | 30 min | _ |
| Time to verify green | 60 min | _ |
| Data loss (PITR window) | < 1 min | _ |

If actual > target for any row: open a P1 ticket to reduce the gap
before the next drill.

---

## 5. Related dashboards & alerts

- **CloudWatch** alarm `em-backup-canary-failed` — pages on-call when
  the nightly `verify_backup.py` job exits non-zero two runs in a row.
- **Supabase dashboard** Project → Database → Stats — free-disk %,
  connection count, query latency.
- **Grafana** (if `Task 6.1` Prometheus is live) — `supabase_up` gauge,
  `db_verify_backup_last_success_timestamp`.

---

## 6. Change log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-17 | Initial runbook (Phase 6.3) | Platform SRE |
