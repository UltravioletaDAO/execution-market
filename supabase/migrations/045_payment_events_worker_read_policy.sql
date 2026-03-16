-- Migration 045: Allow workers to read payment events for their tasks
-- The payment_events table previously only had service_role access.
-- Workers (authenticated via anonymous sign-in) need to read payment events
-- to display TX links in the mobile app task detail timeline.

CREATE POLICY "Workers can read payment events for their tasks"
    ON payment_events
    FOR SELECT
    TO authenticated
    USING (
        task_id IN (
            SELECT id FROM tasks
            WHERE executor_id IN (
                SELECT e.id FROM executors e
                WHERE e.user_id = auth.uid()
            )
        )
    );
