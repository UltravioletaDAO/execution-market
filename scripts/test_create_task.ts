/**
 * Execution Market Test Script - Create a Simple Test Task
 *
 * Creates a task directly in Supabase to test the dashboard.
 * No payments involved - just database insertion.
 *
 * Usage:
 *   cd scripts
 *   npx tsx test_create_task.ts
 */

import { createClient } from '@supabase/supabase-js';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { randomUUID } from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment
config({ path: resolve(__dirname, '../.env.local') });

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://puyhpytmtkyevnxffksl.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;

if (!SUPABASE_KEY) {
  console.error('Missing SUPABASE_ANON_KEY or SUPABASE_SERVICE_KEY');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// Test task data
const TEST_TASK = {
  id: randomUUID(),
  agent_id: 'test-agent-' + Date.now(),
  title: 'Test Task - Verify Coffee Shop Hours',
  instructions: `
Please visit the coffee shop at the specified location and verify:
1. Current business hours displayed on the door
2. Whether they are currently open
3. Take a photo of the storefront showing the hours

This is a TEST TASK created at ${new Date().toISOString()}
  `.trim(),
  category: 'physical_presence',
  status: 'published',
  bounty_usd: 5.00,
  deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24 hours
  evidence_required: ['photo_geo', 'text_response'],
  evidence_optional: ['photo'],
  location_hint: 'Downtown area, any coffee shop',
  min_reputation: 0,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

async function main() {
  console.log('===========================================');
  console.log('  Execution Market Test Task Creator');
  console.log('===========================================\n');

  console.log('Supabase URL:', SUPABASE_URL);
  console.log('Task ID:', TEST_TASK.id);
  console.log('Title:', TEST_TASK.title);
  console.log('Bounty: $' + TEST_TASK.bounty_usd);
  console.log('');

  // Insert task
  console.log('Creating task...');
  const { data, error } = await supabase
    .from('tasks')
    .insert(TEST_TASK)
    .select()
    .single();

  if (error) {
    console.error('Error creating task:', error.message);
    console.error('Details:', error);
    process.exit(1);
  }

  console.log('\n[OK] Task created successfully!');
  console.log('');
  console.log('Task Details:');
  console.log('  ID:', data.id);
  console.log('  Title:', data.title);
  console.log('  Status:', data.status);
  console.log('  Bounty: $' + data.bounty_usd);
  console.log('  Deadline:', data.deadline);
  console.log('');
  console.log('View in dashboard:');
  console.log('  https://app.execution.market/tasks/' + data.id);
  console.log('');

  // Verify task count
  const { count } = await supabase
    .from('tasks')
    .select('*', { count: 'exact', head: true })
    .eq('status', 'published');

  console.log('Total published tasks:', count);
}

main().catch(console.error);
