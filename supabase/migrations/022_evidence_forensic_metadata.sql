-- Migration 022: Add forensic metadata fields to submissions
-- Captures GPS, device info, EXIF data, content checksums for evidence integrity.
-- Safe to re-run (all IF NOT EXISTS / CREATE OR REPLACE).

-- Evidence metadata JSONB: GPS, device, EXIF, source detection, checksums
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS evidence_metadata JSONB DEFAULT '{}'::jsonb;
COMMENT ON COLUMN submissions.evidence_metadata IS 'Forensic metadata: { gps, device, exif, source, checksums, capture_timestamp }';

-- Storage backend used for this submission (supabase, s3, ipfs)
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(20) DEFAULT 'supabase';
COMMENT ON COLUMN submissions.storage_backend IS 'Where evidence files are stored: supabase, s3, ipfs';

-- SHA-256 content hash of all evidence files (for tamper detection)
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS evidence_content_hash VARCHAR(66);
COMMENT ON COLUMN submissions.evidence_content_hash IS 'SHA-256 hash of concatenated evidence files for tamper detection';

-- Index for metadata queries (GIN for JSONB containment)
CREATE INDEX IF NOT EXISTS idx_submissions_evidence_metadata
  ON submissions USING GIN (evidence_metadata);

-- Index for storage backend filtering
CREATE INDEX IF NOT EXISTS idx_submissions_storage_backend
  ON submissions(storage_backend);
