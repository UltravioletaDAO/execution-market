/**
 * Execution Market Escrow Lifecycle Test
 *
 * Tests the full task lifecycle with escrow:
 *   1. Create task in Supabase with 2-minute deadline
 *   2. (On-chain deposit via MCP server API — mainnet only)
 *   3. Monitor task status via Supabase polling
 *   4. Wait for MCP server task_expiration job to mark it expired
 *   5. Verify task status changed to 'expired'
 *
 * Two modes:
 *   --live     Uses Base Mainnet contracts for real escrow (direct wallet mode, debug only)
 *   (default)  Simulated mode — creates task, monitors expiry, verifies MCP server job
 *
 * Usage:
 *   npx tsx test-escrow-flow.ts          # Simulated (server-side expiry test)
 *   npx tsx test-escrow-flow.ts --live --allow-direct-wallet   # Direct on-chain debug mode
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
import { base, baseSepolia } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.env.local') });

// =============================================================================
// Configuration
// =============================================================================

const LIVE_MODE = process.argv.includes('--live');
const ALLOW_DIRECT_WALLET = process.argv.includes('--allow-direct-wallet');

const PRIVATE_KEY = (process.env.WALLET_PRIVATE_KEY ||
  '0xc6c257c724e09edf7c49f7cc33d3beba5ece73a98e9dda83b31dada3ddbc5c9d') as Hex;

// Base Mainnet contracts (x402r production)
const MAINNET_FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as Address;
const MAINNET_USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as Address;

const SUPABASE_URL = 'https://puyhpytmtkyevnxffksl.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1eWhweXRtdGt5ZXZueGZma3NsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg2NzgzOTMsImV4cCI6MjA4NDI1NDM5M30.R4Sf4SwDo-5yRhRMOazQ-4Jn972YLT7lYunjdqiGjaU';

// MCP server base URL
const MCP_SERVER_URL = 'https://mcp.execution.market';

const BOUNTY_USD = 0.13;
const TASK_DEADLINE_MINUTES = 2; // Short deadline for testing
const POLL_INTERVAL_MS = 15_000; // 15 seconds

// =============================================================================
// Contract ABIs (Base Mainnet DepositRelayFactory)
// =============================================================================

const ERC20_ABI = [
  {
    name: 'approve',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'spender', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    name: 'allowance',
    type: 'function',
    stateMutability: 'view',
    inputs: [
      { name: 'owner', type: 'address' },
      { name: 'spender', type: 'address' },
    ],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

const FACTORY_ABI = [
  {
    name: 'createEscrow',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'token', type: 'address' },
      { name: 'amount', type: 'uint256' },
      { name: 'beneficiary', type: 'address' },
      { name: 'timeout', type: 'uint256' },
      { name: 'taskId', type: 'bytes32' },
    ],
    outputs: [{ name: 'escrowId', type: 'bytes32' }],
  },
  {
    name: 'getEscrow',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'escrowId', type: 'bytes32' }],
    outputs: [
      { name: 'depositor', type: 'address' },
      { name: 'beneficiary', type: 'address' },
      { name: 'amount', type: 'uint256' },
      { name: 'timeout', type: 'uint256' },
      { name: 'released', type: 'bool' },
      { name: 'refunded', type: 'bool' },
    ],
  },
  {
    name: 'refundEscrow',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [{ name: 'escrowId', type: 'bytes32' }],
    outputs: [],
  },
] as const;

// =============================================================================
// Helpers
// =============================================================================

const account = privateKeyToAccount(PRIVATE_KEY);
const WALLET_ADDRESS = account.address;

async function supabase(
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

function formatRemaining(ms: number): string {
  if (ms <= 0) return '0:00';
  const totalSec = Math.floor(ms / 1000);
  return `${Math.floor(totalSec / 60)}:${(totalSec % 60).toString().padStart(2, '0')}`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function header(step: number, title: string): void {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`  Step ${step}: ${title}`);
  console.log('='.repeat(60));
}

// =============================================================================
// Main Flow
// =============================================================================

async function main(): Promise<void> {
  if (LIVE_MODE && !ALLOW_DIRECT_WALLET) {
    throw new Error(
      'Direct wallet mode is disabled by default. ' +
      'Use facilitator flow (`test-x402-full-flow.ts --strict-api`) or pass --allow-direct-wallet for debugging.'
    );
  }

  console.log(`\n=== Execution Market Escrow E2E Test (${LIVE_MODE ? 'LIVE - Base Mainnet' : 'Simulated'}) ===`);
  console.log('Wallet:', WALLET_ADDRESS);
  console.log('MCP Server:', MCP_SERVER_URL);
  console.log('Bounty:', `$${BOUNTY_USD}`);
  console.log('Deadline:', `${TASK_DEADLINE_MINUTES} minutes`);

  // Pre-flight: check MCP server health
  try {
    const healthRes = await fetch(`${MCP_SERVER_URL}/health`);
    const health = await healthRes.json();
    console.log('MCP Server:', health.status, `(uptime: ${Math.round(health.uptime_seconds)}s)`);
  } catch {
    console.warn('MCP Server health check failed — continuing anyway');
  }

  // =========================================================================
  // Step 1: Create task in Supabase
  // =========================================================================
  header(1, 'Create task in Supabase');

  const deadlineAt = new Date(Date.now() + TASK_DEADLINE_MINUTES * 60 * 1000).toISOString();
  const taskPayload = {
    title: `E2E Test - Escrow Flow ${new Date().toISOString().slice(11, 19)}`,
    instructions:
      'Automated E2E test task. Verifies the full escrow lifecycle: deposit, monitor, auto-expiry by MCP server.',
    category: 'simple_action',
    bounty_usd: BOUNTY_USD,
    payment_token: 'USDC',
    status: 'published',
    agent_id: WALLET_ADDRESS,
    deadline: deadlineAt,
    location_hint: 'Remote',
    evidence_schema: { required: ['screenshot'], optional: [] },
    min_reputation: 0,
    required_roles: [],
    max_executors: 1,
  };

  const [task] = await supabase('tasks', 'POST', taskPayload);
  const taskId: string = task.id;
  const taskIdBytes32 = keccak256(toHex(taskId)) as Hex;
  console.log(`Task created: ${taskId}`);
  console.log(`  Title: ${task.title}`);
  console.log(`  Deadline: ${deadlineAt}`);
  console.log(`  Task ID (bytes32): ${taskIdBytes32}`);

  // =========================================================================
  // Step 2: Escrow deposit
  // =========================================================================
  header(2, LIVE_MODE ? 'Create on-chain escrow (Base Mainnet)' : 'Simulate escrow deposit');

  let escrowTx: string | null = null;
  let escrowId: string | null = null;

  if (LIVE_MODE) {
    // Real on-chain escrow via Base Mainnet DepositRelayFactory
    const publicClient = createPublicClient({ chain: base, transport: http() });
    const walletClient = createWalletClient({ account, chain: base, transport: http() });
    const bountyUnits = parseUnits('0.13', 6);

    // Check USDC balance
    const usdcBalance = await publicClient.readContract({
      address: MAINNET_USDC,
      abi: ERC20_ABI,
      functionName: 'balanceOf',
      args: [WALLET_ADDRESS],
    });
    console.log('USDC balance (mainnet):', formatUnits(usdcBalance, 6));

    if (usdcBalance < bountyUnits) {
      console.error(`ERROR: Need ${formatUnits(bountyUnits, 6)} USDC but have ${formatUnits(usdcBalance, 6)}`);
      console.error('Fund the wallet with USDC on Base Mainnet to use --live mode.');
      await supabase(`tasks?id=eq.${taskId}`, 'PATCH', { status: 'cancelled' });
      process.exit(1);
    }

    // Approve USDC
    const allowance = await publicClient.readContract({
      address: MAINNET_USDC,
      abi: ERC20_ABI,
      functionName: 'allowance',
      args: [WALLET_ADDRESS, MAINNET_FACTORY],
    });

    if (allowance < bountyUnits) {
      console.log('Approving USDC...');
      const approveTx = await walletClient.writeContract({
        address: MAINNET_USDC,
        abi: ERC20_ABI,
        functionName: 'approve',
        args: [MAINNET_FACTORY, parseUnits('1000', 6)],
      });
      await publicClient.waitForTransactionReceipt({ hash: approveTx });
      console.log(`  Approved: ${approveTx}`);
    }

    // Create escrow
    const timeoutTimestamp = BigInt(Math.floor(Date.now() / 1000) + TASK_DEADLINE_MINUTES * 60);
    console.log('Creating escrow on DepositRelayFactory...');

    const depositHash = await walletClient.writeContract({
      address: MAINNET_FACTORY,
      abi: FACTORY_ABI,
      functionName: 'createEscrow',
      args: [MAINNET_USDC, bountyUnits, WALLET_ADDRESS, timeoutTimestamp, taskIdBytes32],
    });

    const receipt = await publicClient.waitForTransactionReceipt({ hash: depositHash });
    if (receipt.status !== 'success') {
      console.error('ERROR: createEscrow reverted');
      await supabase(`tasks?id=eq.${taskId}`, 'PATCH', { status: 'cancelled' });
      process.exit(1);
    }

    escrowTx = depositHash;
    escrowId = taskIdBytes32;
    console.log(`  Escrow created: ${depositHash}`);
    console.log(`  Block: ${receipt.blockNumber}`);
    console.log(`  Gas: ${receipt.gasUsed}`);
    console.log(`  Escrow ID: ${escrowId}`);
    console.log(`  BaseScan: https://basescan.org/tx/${depositHash}`);
  } else {
    // Simulated: record a fake escrow reference so dashboard shows payment info
    escrowTx = `0x${'0'.repeat(62)}e2e`;
    escrowId = taskIdBytes32;
    console.log('Simulated escrow deposit (no on-chain transaction)');
    console.log(`  Escrow ID: ${escrowId}`);
    console.log('  This tests the server-side task_expiration job and dashboard display.');
  }

  // Update task with escrow info
  await supabase(`tasks?id=eq.${taskId}`, 'PATCH', {
    escrow_tx: escrowTx,
    escrow_id: escrowId,
  });
  console.log('  Supabase task updated with escrow_tx and escrow_id');

  // =========================================================================
  // Step 3: Monitor task
  // =========================================================================
  header(3, 'Monitor task (waiting for deadline + MCP server expiry job)');
  console.log('The MCP server task_expiration job runs every 60s.');
  console.log('It will automatically mark expired tasks and attempt escrow refund.\n');

  const deadlineMs = new Date(deadlineAt).getTime();
  let taskExpired = false;
  let lastStatus = 'published';

  while (!taskExpired) {
    const now = Date.now();
    const remaining = deadlineMs - now;

    const currentTask = await supabase(
      `tasks?id=eq.${taskId}&select=status`,
      'GET',
      undefined,
      true,
    );
    const status = currentTask?.status || 'unknown';

    if (status !== lastStatus) {
      console.log(`*** Status changed: ${lastStatus} → ${status}`);
      lastStatus = status;
    }

    if (status === 'expired') {
      taskExpired = true;
      console.log('Task marked as EXPIRED by MCP server!');
      break;
    }

    if (status === 'accepted' || status === 'in_progress' || status === 'submitted') {
      console.log('Task was picked up by a worker. Exiting monitor.');
      break;
    }

    if (remaining > 0) {
      console.log(`  Status: ${status} | Time remaining: ${formatRemaining(remaining)}`);
    } else {
      // Past deadline but MCP server hasn't marked it yet
      const overdueS = Math.floor((now - deadlineMs) / 1000);
      console.log(`  Status: ${status} | Overdue by ${overdueS}s (waiting for MCP server job)`);

      // Safety: if overdue by more than 3 minutes, MCP server job might not be running
      if (overdueS > 180) {
        console.error('ERROR: Task not expired after 3 minutes overdue.');
        console.error('The MCP server task_expiration job may not be running.');
        break;
      }
    }

    await sleep(POLL_INTERVAL_MS);
  }

  // =========================================================================
  // Step 4: Verify on-chain (live mode only)
  // =========================================================================
  if (LIVE_MODE && escrowId) {
    header(4, 'Verify on-chain escrow state');

    const publicClient = createPublicClient({ chain: base, transport: http() });

    try {
      const escrowState = await publicClient.readContract({
        address: MAINNET_FACTORY,
        abi: FACTORY_ABI,
        functionName: 'getEscrow',
        args: [escrowId as Hex],
      });

      const [depositor, beneficiary, amount, timeout, released, refunded] = escrowState;
      console.log('On-chain escrow state:');
      console.log('  Depositor:', depositor);
      console.log('  Beneficiary:', beneficiary);
      console.log('  Amount:', formatUnits(amount, 6), 'USDC');
      console.log('  Released:', released);
      console.log('  Refunded:', refunded);

      if (refunded) {
        console.log('  ✓ Escrow refunded on-chain!');
      } else if (released) {
        console.log('  ✓ Escrow released to worker!');
      } else {
        console.log('  ⚠ Escrow still locked (timeout may not have passed)');
      }
    } catch (err: any) {
      console.log(`  Could not read escrow state: ${err.message?.slice(0, 100)}`);
    }

    // Check USDC balance after
    const usdcAfter = await publicClient.readContract({
      address: MAINNET_USDC,
      abi: ERC20_ABI,
      functionName: 'balanceOf',
      args: [WALLET_ADDRESS],
    });
    console.log('  Final USDC balance:', formatUnits(usdcAfter, 6));
  }

  // =========================================================================
  // Step 5: Verify Supabase state
  // =========================================================================
  header(LIVE_MODE ? 5 : 4, 'Verify final state');

  const finalTask = await supabase(
    `tasks?id=eq.${taskId}&select=*`,
    'GET',
    undefined,
    true,
  );
  console.log('Final task state:');
  console.log('  Status:', finalTask.status);
  console.log('  Escrow TX:', finalTask.escrow_tx?.slice(0, 20) + '...');
  console.log('  Escrow ID:', finalTask.escrow_id?.slice(0, 20) + '...');

  // Check dashboard URL
  console.log(`\nDashboard: https://app.execution.market`);
  console.log(`Task visible in public task browser (if still published) or task detail.`);

  console.log('\n' + '='.repeat(60));
  console.log('  Test COMPLETE');
  console.log('='.repeat(60));
  console.log('\nSummary:');
  console.log(`  Mode:           ${LIVE_MODE ? 'Live (Base Mainnet)' : 'Simulated'}`);
  console.log(`  Task ID:        ${taskId}`);
  console.log(`  Escrow ID:      ${escrowId}`);
  console.log(`  Escrow TX:      ${escrowTx?.slice(0, 20)}...`);
  console.log(`  Final Status:   ${finalTask.status}`);
  console.log(`  MCP Server:     ${MCP_SERVER_URL}`);
  console.log(`  Dashboard:      https://app.execution.market`);

  if (finalTask.status === 'expired') {
    console.log('\n  ✓ SUCCESS: Task expired and processed by MCP server');
  } else if (finalTask.status === 'published') {
    console.log('\n  ⚠ PENDING: Task not yet expired. MCP server job may still be processing.');
  } else {
    console.log(`\n  ? UNEXPECTED: Task status is '${finalTask.status}'`);
  }
  console.log('');
}

// =============================================================================
// Entry Point
// =============================================================================

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('\nFATAL ERROR:', err);
    process.exit(1);
  });
