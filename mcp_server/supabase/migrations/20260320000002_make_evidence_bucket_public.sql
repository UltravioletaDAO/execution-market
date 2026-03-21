-- ============================================================================
-- Migration 011: Make evidence storage bucket public for reads
-- ============================================================================
-- FIX: Evidence uploaded from web dashboard falls back to Supabase Storage
-- when VITE_EVIDENCE_API_URL is not configured. The bucket is private by
-- default, so fileUrl links return 403 on the dashboard.
--
-- This migration:
-- 1. Makes the 'evidence' bucket public (allows unauthenticated reads)
-- 2. Adds a public SELECT policy so anyone can view evidence files
--
-- NOTE: New uploads will go to S3/CloudFront now that VITE_EVIDENCE_API_URL
-- is configured. This fix is for EXISTING evidence stored in Supabase.
-- ============================================================================

-- Make the evidence bucket public for reads
UPDATE storage.buckets
SET public = true
WHERE id = 'evidence';

-- Allow public read access to evidence files
-- Drop first in case it already exists
DROP POLICY IF EXISTS "Public evidence read access" ON storage.objects;
CREATE POLICY "Public evidence read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'evidence');
