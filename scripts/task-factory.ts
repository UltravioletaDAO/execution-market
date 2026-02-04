/**
 * Execution Market Task Factory — CLI tool for creating test tasks
 *
 * Creates tasks in Supabase that appear in the dashboard for human workers.
 * Supports multiple task types, configurable bounties, deadlines, and escrow modes.
 *
 * Usage:
 *   npx tsx task-factory.ts                         # Interactive menu
 *   npx tsx task-factory.ts --preset screenshot      # Quick: screenshot task
 *   npx tsx task-factory.ts --preset photo            # Quick: photo task
 *   npx tsx task-factory.ts --preset verification     # Quick: verification task
 *   npx tsx task-factory.ts --preset fibonacci        # Create Fibonacci series of tasks
 *
 *   # Custom task:
 *   npx tsx task-factory.ts \
 *     --title "Take screenshot of X trending" \
 *     --bounty 0.21 \
 *     --deadline 15 \
 *     --category simple_action \
 *     --evidence screenshot
 *
 *   # With real escrow (Base Mainnet, requires USDC):
 *   npx tsx task-factory.ts --preset screenshot --bounty 0.21 --live
 *
 *   # Fibonacci series with real escrow:
 *   npx tsx task-factory.ts --preset fibonacci --live
 *
 *   # Clean up: cancel all test tasks
 *   npx tsx task-factory.ts --cleanup
 */

import {
  createPublicClient,
  createWalletClient,
  http,
  formatUnits,
  parseUnits,
  keccak256,
  toHex,
  type Hex,
  type Address,
} from 'viem';
import { base } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.env.local') });

// =============================================================================
// Configuration
// =============================================================================

const PRIVATE_KEY = process.env.WALLET_PRIVATE_KEY as Hex;
if (!PRIVATE_KEY) {
  console.error('ERROR: WALLET_PRIVATE_KEY not set in .env.local');
  process.exit(1);
}

const account = privateKeyToAccount(PRIVATE_KEY);
const WALLET_ADDRESS = account.address;

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://YOUR_PROJECT_REF.supabase.co';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1eWhweXRtdGt5ZXZueGZma3NsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg2NzgzOTMsImV4cCI6MjA4NDI1NDM5M30.R4Sf4SwDo-5yRhRMOazQ-4Jn972YLT7lYunjdqiGjaU';

const MCP_SERVER_URL = 'https://mcp.execution.market';
const DASHBOARD_URL = 'https://app.execution.market';

// Base Mainnet contracts
const MAINNET_FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as Address;
const MAINNET_USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as Address;

// =============================================================================
// Contract ABIs
// =============================================================================

