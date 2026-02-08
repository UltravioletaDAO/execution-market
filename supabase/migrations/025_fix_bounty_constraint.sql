-- Fix 0: Allow small bounties (test tasks $0.01+)
-- The original CHECK constraint requires bounty_usd >= 1, but platform_config
-- allows bounty.min_usd = 0.01 and test tasks use $0.05-$0.50.

ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_bounty_usd_check;
ALTER TABLE tasks ADD CONSTRAINT tasks_bounty_usd_check CHECK (bounty_usd >= 0.01);
