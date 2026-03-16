-- Migration 059: Evidence Schema Validation
-- Source: DB Optimization Audit 2026-03-15 (Phase 4, Task 4.4)
-- tasks.evidence_schema is JSONB NOT NULL with a default, but there is
-- no validation that the structure is correct. This CHECK ensures the
-- schema always has 'required' and 'optional' arrays.
-- Applied to production: pending.

-- First verify all existing rows satisfy the constraint
-- (default is '{"required": ["photo"], "optional": []}' which passes)
-- If any row fails, this ALTER will error — fix data first.
ALTER TABLE tasks ADD CONSTRAINT chk_tasks_evidence_schema_valid CHECK (
    evidence_schema ? 'required'
    AND evidence_schema ? 'optional'
    AND jsonb_typeof(evidence_schema->'required') = 'array'
    AND jsonb_typeof(evidence_schema->'optional') = 'array'
);
