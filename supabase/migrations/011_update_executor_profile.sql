-- ============================================================================
-- EXECUTION MARKET: Human Execution Layer for AI Agents
-- Migration: 011_update_executor_profile.sql
-- Description: Add RPC function for updating executor profile (bypasses RLS)
-- Version: 2.0.1
-- Date: 2026-02-04
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Update Executor Profile
-- ---------------------------------------------------------------------------
-- This function allows updating executor profiles without Supabase session auth.
-- Required because Dynamic.xyz wallet auth doesn't create Supabase sessions,
-- so all dashboard users are "anonymous" from Supabase's perspective.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_executor_profile(
    p_executor_id UUID,
    p_display_name TEXT DEFAULT NULL,
    p_bio TEXT DEFAULT NULL,
    p_skills TEXT[] DEFAULT NULL,
    p_languages TEXT[] DEFAULT NULL,
    p_location_city TEXT DEFAULT NULL,
    p_location_country TEXT DEFAULT NULL,
    p_email TEXT DEFAULT NULL
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
        last_active_at = NOW()
    WHERE id = p_executor_id;

    RETURN jsonb_build_object(
        'success', true,
        'executor_id', p_executor_id,
        'updated_at', NOW()
    );
END;
$$;

-- Grant execute to anon (Dynamic.xyz users don't have Supabase sessions)
GRANT EXECUTE ON FUNCTION update_executor_profile TO anon;
GRANT EXECUTE ON FUNCTION update_executor_profile TO authenticated;

-- Also grant get_or_create_executor to anon (both overloads)
GRANT EXECUTE ON FUNCTION get_or_create_executor(TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION get_or_create_executor(TEXT, TEXT, TEXT, TEXT, TEXT) TO anon;

COMMENT ON FUNCTION update_executor_profile IS 'Update executor profile fields (bypasses RLS for Dynamic.xyz auth)';