const ERC20_ABI = [
  {
    name: 'approve', type: 'function', stateMutability: 'nonpayable' as const,
    inputs: [{ name: 'spender', type: 'address' }, { name: 'amount', type: 'uint256' }],
    outputs: [{ name: '', type: 'bool' }],
  },
  {
    name: 'balanceOf', type: 'function', stateMutability: 'view' as const,
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    name: 'allowance', type: 'function', stateMutability: 'view' as const,
    inputs: [{ name: 'owner', type: 'address' }, { name: 'spender', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

const FACTORY_ABI = [
  {
    name: 'createEscrow', type: 'function', stateMutability: 'nonpayable' as const,
    inputs: [
      { name: 'token', type: 'address' }, { name: 'amount', type: 'uint256' },
      { name: 'beneficiary', type: 'address' }, { name: 'timeout', type: 'uint256' },
      { name: 'taskId', type: 'bytes32' },
    ],
    outputs: [{ name: 'escrowId', type: 'bytes32' }],
  },
  {
    name: 'getEscrow', type: 'function', stateMutability: 'view' as const,
    inputs: [{ name: 'escrowId', type: 'bytes32' }],
    outputs: [
      { name: 'depositor', type: 'address' }, { name: 'beneficiary', type: 'address' },
      { name: 'amount', type: 'uint256' }, { name: 'timeout', type: 'uint256' },
      { name: 'released', type: 'bool' }, { name: 'refunded', type: 'bool' },
    ],
  },
  {
    name: 'refundEscrow', type: 'function', stateMutability: 'nonpayable' as const,
    inputs: [{ name: 'escrowId', type: 'bytes32' }],
    outputs: [],
  },
  {
    name: 'releaseEscrow', type: 'function', stateMutability: 'nonpayable' as const,
    inputs: [{ name: 'escrowId', type: 'bytes32' }],
    outputs: [],
  },
] as const;

// =============================================================================
// Task Presets
// =============================================================================

interface TaskPreset {
  title: string;
  instructions: string;
  category: string;
  evidence_schema: { required: string[]; optional: string[] };
  location_hint: string;
  required_roles: string[];
}

const PRESETS: Record<string, TaskPreset> = {
  screenshot: {
    title: 'Take a screenshot of X (Twitter) trending topics',
    instructions:
      'Open x.com (Twitter) on your browser. Navigate to the Explore/Trending page. ' +
      'Take a full-screen screenshot showing the current trending topics. ' +
      'The screenshot must include the date/time visible on screen and at least 5 trending topics.',
    category: 'simple_action',
    evidence_schema: { required: ['screenshot'], optional: ['description'] },
    location_hint: 'Remote',
    required_roles: [],
  },
  photo: {
    title: 'Take a photo of a local business storefront',
    instructions:
      'Go to any local business in your area. Take a clear photo of the storefront ' +
      'showing the business name, address, and opening hours if visible. ' +
      'The photo must be taken during daylight hours and be clearly readable.',
    category: 'physical_presence',
    evidence_schema: { required: ['photo', 'location'], optional: ['description'] },
    location_hint: 'Any city',
    required_roles: [],
  },
  verification: {
    title: 'Verify a Google Maps listing is accurate',
    instructions:
      'Visit the business at the provided address. Confirm: (1) The business exists, ' +
      '(2) The name matches the listing, (3) Operating hours are correct. ' +
      'Take a photo of the storefront as proof. Report any discrepancies.',
    category: 'physical_presence',
    evidence_schema: { required: ['photo', 'report'], optional: ['location'] },
    location_hint: 'Any city',
    required_roles: ['verification'],
  },
  delivery: {
    title: 'Pick up and deliver a small package',
    instructions:
      'Pick up a document/small package from Point A and deliver to Point B within ' +
      'the deadline. Take a photo of the package at pickup and at delivery. ' +
      'Confirm delivery with a photo of the recipient or drop-off location.',
    category: 'simple_action',
    evidence_schema: { required: ['photo_pickup', 'photo_delivery'], optional: ['description'] },
    location_hint: 'Local',
    required_roles: ['delivery'],
  },
  translation: {
    title: 'Translate a short document from English to Spanish',
    instructions:
      'Translate the following text into natural, fluent Spanish. ' +
      'The translation should read naturally, not word-for-word. ' +
      'Submit the translated text as your evidence. Text: ' +
      '"The execution market connects AI agents with human workers for tasks that require ' +
      'physical presence, local knowledge, or human judgment. Workers are paid instantly via ' +
      'blockchain escrow upon task completion and verification."',
    category: 'human_authority',
    evidence_schema: { required: ['text'], optional: [] },
    location_hint: 'Remote',
    required_roles: ['translation'],
  },
  data_collection: {
    title: 'Collect prices of 5 items at a local grocery store',
    instructions:
      'Visit a local grocery store and record the prices of: milk (1L), bread (loaf), ' +
      'eggs (dozen), rice (1kg), and bananas (1kg). Take a photo of each price tag. ' +
      'Submit all 5 photos with the store name and date.',
    category: 'knowledge_access',
    evidence_schema: { required: ['photos', 'price_list'], optional: ['store_name', 'location'] },
    location_hint: 'Any city',
    required_roles: ['data_collection'],
  },
};

// Fibonacci bounty amounts in USD
const FIBONACCI_BOUNTIES = [0.01, 0.02, 0.03, 0.05, 0.08, 0.13, 0.21, 0.34, 0.55, 0.89];

// =============================================================================
// Helpers
// =============================================================================

async function supabaseRequest(
  path: string,
  method: 'GET' | 'POST' | 'PATCH' = 'GET',
  body?: Record<string, unknown>,
  returnSingle = false,
): Promise<any> {
  const headers: Record<string, string> = {
    apikey: SUPABASE_ANON_KEY,
    Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
    'Content-Type': 'application/json',
  };
  if (returnSingle) headers['Accept'] = 'application/vnd.pgrst.object+json';
  if (method === 'POST' || method === 'PATCH') headers['Prefer'] = 'return=representation';

  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Supabase ${method} ${path} failed (${res.status}): ${text}`);
  }

  const text = await res.text();
  if (!text) return null;
  return JSON.parse(text);
}

function parseArgs(): Record<string, string> {
  const args: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      // Flags without values
      if (key === 'live' || key === 'cleanup' || key === 'monitor') {
        args[key] = 'true';
      } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
        args[key] = argv[i + 1];
        i++;
      } else {
        args[key] = 'true';
      }
    }
  }
  return args;
}

async function checkUSDCBalance(): Promise<bigint> {
  const publicClient = createPublicClient({ chain: base, transport: http() });
  return publicClient.readContract({
    address: MAINNET_USDC,
    abi: ERC20_ABI,
    functionName: 'balanceOf',
    args: [WALLET_ADDRESS],
  });
}

async function createOnChainEscrow(
  taskId: string,
  bountyUsd: number,
  deadlineMinutes: number,
): Promise<{ escrowTx: string; escrowId: string }> {
  const publicClient = createPublicClient({ chain: base, transport: http() });
  const walletClient = createWalletClient({ account, chain: base, transport: http() });
  const bountyUnits = parseUnits(bountyUsd.toFixed(6), 6);
  const taskIdBytes32 = keccak256(toHex(taskId)) as Hex;

  // Check balance
  const balance = await checkUSDCBalance();
  if (balance < bountyUnits) {
    throw new Error(
      `Insufficient USDC: need ${formatUnits(bountyUnits, 6)} but have ${formatUnits(balance, 6)}. ` +
      `Fund wallet ${WALLET_ADDRESS} on Base Mainnet.`
    );
  }

  // Approve if needed
  const allowance = await publicClient.readContract({
    address: MAINNET_USDC,
    abi: ERC20_ABI,
    functionName: 'allowance',
    args: [WALLET_ADDRESS, MAINNET_FACTORY],
  });

  if (allowance < bountyUnits) {
    console.log('  Approving USDC...');
    const approveTx = await walletClient.writeContract({
      address: MAINNET_USDC,
      abi: ERC20_ABI,
      functionName: 'approve',
      args: [MAINNET_FACTORY, parseUnits('100', 6)],
    });
    await publicClient.waitForTransactionReceipt({ hash: approveTx });
    console.log(`  Approved: https://basescan.org/tx/${approveTx}`);
  }

  // Create escrow
  const timeoutTimestamp = BigInt(Math.floor(Date.now() / 1000) + deadlineMinutes * 60);
  console.log('  Creating on-chain escrow...');

  const depositHash = await walletClient.writeContract({
    address: MAINNET_FACTORY,
    abi: FACTORY_ABI,
    functionName: 'createEscrow',
    args: [MAINNET_USDC, bountyUnits, WALLET_ADDRESS, timeoutTimestamp, taskIdBytes32],
  });

  const receipt = await publicClient.waitForTransactionReceipt({ hash: depositHash });
  if (receipt.status !== 'success') {
    throw new Error('createEscrow transaction reverted');
  }

  return { escrowTx: depositHash, escrowId: taskIdBytes32 };
}

// =============================================================================
// Core: Create a task
// =============================================================================

interface CreateTaskOptions {
  title: string;
  instructions: string;
  category: string;
  bountyUsd: number;
  deadlineMinutes: number;
  evidenceSchema: { required: string[]; optional: string[] };
  locationHint: string;
  requiredRoles: string[];
  liveEscrow: boolean;
}

async function createTask(opts: CreateTaskOptions): Promise<{
  taskId: string;
  escrowTx: string | null;
  escrowId: string | null;
  bountyUsd: number;
  deadline: string;
}> {
  const deadline = new Date(Date.now() + opts.deadlineMinutes * 60 * 1000).toISOString();

  const payload = {
    title: opts.title,
    instructions: opts.instructions,
    category: opts.category,
    bounty_usd: opts.bountyUsd,
    payment_token: 'USDC',
    status: 'published',
    agent_id: WALLET_ADDRESS,
    deadline,
    location_hint: opts.locationHint,
    evidence_schema: opts.evidenceSchema,
    min_reputation: 0,
    required_roles: opts.requiredRoles,
    max_executors: 1,
  };

  const [task] = await supabaseRequest('tasks', 'POST', payload);
  const taskId = task.id;

  let escrowTx: string | null = null;
  let escrowId: string | null = null;

  if (opts.liveEscrow) {
    const result = await createOnChainEscrow(taskId, opts.bountyUsd, opts.deadlineMinutes);
    escrowTx = result.escrowTx;
    escrowId = result.escrowId;
  } else {
    // Simulated escrow markers
    escrowTx = `0x${'0'.repeat(58)}sim${Math.random().toString(16).slice(2, 6)}`;
    escrowId = keccak256(toHex(taskId)) as string;
  }

  // Update task with escrow info
  await supabaseRequest(`tasks?id=eq.${taskId}`, 'PATCH', {
    escrow_tx: escrowTx,
    escrow_id: escrowId,
  });

  return { taskId, escrowTx, escrowId, bountyUsd: opts.bountyUsd, deadline };
}

// =============================================================================
// Monitor a task until completion or expiry
// =============================================================================

async function monitorTask(
  taskId: string,
  deadline: string,
  escrowId: string | null,
  liveMode: boolean,
): Promise<string> {
  const deadlineMs = new Date(deadline).getTime();
  let lastStatus = 'published';
  const POLL_MS = 15_000;

  console.log('\nMonitoring task...');
  console.log('  The MCP server task_expiration job runs every 60s.');
  console.log('  Press Ctrl+C to stop monitoring.\n');

  while (true) {
    const now = Date.now();
    const remaining = deadlineMs - now;

    const currentTask = await supabaseRequest(
      `tasks?id=eq.${taskId}&select=status,executor_id`,
      'GET',
      undefined,
      true,
    );
    const status = currentTask?.status || 'unknown';

    if (status !== lastStatus) {
      console.log(`  ** Status changed: ${lastStatus} -> ${status}`);
      lastStatus = status;
    }

    if (['expired', 'completed', 'cancelled'].includes(status)) {
      console.log(`\nTask reached terminal state: ${status}`);
      break;
    }

    if (status === 'accepted' || status === 'in_progress') {
      const eid = currentTask?.executor_id;
      console.log(`\nTask picked up by worker${eid ? ' (' + eid.slice(0, 8) + '...)' : ''}`);
      console.log('Waiting for submission...');
    }

    if (status === 'submitted' || status === 'verifying') {
      console.log(`\nTask has a submission! Status: ${status}`);
      console.log('Waiting for approval...');
    }

    if (remaining > 0) {
      const min = Math.floor(remaining / 60000);
      const sec = Math.floor((remaining % 60000) / 1000);
      console.log(`  Status: ${status} | Time remaining: ${min}:${sec.toString().padStart(2, '0')}`);
    } else {
      const overdueS = Math.floor((now - deadlineMs) / 1000);
      console.log(`  Status: ${status} | Overdue: ${overdueS}s`);
      if (overdueS > 300) {
        console.error('Task not expired after 5 minutes overdue. MCP job may not be running.');
        break;
      }
    }

    await new Promise((r) => setTimeout(r, POLL_MS));
  }

  // Verify on-chain state if live
  if (liveMode && escrowId) {
    console.log('\nChecking on-chain escrow state...');
    const publicClient = createPublicClient({ chain: base, transport: http() });
    try {
      const escrowState = await publicClient.readContract({
        address: MAINNET_FACTORY,
        abi: FACTORY_ABI,
        functionName: 'getEscrow',
        args: [escrowId as Hex],
      });
      const [depositor, beneficiary, amount, timeout, released, refunded] = escrowState;
      console.log('  Depositor:', depositor);
      console.log('  Amount:', formatUnits(amount, 6), 'USDC');
      console.log('  Released:', released);
      console.log('  Refunded:', refunded);
      if (refunded) console.log('  REFUND TX confirmed on-chain');
      if (released) console.log('  PAYMENT released to worker on-chain');
    } catch (err: any) {
      console.log(`  Could not read escrow: ${err.message?.slice(0, 100)}`);
    }
  }

  return lastStatus;
}

// =============================================================================
// Preset runners
// =============================================================================

async function runPreset(presetName: string, args: Record<string, string>): Promise<void> {
  const preset = PRESETS[presetName];
  if (!preset) {
    console.error(`Unknown preset: ${presetName}`);
    console.error('Available presets:', Object.keys(PRESETS).join(', '), '+ fibonacci');
    process.exit(1);
  }

  const bounty = parseFloat(args.bounty || '0.21');
  const deadline = parseInt(args.deadline || '15', 10);
  const liveMode = args.live === 'true';
  const shouldMonitor = args.monitor === 'true';

  console.log(`\n=== Creating Task: ${presetName} ===`);
  console.log(`Bounty: $${bounty.toFixed(2)} | Deadline: ${deadline}min | Mode: ${liveMode ? 'LIVE (Base Mainnet)' : 'Simulated'}`);
  console.log(`Wallet: ${WALLET_ADDRESS}\n`);

  const result = await createTask({
    title: preset.title,
    instructions: preset.instructions,
    category: preset.category,
    bountyUsd: bounty,
    deadlineMinutes: deadline,
    evidenceSchema: preset.evidence_schema,
    locationHint: preset.location_hint,
    requiredRoles: preset.required_roles,
    liveEscrow: liveMode,
  });

  printTaskResult(result, liveMode);

  if (shouldMonitor) {
    await monitorTask(result.taskId, result.deadline, result.escrowId, liveMode);
  }
}

async function runCustom(args: Record<string, string>): Promise<void> {
  const title = args.title;
  const instructions = args.instructions || `Complete the task: ${title}`;
  const bounty = parseFloat(args.bounty || '0.21');
  const deadline = parseInt(args.deadline || '15', 10);
  const category = args.category || 'simple_action';
  const evidence = args.evidence || 'screenshot';
  const liveMode = args.live === 'true';
  const shouldMonitor = args.monitor === 'true';

  if (!title) {
    console.error('ERROR: --title is required for custom tasks');
    process.exit(1);
  }

  console.log(`\n=== Creating Custom Task ===`);
  console.log(`Title: ${title}`);
  console.log(`Bounty: $${bounty.toFixed(2)} | Deadline: ${deadline}min | Mode: ${liveMode ? 'LIVE' : 'Simulated'}\n`);

  const result = await createTask({
    title,
    instructions,
    category,
    bountyUsd: bounty,
    deadlineMinutes: deadline,
    evidenceSchema: { required: evidence.split(','), optional: [] },
    locationHint: args.location || 'Remote',
    requiredRoles: args.roles ? args.roles.split(',') : [],
    liveEscrow: liveMode,
  });

  printTaskResult(result, liveMode);

  if (shouldMonitor) {
    await monitorTask(result.taskId, result.deadline, result.escrowId, liveMode);
  }
}

async function runFibonacci(args: Record<string, string>): Promise<void> {
  const liveMode = args.live === 'true';
  const deadline = parseInt(args.deadline || '15', 10);
  const count = Math.min(parseInt(args.count || '6', 10), FIBONACCI_BOUNTIES.length);

  console.log(`\n=== Fibonacci Task Series ===`);
  console.log(`Creating ${count} tasks with Fibonacci bounties`);
  console.log(`Mode: ${liveMode ? 'LIVE (Base Mainnet)' : 'Simulated'}`);
  console.log(`Deadline: ${deadline}min each\n`);

  if (liveMode) {
    const totalNeeded = FIBONACCI_BOUNTIES.slice(0, count).reduce((a, b) => a + b, 0);
    console.log(`Total USDC needed: $${totalNeeded.toFixed(2)}`);
    const balance = await checkUSDCBalance();
    console.log(`Wallet USDC balance: $${formatUnits(balance, 6)}`);
    if (balance < parseUnits(totalNeeded.toFixed(6), 6)) {
      console.error(`ERROR: Insufficient funds. Need $${totalNeeded.toFixed(2)} USDC on Base Mainnet.`);
      console.error(`Fund wallet: ${WALLET_ADDRESS}`);
      process.exit(1);
    }
    console.log('');
  }

  const presetNames = Object.keys(PRESETS);
  const results: Array<{ preset: string; bounty: number; taskId: string }> = [];

  for (let i = 0; i < count; i++) {
    const bounty = FIBONACCI_BOUNTIES[i];
    const presetName = presetNames[i % presetNames.length];
    const preset = PRESETS[presetName];

    console.log(`[${i + 1}/${count}] $${bounty.toFixed(2)} — ${presetName}`);

    const result = await createTask({
      title: `${preset.title} [Fib #${i + 1}]`,
      instructions: preset.instructions,
      category: preset.category,
      bountyUsd: bounty,
      deadlineMinutes: deadline,
      evidenceSchema: preset.evidence_schema,
      locationHint: preset.location_hint,
      requiredRoles: preset.required_roles,
      liveEscrow: liveMode,
    });

    results.push({ preset: presetName, bounty, taskId: result.taskId });
    console.log(`  Task: ${result.taskId}`);
    if (liveMode && result.escrowTx) {
      console.log(`  Escrow TX: https://basescan.org/tx/${result.escrowTx}`);
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('  Fibonacci Series Created');
  console.log('='.repeat(60));
  console.log(`\n  Total tasks: ${results.length}`);
  console.log(`  Total bounty: $${results.reduce((s, r) => s + r.bounty, 0).toFixed(2)}`);
  console.log(`  Dashboard: ${DASHBOARD_URL}`);
  console.log('\n  Tasks:');
  for (const r of results) {
    console.log(`    $${r.bounty.toFixed(2)} | ${r.preset.padEnd(16)} | ${r.taskId}`);
  }
  console.log('');
}

async function runCleanup(): Promise<void> {
  console.log('\n=== Cleaning up test tasks ===');
  console.log(`Looking for tasks by agent ${WALLET_ADDRESS}...\n`);

  const tasks = await supabaseRequest(
    `tasks?agent_id=eq.${WALLET_ADDRESS}&status=eq.published&select=id,title,bounty_usd,created_at`,
  );

  if (!tasks || tasks.length === 0) {
    console.log('No active test tasks found.');
    return;
  }

  console.log(`Found ${tasks.length} active tasks:`);
  for (const t of tasks) {
    console.log(`  $${t.bounty_usd} | ${t.title} | ${t.id}`);
  }

  console.log(`\nCancelling all ${tasks.length} tasks...`);
  for (const t of tasks) {
    await supabaseRequest(`tasks?id=eq.${t.id}`, 'PATCH', { status: 'cancelled' });
    console.log(`  Cancelled: ${t.id}`);
  }

  console.log('\nDone. All test tasks cancelled.');
}

// =============================================================================
// Output
// =============================================================================

function printTaskResult(
  result: { taskId: string; escrowTx: string | null; escrowId: string | null; bountyUsd: number; deadline: string },
  liveMode: boolean,
): void {
  console.log('\n' + '='.repeat(60));
  console.log('  Task Created');
  console.log('='.repeat(60));
  console.log(`\n  Task ID:    ${result.taskId}`);
  console.log(`  Bounty:     $${result.bountyUsd.toFixed(2)} USDC`);
  console.log(`  Deadline:   ${result.deadline}`);
  console.log(`  Escrow:     ${liveMode ? 'On-chain (Base Mainnet)' : 'Simulated'}`);
  if (liveMode && result.escrowTx) {
    console.log(`  Escrow TX:  https://basescan.org/tx/${result.escrowTx}`);
  }
  console.log(`  Dashboard:  ${DASHBOARD_URL}`);
  console.log(`\n  Open the dashboard and look for this task in the job list.`);
  console.log(`  Connect your wallet and apply to complete it!\n`);
}

function printUsage(): void {
  console.log(`
Execution Market Task Factory — Create test tasks for the Execution Market

Usage:
  npx tsx task-factory.ts --preset <name> [options]
  npx tsx task-factory.ts --title "..." [options]
  npx tsx task-factory.ts --cleanup

Presets:
  screenshot       Screenshot of X (Twitter) trending
  photo            Photo of local business storefront
  verification     Verify a Google Maps listing
  delivery         Pick up and deliver a package
  translation      Translate English to Spanish
  data_collection  Collect grocery store prices
  fibonacci        Create Fibonacci series (multiple tasks)

Options:
  --bounty <usd>     Bounty amount in USD (default: 0.21)
  --deadline <min>   Deadline in minutes (default: 15)
  --live             Use real on-chain escrow (Base Mainnet, needs USDC)
  --monitor          Monitor task until completion/expiry
  --count <n>        Number of tasks for fibonacci preset (default: 6)
  --category <cat>   Task category (simple_action, physical_presence, etc.)
  --evidence <types> Comma-separated evidence types (screenshot,photo,etc.)
  --location <loc>   Location hint
  --cleanup          Cancel all active test tasks

Examples:
  # Screenshot task, $0.21, 15 min
  npx tsx task-factory.ts --preset screenshot --bounty 0.21 --deadline 15

  # Custom task
  npx tsx task-factory.ts --title "Take a selfie at Times Square" --bounty 0.13 --category physical_presence

  # Fibonacci series with real money
  npx tsx task-factory.ts --preset fibonacci --live --count 5

  # Monitor task until expiry
  npx tsx task-factory.ts --preset screenshot --monitor

  # Clean up all test tasks
  npx tsx task-factory.ts --cleanup
`);
}

// =============================================================================
// Main
// =============================================================================

async function main(): Promise<void> {
  const args = parseArgs();

  if (args.cleanup === 'true') {
    await runCleanup();
    return;
  }

  if (args.preset === 'fibonacci') {
    await runFibonacci(args);
    return;
  }

  if (args.preset) {
    await runPreset(args.preset, args);
    return;
  }

  if (args.title) {
    await runCustom(args);
    return;
  }

  // No arguments — print usage
  printUsage();
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('\nFATAL ERROR:', err.message || err);
    process.exit(1);
  });
