-- Migration 033: Agent Cards - Universal agent identity system
-- Adds agent_type, networks_active columns and activity_feed table

-- ============================================================================
-- 1. Add agent_type column to executors
-- ============================================================================
ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS agent_type TEXT DEFAULT 'human'
  CHECK (agent_type IN ('human', 'ai', 'organization'));

CREATE INDEX IF NOT EXISTS idx_executors_agent_type ON executors(agent_type);

-- ============================================================================
-- 2. Add networks_active column to executors
-- ============================================================================
ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS networks_active TEXT[] DEFAULT '{}';

-- ============================================================================
-- 3. Create activity_feed table
-- ============================================================================
CREATE TABLE IF NOT EXISTS activity_feed (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL, -- 'task_created', 'task_accepted', 'task_completed', 'feedback_given', 'worker_joined', 'dispute_opened', 'dispute_resolved'
  actor_wallet TEXT NOT NULL,
  actor_name TEXT,
  actor_type TEXT DEFAULT 'human',
  target_wallet TEXT,
  target_name TEXT,
  task_id UUID REFERENCES tasks(id),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_feed_created ON activity_feed(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_feed_actor ON activity_feed(actor_wallet);
CREATE INDEX IF NOT EXISTS idx_activity_feed_type ON activity_feed(event_type);

-- ============================================================================
-- 4. RLS policies for activity_feed
-- ============================================================================
ALTER TABLE activity_feed ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "activity_feed_read_public" ON activity_feed
  FOR SELECT
  USING (true);

-- Insert only for service_role (backend/triggers)
CREATE POLICY "activity_feed_insert_service" ON activity_feed
  FOR INSERT
  WITH CHECK (
    current_setting('role', true) = 'service_role'
    OR current_setting('request.jwt.claims', true)::jsonb->>'role' = 'service_role'
  );

-- ============================================================================
-- 5. Trigger function to auto-populate activity_feed on task status changes
-- ============================================================================
CREATE OR REPLACE FUNCTION fn_activity_feed_on_task_change()
RETURNS TRIGGER AS $$
DECLARE
  v_actor_wallet TEXT;
  v_actor_name TEXT;
  v_actor_type TEXT;
  v_target_wallet TEXT;
  v_target_name TEXT;
  v_event_type TEXT;
BEGIN
  -- Determine event type based on status transition
  IF TG_OP = 'INSERT' AND NEW.status = 'published' THEN
    v_event_type := 'task_created';
    v_actor_wallet := NEW.agent_id;
    -- Look up agent name
    SELECT display_name, agent_type INTO v_actor_name, v_actor_type
      FROM executors WHERE wallet_address = NEW.agent_id LIMIT 1;

  ELSIF TG_OP = 'UPDATE' AND OLD.status != NEW.status THEN
    CASE NEW.status
      WHEN 'accepted' THEN
        v_event_type := 'task_accepted';
        -- Worker accepted
        IF NEW.executor_id IS NOT NULL THEN
          SELECT wallet_address, display_name, agent_type
            INTO v_actor_wallet, v_actor_name, v_actor_type
            FROM executors WHERE id = NEW.executor_id LIMIT 1;
        END IF;
        v_target_wallet := NEW.agent_id;
        SELECT display_name INTO v_target_name
          FROM executors WHERE wallet_address = NEW.agent_id LIMIT 1;

      WHEN 'completed' THEN
        v_event_type := 'task_completed';
        IF NEW.executor_id IS NOT NULL THEN
          SELECT wallet_address, display_name, agent_type
            INTO v_actor_wallet, v_actor_name, v_actor_type
            FROM executors WHERE id = NEW.executor_id LIMIT 1;
        END IF;
        v_target_wallet := NEW.agent_id;

      WHEN 'disputed' THEN
        v_event_type := 'dispute_opened';
        v_actor_wallet := NEW.agent_id;
        SELECT display_name, agent_type INTO v_actor_name, v_actor_type
          FROM executors WHERE wallet_address = NEW.agent_id LIMIT 1;

      ELSE
        -- Other status changes don't generate feed events
        RETURN NEW;
    END CASE;
  ELSE
    RETURN COALESCE(NEW, OLD);
  END IF;

  -- Insert activity feed entry (skip if no actor wallet)
  IF v_actor_wallet IS NOT NULL THEN
    INSERT INTO activity_feed (event_type, actor_wallet, actor_name, actor_type, target_wallet, target_name, task_id, metadata)
    VALUES (
      v_event_type,
      v_actor_wallet,
      v_actor_name,
      COALESCE(v_actor_type, 'human'),
      v_target_wallet,
      v_target_name,
      NEW.id,
      jsonb_build_object('task_title', NEW.title, 'bounty_usd', NEW.bounty_usd, 'category', NEW.category)
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger
DROP TRIGGER IF EXISTS trg_activity_feed_on_task ON tasks;
CREATE TRIGGER trg_activity_feed_on_task
  AFTER INSERT OR UPDATE OF status ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION fn_activity_feed_on_task_change();
