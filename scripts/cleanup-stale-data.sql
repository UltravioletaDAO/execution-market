-- Phase E: Cleanup Stale Data SQL Script for Execution Market
-- 
-- This script safely archives stale data without hard-deleting anything.
-- It adds an archived_at column and sets it for tasks that should be cleaned up.
-- 
-- IMPORTANT: Do NOT run this script directly. Review it first, then execute with caution.
-- This is a DML script that modifies production data.

-- =============================================================================
-- ADD ARCHIVED_AT COLUMN (if it doesn't exist)
-- =============================================================================

-- Check if archived_at column exists, add it if not
DO $$ 
BEGIN
    -- Add archived_at column to tasks table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tasks' 
        AND column_name = 'archived_at'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.tasks 
        ADD COLUMN archived_at TIMESTAMPTZ NULL;
        
        RAISE NOTICE 'Added archived_at column to tasks table';
    ELSE
        RAISE NOTICE 'archived_at column already exists in tasks table';
    END IF;
END $$;

-- =============================================================================
-- CLEANUP RULE 1: Archive published tasks without escrow that are > 7 days old
-- =============================================================================

-- Archive tasks that have status='published', no escrow_tx, and are older than 7 days
-- These are likely incomplete task creations that never got proper escrow setup
UPDATE public.tasks 
SET 
    archived_at = NOW(),
    updated_at = NOW()
WHERE 
    status = 'published' 
    AND escrow_tx IS NULL 
    AND created_at < NOW() - INTERVAL '7 days'
    AND archived_at IS NULL; -- Don't re-archive already archived tasks

-- Display what was archived
DO $$
DECLARE
    archived_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO archived_count
    FROM public.tasks 
    WHERE 
        status = 'published' 
        AND escrow_tx IS NULL 
        AND created_at < NOW() - INTERVAL '7 days'
        AND archived_at IS NOT NULL;
        
    RAISE NOTICE 'Archived % published tasks without escrow older than 7 days', archived_count;
END $$;

-- =============================================================================
-- CLEANUP RULE 2: Archive accepted tasks with passed deadlines
-- =============================================================================

-- Archive tasks that are stuck in 'accepted' status but their deadline has already passed
-- These tasks should have been completed or transitioned to a different state
UPDATE public.tasks 
SET 
    archived_at = NOW(),
    updated_at = NOW()
WHERE 
    status = 'accepted' 
    AND deadline < NOW()
    AND archived_at IS NULL; -- Don't re-archive already archived tasks

-- Display what was archived
DO $$
DECLARE
    archived_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO archived_count
    FROM public.tasks 
    WHERE 
        status = 'accepted' 
        AND deadline < NOW()
        AND archived_at IS NOT NULL;
        
    RAISE NOTICE 'Archived % accepted tasks with passed deadlines', archived_count;
END $$;

-- =============================================================================
-- SUMMARY REPORT
-- =============================================================================

-- Show summary of archived tasks
DO $$
DECLARE
    total_archived INTEGER;
    archived_by_status RECORD;
BEGIN
    -- Count total archived tasks
    SELECT COUNT(*) INTO total_archived
    FROM public.tasks 
    WHERE archived_at IS NOT NULL;
    
    RAISE NOTICE '=== CLEANUP SUMMARY ===';
    RAISE NOTICE 'Total archived tasks: %', total_archived;
    RAISE NOTICE '';
    RAISE NOTICE 'Archived tasks by original status:';
    
    -- Show breakdown by status
    FOR archived_by_status IN 
        SELECT 
            status,
            COUNT(*) as count
        FROM public.tasks 
        WHERE archived_at IS NOT NULL
        GROUP BY status
        ORDER BY COUNT(*) DESC
    LOOP
        RAISE NOTICE '  %: %', archived_by_status.status, archived_by_status.count;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Recent archives (last 1 hour):';
    
    -- Show recently archived tasks
    FOR archived_by_status IN
        SELECT 
            id,
            title,
            status,
            EXTRACT(EPOCH FROM (NOW() - archived_at))/60 as minutes_ago
        FROM public.tasks 
        WHERE archived_at > NOW() - INTERVAL '1 hour'
        ORDER BY archived_at DESC
        LIMIT 10
    LOOP
        RAISE NOTICE '  % | % | % (%.1f min ago)', 
            SUBSTRING(archived_by_status.id::text, 1, 8),
            archived_by_status.status,
            SUBSTRING(archived_by_status.title, 1, 40),
            archived_by_status.minutes_ago;
    END LOOP;
END $$;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Run these queries to verify the cleanup was successful:

/*
-- 1. Check how many tasks are now archived
SELECT 
    'Total archived tasks' as metric,
    COUNT(*) as count
FROM public.tasks 
WHERE archived_at IS NOT NULL

UNION ALL

-- 2. Check breakdown by status
SELECT 
    'Archived ' || status as metric,
    COUNT(*) as count
FROM public.tasks 
WHERE archived_at IS NOT NULL
GROUP BY status;

-- 3. Verify no more stale published tasks without escrow
SELECT 
    'Stale published tasks (should be 0)' as metric,
    COUNT(*) as count
FROM public.tasks 
WHERE 
    status = 'published' 
    AND escrow_tx IS NULL 
    AND created_at < NOW() - INTERVAL '7 days'
    AND archived_at IS NULL;

-- 4. Verify no more stale accepted tasks with passed deadlines
SELECT 
    'Stale accepted tasks (should be 0)' as metric,
    COUNT(*) as count
FROM public.tasks 
WHERE 
    status = 'accepted' 
    AND deadline < NOW()
    AND archived_at IS NULL;
*/

-- =============================================================================
-- ROLLBACK INSTRUCTIONS
-- =============================================================================

/*
If you need to rollback this cleanup, run:

-- Unarchive all tasks that were archived by this script
UPDATE public.tasks 
SET 
    archived_at = NULL,
    updated_at = NOW()
WHERE archived_at IS NOT NULL;

-- Or remove the column entirely
ALTER TABLE public.tasks DROP COLUMN IF EXISTS archived_at;
*/

-- =============================================================================
-- SAFETY NOTES
-- =============================================================================

/*
SAFETY CHECKLIST before running:
□ Database backup created
□ Script reviewed by senior developer  
□ Test run performed on staging environment
□ Business stakeholders notified
□ Rollback plan confirmed

This script:
✅ Does NOT hard-delete any data
✅ Only adds archived_at timestamps  
✅ Is idempotent (safe to run multiple times)
✅ Includes verification queries
✅ Provides rollback instructions

Data affected:
- Tasks with status='published', no escrow_tx, older than 7 days
- Tasks with status='accepted' where deadline has passed

The archived tasks remain in the database but can be filtered out
from normal operations by checking archived_at IS NULL.
*/