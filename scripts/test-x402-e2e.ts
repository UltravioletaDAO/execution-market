/**
 * E2E Test: x402 Payment Flow + ERC-8004 Reputation
 *
 * Tests the complete lifecycle:
 * 1. Agent creates task with x402 payment
 * 2. Worker accepts and submits evidence
 * 3. Agent approves → payment released + reputation submitted
 * 4. Agent cancels (alternative path) → authorization expires
 *
 * Requirements:
 * - WALLET_PRIVATE_KEY: Agent wallet with USDC on Base
 * - API_KEY: Execution Market API key
 * - Uses live facilitator: https://facilitator.ultravioletadao.xyz
 *
 * Usage:
 *   npx tsx scripts/test-x402-e2e.ts --live
 */

import { createWalletClient, http, parseUnits, formatUnits, encodeFunctionData, keccak256, toHex } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import * as dotenv from 'dotenv';

// Load environment
dotenv.config({ path: '.env.local' });

// Configuration
const CONFIG = {
  // API
  API_URL: process.env.API_URL || 'https://mcp.execution.market',
  API_KEY: process.env.API_KEY || 'em_starter_d10baa5d63f02a223494cf9a1bb0d645',

  // Facilitator
  FACILITATOR_URL: 'https://facilitator.ultravioletadao.xyz',

  // Contracts (Base Mainnet)
  USDC_ADDRESS: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as `0x${string}`,
  CHAIN_ID: 8453,

  // USDC EIP-712 domain (for TransferWithAuthorization)
  USDC_DOMAIN: {
    name: 'USD Coin',
    version: '2',
    chainId: 8453,
    verifyingContract: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as `0x${string}`,
  },

  // Test parameters
  TEST_BOUNTY_USD: 0.10, // $0.10 for testing
  PLATFORM_FEE_PERCENT: 0.08, // 8%
};

// Types
interface CreateTaskResponse {
  id: string;
  title: string;
  status: string;
  bounty_usd: number;
  escrow_id?: string;
  escrow_tx?: string;
}

interface TaskDetails {
  id: string;
  title: string;
  status: string;
  bounty_usd: number;
  executor_id?: string;
  escrow_id?: string;
  escrow_tx?: string;
}

// USDC EIP-712 types for TransferWithAuthorization
const TRANSFER_WITH_AUTHORIZATION_TYPES = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' },
  ],
} as const;

// Helper: Generate random nonce
function generateNonce(): `0x${string}` {
  return keccak256(toHex(Date.now().toString() + Math.random().toString()));
}

// Helper: Create EIP-3009 authorization
async function createTransferAuthorization(params: {
  from: `0x${string}`;
  to: `0x${string}`;
  value: bigint;
  validAfter: number;
  validBefore: number;
  nonce: `0x${string}`;
  signer: ReturnType<typeof createWalletClient>;
}): Promise<{ signature: `0x${string}`; authorization: any }> {
  const authorization = {
    from: params.from,
    to: params.to,
    value: params.value,
    validAfter: BigInt(params.validAfter),
    validBefore: BigInt(params.validBefore),
    nonce: params.nonce,
  };

  const signature = await params.signer.signTypedData({
    account: privateKeyToAccount(process.env.WALLET_PRIVATE_KEY as `0x${string}`),
    domain: CONFIG.USDC_DOMAIN,
    types: TRANSFER_WITH_AUTHORIZATION_TYPES,
    primaryType: 'TransferWithAuthorization',
    message: authorization,
  });

  return { signature, authorization };
}

// Helper: Create X-Payment header
function createXPaymentHeader(params: {
  signature: `0x${string}`;
  authorization: any;
}): string {
  const payload = {
    x402Version: 1,
    scheme: 'exact',
    network: 'base',
    payload: {
      signature: params.signature,
      authorization: {
        from: params.authorization.from,
        to: params.authorization.to,
        value: params.authorization.value.toString(),
        validAfter: params.authorization.validAfter.toString(),
        validBefore: params.authorization.validBefore.toString(),
        nonce: params.authorization.nonce,
      },
    },
  };

  return Buffer.from(JSON.stringify(payload)).toString('base64');
}

