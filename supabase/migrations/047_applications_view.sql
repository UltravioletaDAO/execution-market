-- Create a view "applications" pointing to "task_applications" for backward compatibility.
-- The RPC functions (apply_to_task, get_executor_dashboard, assign_task) reference
-- "applications" but the canonical table is "task_applications".
-- Applied to production 2026-03-15.

CREATE OR REPLACE VIEW applications AS SELECT * FROM task_applications;

-- Allow inserts/updates/deletes through the view
CREATE OR REPLACE RULE applications_insert AS ON INSERT TO applications
    DO INSTEAD INSERT INTO task_applications VALUES (NEW.*) RETURNING *;

CREATE OR REPLACE RULE applications_update AS ON UPDATE TO applications
    DO INSTEAD UPDATE task_applications SET
        task_id = NEW.task_id,
        executor_id = NEW.executor_id,
        message = NEW.message,
        status = NEW.status,
        updated_at = NEW.updated_at
    WHERE id = OLD.id;

CREATE OR REPLACE RULE applications_delete AS ON DELETE TO applications
    DO INSTEAD DELETE FROM task_applications WHERE id = OLD.id;
