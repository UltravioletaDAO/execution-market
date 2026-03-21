-- Add preferred_language column to executors table
ALTER TABLE executors ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(5) DEFAULT 'en';