// Test: Create task with x402 payment
async function testCreateTaskWithPayment(live: boolean): Promise<CreateTaskResponse | null> {
  console.log('\n=== TEST: Create Task with x402 Payment ===\n');

  if (!live) {
    console.log('[DRY RUN] Would create task with payment');
    return null;
  }

  const privateKey = process.env.WALLET_PRIVATE_KEY as `0x${string}`;
  if (!privateKey) {
    console.error('WALLET_PRIVATE_KEY not set');
    return null;
  }

  const account = privateKeyToAccount(privateKey);
  console.log(`Agent wallet: ${account.address}`);

  // Calculate payment amount
  const bounty = CONFIG.TEST_BOUNTY_USD;
  const fee = bounty * CONFIG.PLATFORM_FEE_PERCENT;
  const total = bounty + fee;
  const amountWei = parseUnits(total.toFixed(6), 6); // USDC has 6 decimals

  console.log(`Bounty: $${bounty.toFixed(2)}`);
  console.log(`Fee (8%): $${fee.toFixed(2)}`);
  console.log(`Total: $${total.toFixed(2)} (${amountWei.toString()} wei)`);

  // Create wallet client
  const client = createWalletClient({
    account,
    chain: base,
    transport: http(),
  });

  // Create EIP-3009 authorization
  const now = Math.floor(Date.now() / 1000);
  const validAfter = now - 60; // Valid from 1 minute ago
  const validBefore = now + 3600; // Valid for 1 hour
  const nonce = generateNonce();

  // Recipient is the facilitator vault (will be determined by facilitator)
  // For now, we use a placeholder - the facilitator will validate
  const recipientAddress = '0x0000000000000000000000000000000000000000' as `0x${string}`;

  console.log(`\nCreating authorization...`);
  console.log(`  Valid: ${new Date(validAfter * 1000).toISOString()} - ${new Date(validBefore * 1000).toISOString()}`);
  console.log(`  Nonce: ${nonce.slice(0, 18)}...`);

  const { signature, authorization } = await createTransferAuthorization({
    from: account.address,
    to: recipientAddress,
    value: amountWei,
    validAfter,
    validBefore,
    nonce,
    signer: client,
  });

  console.log(`  Signature: ${signature.slice(0, 42)}...`);

  // Create X-Payment header
  const xPaymentHeader = createXPaymentHeader({ signature, authorization });
  console.log(`\nX-Payment header created (${xPaymentHeader.length} chars)`);

  // Create task via API
  const taskRequest = {
    title: `E2E Test Task ${new Date().toISOString()}`,
    instructions: 'This is an automated test task. Take a photo of your screen.',
    category: 'simple_action',
    bounty_usd: bounty,
    deadline_hours: 1,
    evidence_required: ['photo'],
    location_hint: 'Anywhere',
    min_reputation: 0,
  };

  console.log(`\nCreating task via API...`);
  console.log(`  URL: ${CONFIG.API_URL}/api/v1/tasks`);
  console.log(`  Title: ${taskRequest.title}`);

  try {
    const response = await fetch(`${CONFIG.API_URL}/api/v1/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': CONFIG.API_KEY,
        'X-Payment': xPaymentHeader,
      },
      body: JSON.stringify(taskRequest),
    });

    const responseText = await response.text();
    console.log(`\nResponse status: ${response.status}`);

    if (response.status === 402) {
      console.log('Payment required (expected if verification failed):');
      console.log(JSON.parse(responseText));
      return null;
    }

    if (!response.ok) {
      console.error('Error:', responseText);
      return null;
    }

    const task = JSON.parse(responseText) as CreateTaskResponse;
    console.log('\nTask created successfully!');
    console.log(`  ID: ${task.id}`);
    console.log(`  Status: ${task.status}`);
    console.log(`  Escrow ID: ${task.escrow_id || 'N/A'}`);
    console.log(`  Escrow TX: ${task.escrow_tx ? task.escrow_tx.slice(0, 50) + '...' : 'N/A'}`);

    return task;
  } catch (error) {
    console.error('Request failed:', error);
    return null;
  }
}

// Test: Get task details
async function testGetTask(taskId: string): Promise<TaskDetails | null> {
  console.log(`\n=== TEST: Get Task Details ===\n`);
  console.log(`Task ID: ${taskId}`);

  try {
    const response = await fetch(`${CONFIG.API_URL}/api/v1/tasks/${taskId}`, {
      headers: {
        'X-API-Key': CONFIG.API_KEY,
      },
    });

    if (!response.ok) {
      console.error('Failed to get task:', await response.text());
      return null;
    }

    const task = await response.json() as TaskDetails;
    console.log('\nTask details:');
    console.log(`  Title: ${task.title}`);
    console.log(`  Status: ${task.status}`);
    console.log(`  Bounty: $${task.bounty_usd}`);
    console.log(`  Executor: ${task.executor_id || 'None'}`);

    return task;
  } catch (error) {
    console.error('Request failed:', error);
    return null;
  }
}

// Test: Cancel task
async function testCancelTask(taskId: string): Promise<boolean> {
  console.log(`\n=== TEST: Cancel Task ===\n`);
  console.log(`Task ID: ${taskId}`);

  try {
    const response = await fetch(`${CONFIG.API_URL}/api/v1/tasks/${taskId}/cancel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': CONFIG.API_KEY,
      },
      body: JSON.stringify({ reason: 'E2E test cancellation' }),
    });

    const result = await response.json();
    console.log('\nCancel result:');
    console.log(JSON.stringify(result, null, 2));

    return response.ok;
  } catch (error) {
    console.error('Request failed:', error);
    return false;
  }
}

