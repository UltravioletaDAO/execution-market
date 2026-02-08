-- ============================================================================
-- EXECUTION MARKET: Human Execution Layer for AI Agents
-- Migration: 024_update_executor_profile_v2.sql
-- Description: Add avatar_url and phone parameters to update_executor_profile RPC
-- Version: 2.0.2
-- Date: 2026-02-07
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Update Executor Profile v2
-- ---------------------------------------------------------------------------
-- Adds p_avatar_url and p_phone to the existing RPC so the dashboard can
-- persist avatar uploads and phone numbers without a direct table update.
-- ---------------------------------------------------------------------------

-- Drop the old 8-param overload from migration 011 so we don't end up with
-- two ambiguous signatures.  The new 10-param version replaces it entirely.
DROP FUNCTION IF EXISTS update_executor_profile(UUID, TEXT, TEXT, TEXT[], TEXT[], TEXT, TEXT, TEXT);

CREATE OR REPLACE FUNCTION update_executor_profile(
    p_executor_id UUID,
    p_display_name TEXT DEFAULT NULL,
    p_bio TEXT DEFAULT NULL,
    p_skills TEXT[] DEFAULT NULL,
    p_languages TEXT[] DEFAULT NULL,
    p_location_city TEXT DEFAULT NULL,
    p_location_country TEXT DEFAULT NULL,
    p_email TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_phone TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_executor executors%ROWTYPE;
BEGIN
    -- Get existing executor
    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;

    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Executor not found'
        );
    END IF;

    -- Update profile fields (only update non-null parameters)
    UPDATE executors
    SET
        display_name = COALESCE(p_display_name, executors.display_name),
        bio = CASE WHEN p_bio IS NOT NULL THEN p_bio ELSE executors.bio END,
        skills = CASE WHEN p_skills IS NOT NULL THEN p_skills ELSE executors.skills END,
        languages = CASE WHEN p_languages IS NOT NULL THEN p_languages ELSE executors.languages END,
        location_city = CASE WHEN p_location_city IS NOT NULL THEN p_location_city ELSE executors.location_city END,
        location_country = CASE WHEN p_location_country IS NOT NULL THEN p_location_country ELSE executors.location_country END,
        email = CASE WHEN p_email IS NOT NULL THEN p_email ELSE executors.email END,
        avatar_url = CASE WHEN p_avatar_url IS NOT NULL THEN p_avatar_url ELSE executors.avatar_url END,
        phone = CASE WHEN p_phone IS NOT NULL THEN p_phone ELSE executors.phone END,
        last_active_at = NOW()
    WHERE id = p_executor_id;

    RETURN jsonb_build_object(
        'success', true,
        'executor_id', p_executor_id,
        'updated_at', NOW()
    );
END;
$$;

-- Re-grant with explicit signature to avoid ambiguity
GRANT EXECUTE ON FUNCTION update_executor_profile(UUID, TEXT, TEXT, TEXT[], TEXT[], TEXT, TEXT, TEXT, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION update_executor_profile(UUID, TEXT, TEXT, TEXT[], TEXT[], TEXT, TEXT, TEXT, TEXT, TEXT) TO authenticated;

COMMENT ON FUNCTION update_executor_profile(UUID, TEXT, TEXT, TEXT[], TEXT[], TEXT, TEXT, TEXT, TEXT, TEXT)
    IS 'Update executor profile fields including avatar and phone (bypasses RLS for Dynamic.xyz auth)';