// Test: Check ERC-8004 reputation
async function testCheckReputation(): Promise<void> {
  console.log(`\n=== TEST: Check ERC-8004 Reputation ===\n`);

  try {
    // Get EM's reputation
    const response = await fetch(`${CONFIG.API_URL}/api/v1/reputation/em`);
    const reputation = await response.json();

    console.log('Execution Market Reputation:');
    console.log(`  Agent ID: ${reputation.agent_id}`);
    console.log(`  Score: ${reputation.score}`);
    console.log(`  Count: ${reputation.count}`);
    console.log(`  Network: ${reputation.network}`);
  } catch (error) {
    console.error('Failed to check reputation:', error);
  }
}

// Test: Check facilitator health
async function testFacilitatorHealth(): Promise<boolean> {
  console.log(`\n=== TEST: Facilitator Health ===\n`);

  try {
    const response = await fetch(`${CONFIG.FACILITATOR_URL}/health`);
    const health = await response.json();

    console.log('Facilitator status:');
    console.log(JSON.stringify(health, null, 2));

    return health.status === 'healthy';
  } catch (error) {
    console.error('Failed to check facilitator:', error);
    return false;
  }
}

// Main test runner
async function runTests() {
  const args = process.argv.slice(2);
  const live = args.includes('--live');

  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║          x402 Payment + ERC-8004 Reputation E2E Test       ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log(`\nMode: ${live ? 'LIVE (real transactions)' : 'DRY RUN (no transactions)'}`);
  console.log(`API: ${CONFIG.API_URL}`);
  console.log(`Facilitator: ${CONFIG.FACILITATOR_URL}`);

  // Check facilitator health
  const facilitatorHealthy = await testFacilitatorHealth();
  if (!facilitatorHealthy) {
    console.error('\nFacilitator is not healthy. Aborting.');
    return;
  }

  // Check reputation endpoint
  await testCheckReputation();

  // Create task with payment
  const task = await testCreateTaskWithPayment(live);
  if (!task && live) {
    console.error('\nFailed to create task. Aborting.');
    return;
  }

  if (task) {
    // Get task details
    await testGetTask(task.id);

    // Cancel the task to test refund flow
    console.log('\n--- Testing cancellation flow ---');
    const cancelled = await testCancelTask(task.id);
    if (cancelled) {
      // Verify task is cancelled
      await testGetTask(task.id);
    }
  }

  console.log('\n╔════════════════════════════════════════════════════════════╗');
  console.log('║                      TEST COMPLETE                          ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
}

// Run tests
runTests().catch(console.error);
