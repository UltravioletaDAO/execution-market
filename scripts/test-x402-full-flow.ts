/**
 * Execution Market — Full x402 Payment Flow Test (Base Mainnet)
 *
 * Tests the complete payment lifecycle with real USDC:
 *   1. Sign EIP-3009 TransferWithAuthorization for USDC on Base
 *   2. Construct x402 payment header (base64 JSON)
 *   3. POST task to MCP API with X-Payment header
 *   4. MCP server verifies via Ultravioleta Facilitator
 *   5. Worker accepts + submits evidence on dashboard
 *   6. Agent approves → facilitator settles → USDC to worker (gasless)
 *
 * Fibonacci bounties: $0.01, $0.02, $0.03, $0.05, $0.08
 *
 * Usage:
 *   npx tsx test-x402-full-flow.ts                  # Full x402 via MCP API
 *   npx tsx test-x402-full-flow.ts --direct         # Fallback: direct Supabase insert
 *   npx tsx test-x402-full-flow.ts --count 3        # Only first N Fibonacci tasks
 *   npx tsx test-x402-full-flow.ts --monitor        # Monitor tasks after creation
 *   npx tsx test-x402-full-flow.ts --auto-approve   # Auto-approve submissions
 *   npx tsx test-x402-full-flow.ts --deadline 10    # Deadline in minutes (default: 15)
 */

import {
  createPublicClient,
  http,
  formatUnits,
  parseUnits,
  encodePacked,
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

const SUPABASE_URL = 'https://YOUR_PROJECT_REF.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1eWhweXRtdGt5ZXZueGZma3NsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg2NzgzOTMsImV4cCI6MjA4NDI1NDM5M30.R4Sf4SwDo-5yRhRMOazQ-4Jn972YLT7lYunjdqiGjaU';

const MCP_SERVER_URL = 'https://mcp.execution.market';
const DASHBOARD_URL = 'https://execution.market';
const FACILITATOR_URL = 'https://facilitator.ultravioletadao.xyz';

// Base Mainnet contracts
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as Address;
const EM_TREASURY = 'YOUR_TREASURY_WALLET' as Address;

// Fibonacci bounties for test tasks
const FIBONACCI_BOUNTIES = [0.01, 0.02, 0.03, 0.05, 0.08];

// Platform fee (8%)
const PLATFORM_FEE_PERCENT = 0.08;

// =============================================================================
// Contract ABIs
// =============================================================================

const ERC20_ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    name: 'nonces',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [{ name: 'owner', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    name: 'name',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [],
    outputs: [{ name: '', type: 'string' }],
  },
  {
    name: 'version',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [],
    outputs: [{ name: '', type: 'string' }],
  },
] as const;

// =============================================================================
// CLI Args
// =============================================================================

function parseArgs(): Record<string, string> {
  const args: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      if (['direct', 'monitor', 'auto-approve'].includes(key)) {
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

const CLI_ARGS = parseArgs();
const DIRECT_MODE = CLI_ARGS['direct'] === 'true';
const MONITOR_MODE = CLI_ARGS['monitor'] === 'true';
const AUTO_APPROVE = CLI_ARGS['auto-approve'] === 'true';
const TASK_COUNT = Math.min(parseInt(CLI_ARGS['count'] || '5', 10), FIBONACCI_BOUNTIES.length);
const DEADLINE_MINUTES = parseInt(CLI_ARGS['deadline'] || '15', 10);

// =============================================================================
// Helpers
// =============================================================================

const publicClient = createPublicClient({ chain: base, transport: http() });

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function header(step: number, title: string): void {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`  Step ${step}: ${title}`);
  console.log('='.repeat(60));
}

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

// =============================================================================
// EIP-3009 TransferWithAuthorization Signing
// =============================================================================

// EIP-712 domain for USDC on Base Mainnet
const USDC_EIP712_DOMAIN = {
  name: 'USD Coin',
  version: '2',
  chainId: 8453n,
  verifyingContract: USDC_ADDRESS,
} as const;

// EIP-3009 TransferWithAuthorization types
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

interface EIP3009Authorization {
  from: Address;
  to: Address;
  value: string;
  validAfter: string;
  validBefore: string;
  nonce: Hex;
}

/**
 * Sign an EIP-3009 TransferWithAuthorization for USDC.
 * Returns the authorization params and the EIP-712 signature.
 */
async function signTransferWithAuthorization(
  to: Address,
  amountUsd: number,
  validForSeconds: number = 3600,
): Promise<{ authorization: EIP3009Authorization; signature: Hex }> {
  const value = parseUnits(amountUsd.toFixed(6), 6);
  const now = Math.floor(Date.now() / 1000);

  // Generate random nonce (bytes32)
  const randomBytes = new Uint8Array(32);
  crypto.getRandomValues(randomBytes);
  const nonce = ('0x' + Array.from(randomBytes).map(b => b.toString(16).padStart(2, '0')).join('')) as Hex;

  const authorization: EIP3009Authorization = {
    from: WALLET_ADDRESS,
    to,
    value: value.toString(),
    validAfter: '0',
    validBefore: (now + validForSeconds).toString(),
    nonce,
  };

  // Sign with EIP-712
  const signature = await account.signTypedData({
    domain: USDC_EIP712_DOMAIN,
    types: TRANSFER_WITH_AUTHORIZATION_TYPES,
    primaryType: 'TransferWithAuthorization',
    message: {
      from: authorization.from,
      to: authorization.to,
      value: BigInt(authorization.value),
      validAfter: BigInt(authorization.validAfter),
      validBefore: BigInt(authorization.validBefore),
      nonce: authorization.nonce,
    },
  });

  return { authorization, signature };
}

/**
 * Construct the x402 X-Payment header value.
 * Format: base64-encoded JSON per x402 spec v1.
 */
function buildX402PaymentHeader(
  authorization: EIP3009Authorization,
  signature: Hex,
): string {
  const payload = {
    x402Version: 1,
    scheme: 'exact',
    network: 'base',
    payload: {
      signature,
      authorization: {
        from: authorization.from,
        to: authorization.to,
        value: authorization.value,
        validAfter: authorization.validAfter,
        validBefore: authorization.validBefore,
        nonce: authorization.nonce,
      },
    },
  };

  const jsonStr = JSON.stringify(payload);
  // Base64 encode
  return Buffer.from(jsonStr).toString('base64');
}

// =============================================================================
// MCP API Client
// =============================================================================

interface TaskDefinition {
  title: string;
  instructions: string;
  category: string;
  bountyUsd: number;
  deadlineMinutes: number;
  evidenceRequired: string[];
}

const TASK_TEMPLATES: TaskDefinition[] = [
  {
    title: 'Take a screenshot of X (Twitter) trending topics',
    instructions:
      'Open x.com (Twitter) on your browser. Navigate to the Explore/Trending page. ' +
      'Take a full-screen screenshot showing the current trending topics. ' +
      'The screenshot must include the date/time visible on screen and at least 5 trending topics.',
    category: 'simple_action',
    bountyUsd: 0,
    deadlineMinutes: DEADLINE_MINUTES,
    evidenceRequired: ['screenshot'],
  },
  {
    title: 'Take a photo of a local business storefront',
    instructions:
      'Go to any local business in your area. Take a clear photo of the storefront ' +
      'showing the business name, address, and opening hours if visible. ' +
      'The photo must be taken during daylight hours and be clearly readable.',
    category: 'physical_presence',
    bountyUsd: 0,
    deadlineMinutes: DEADLINE_MINUTES,
    evidenceRequired: ['photo'],
  },
  {
    title: 'Verify a Google Maps listing is accurate',
    instructions:
      'Visit the business at the provided address. Confirm: (1) The business exists, ' +
      '(2) The name matches the listing, (3) Operating hours are correct. ' +
      'Take a photo of the storefront as proof. Report any discrepancies.',
    category: 'physical_presence',
    bountyUsd: 0,
    deadlineMinutes: DEADLINE_MINUTES,
    evidenceRequired: ['photo', 'text'],
  },
  {
    title: 'Translate a short paragraph from English to Spanish',
    instructions:
      'Translate the following text into natural, fluent Spanish: ' +
      '"The execution market connects AI agents with human workers for tasks that require ' +
      'physical presence, local knowledge, or human judgment. Workers are paid instantly via ' +
      'blockchain escrow upon task completion and verification."',
    category: 'human_authority',
    bountyUsd: 0,
    deadlineMinutes: DEADLINE_MINUTES,
    evidenceRequired: ['text'],
  },
  {
    title: 'Collect prices of 5 items at a local grocery store',
    instructions:
      'Visit a local grocery store and record the prices of: milk (1L), bread (loaf), ' +
      'eggs (dozen), rice (1kg), and bananas (1kg). Take a photo of each price tag. ' +
      'Submit all 5 photos with the store name and date.',
    category: 'knowledge_access',
    bountyUsd: 0,
    deadlineMinutes: DEADLINE_MINUTES,
    evidenceRequired: ['photo', 'text'],
  },
];

/**
 * Try to create a task via the MCP REST API with x402 payment header.
 * Returns the task data on success, or null if the API rejects us.
 */
async function createTaskViaMCP(
  template: TaskDefinition,
  bountyUsd: number,
  paymentHeader: string,
  apiKey: string,
): Promise<any | null> {
  const deadlineHours = Math.max(1, Math.ceil(template.deadlineMinutes / 60));

  const body = {
    title: template.title,
    instructions: template.instructions,
    category: template.category,
    bounty_usd: bountyUsd,
    deadline_hours: deadlineHours,
    evidence_required: template.evidenceRequired,
    location_hint: 'Remote',
    min_reputation: 0,
    payment_token: 'USDC',
  };

  const res = await fetch(`${MCP_SERVER_URL}/api/v1/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
      'X-Payment': paymentHeader,
    },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    return await res.json();
  }

  const text = await res.text();
  console.log(`  MCP API returned ${res.status}: ${text.slice(0, 200)}`);
  return null;
}

/**
 * Create a task directly in Supabase (fallback mode).
 */
async function createTaskDirect(
  template: TaskDefinition,
  bountyUsd: number,
  fibIndex: number,
): Promise<any> {
  const deadline = new Date(Date.now() + template.deadlineMinutes * 60 * 1000).toISOString();

  const payload = {
    title: `${template.title} [Fib #${fibIndex + 1}]`,
    instructions: template.instructions,
    category: template.category,
    bounty_usd: bountyUsd,
    payment_token: 'USDC',
    status: 'published',
    agent_id: WALLET_ADDRESS,
    deadline,
    location_hint: 'Remote',
    evidence_schema: {
      required: template.evidenceRequired,
      optional: [],
    },
    min_reputation: 0,
    required_roles: [],
    max_executors: 1,
  };

  const [task] = await supabaseRequest('tasks', 'POST', payload);
  return task;
}

/**
 * Get API key for MCP server authentication.
 * Uses EM_API_KEY env var, or falls back to the registered test key.
 */
function getApiKey(): string {
  const envKey = process.env.EM_API_KEY;
  if (envKey) {
    console.log(`  Using API key from EM_API_KEY env: ${envKey.slice(0, 25)}...`);
    return envKey;
  }

  // Registered test key for wallet YOUR_DEV_WALLET
  const testKey = 'em_starter_d10baa5d63f02a223494cf9a1bb0d645';
  console.log(`  Using registered test API key: ${testKey.slice(0, 25)}...`);
  return testKey;
}

// =============================================================================
// Facilitator Direct Verify (for diagnostics)
// =============================================================================

async function verifyWithFacilitator(
  paymentHeader: string,
  amountUsd: number,
): Promise<any> {
  const paymentPayload = JSON.parse(Buffer.from(paymentHeader, 'base64').toString());

  // x402 facilitator verify format per Coinbase spec:
  // https://docs.cdp.coinbase.com/api-reference/v2/rest-api/x402-facilitator/verify-a-payment
  const verifyBody = {
    x402Version: 1,
    paymentPayload,
    paymentRequirements: {
      scheme: 'exact',
      network: 'base',
      maxAmountRequired: parseUnits(amountUsd.toFixed(6), 6).toString(),
      resource: `https://mcp.execution.market/api/v1/tasks`,
      description: 'Execution Market task creation',
      mimeType: 'application/json',
      payTo: EM_TREASURY,
      maxTimeoutSeconds: 3600,
      asset: USDC_ADDRESS,
      extra: {},
    },
  };

  try {
    const res = await fetch(`${FACILITATOR_URL}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(verifyBody),
    });
    return await res.json();
  } catch (err: any) {
    return { error: err.message };
  }
}

// =============================================================================
// Monitor & Approve
// =============================================================================

interface CreatedTask {
  id: string;
  bountyUsd: number;
  fibIndex: number;
  deadline: string;
  paymentHeader?: string;
  status: string;
}

async function monitorTasks(
  tasks: CreatedTask[],
  apiKey: string,
): Promise<void> {
  console.log(`\nMonitoring ${tasks.length} tasks...`);
  console.log('Press Ctrl+C to stop.\n');

  const POLL_MS = 15_000;
  const activeTasks = new Map(tasks.map((t) => [t.id, { ...t }]));

  while (activeTasks.size > 0) {
    for (const [taskId, task] of activeTasks) {
      try {
        const current = await supabaseRequest(
          `tasks?id=eq.${taskId}&select=status,executor_id`,
          'GET',
          undefined,
          true,
        );

        const newStatus = current?.status || 'unknown';

        if (newStatus !== task.status) {
          console.log(`  [Fib #${task.fibIndex + 1} $${task.bountyUsd.toFixed(2)}] ${task.status} -> ${newStatus}`);
          task.status = newStatus;
        }

        // Check for submissions if task is submitted/verifying
        if (['submitted', 'verifying'].includes(newStatus) && AUTO_APPROVE) {
          await autoApproveSubmissions(taskId, apiKey);
        }

        // Remove completed/expired/cancelled tasks from monitoring
        if (['completed', 'expired', 'cancelled'].includes(newStatus)) {
          activeTasks.delete(taskId);
          console.log(`  [Fib #${task.fibIndex + 1}] Terminal state: ${newStatus}`);
        }
      } catch (err: any) {
        console.log(`  Error polling task ${taskId.slice(0, 8)}: ${err.message?.slice(0, 60)}`);
      }
    }

    if (activeTasks.size > 0) {
      const now = Date.now();
      for (const [, task] of activeTasks) {
        const remaining = new Date(task.deadline).getTime() - now;
        const min = Math.floor(Math.abs(remaining) / 60000);
        const sec = Math.floor((Math.abs(remaining) % 60000) / 1000);
        const sign = remaining < 0 ? '-' : '';
        process.stdout.write(
          `  $${task.bountyUsd.toFixed(2)} [${task.status}] ${sign}${min}:${sec.toString().padStart(2, '0')}  `,
        );
      }
      process.stdout.write('\n');

      await sleep(POLL_MS);
    }
  }

  console.log('\nAll tasks reached terminal state.');
}

async function autoApproveSubmissions(taskId: string, apiKey: string): Promise<void> {
  try {
    // Get submissions via Supabase (MCP API requires ownership verification)
    const submissions = await supabaseRequest(
      `submissions?task_id=eq.${taskId}&agent_verdict=is.null&select=id,executor_id`,
    );

    if (!submissions || submissions.length === 0) return;

    for (const sub of submissions) {
      console.log(`  Auto-approving submission ${sub.id.slice(0, 8)}...`);

      const res = await fetch(`${MCP_SERVER_URL}/api/v1/submissions/${sub.id}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({ notes: 'Auto-approved by test-x402-full-flow.ts' }),
      });

      if (res.ok) {
        const result = await res.json();
        console.log(`  Approved! Payment TX: ${result.data?.payment_tx || 'pending'}`);
      } else {
        const text = await res.text();
        console.log(`  Approval via API failed (${res.status}), falling back to Supabase...`);

        // Fallback: approve directly in Supabase
        await supabaseRequest(`submissions?id=eq.${sub.id}`, 'PATCH', {
          agent_verdict: 'accepted',
          agent_notes: 'Auto-approved by test-x402-full-flow.ts (direct)',
          verified_at: new Date().toISOString(),
        });

        // Also update task status
        await supabaseRequest(`tasks?id=eq.${taskId}`, 'PATCH', {
          status: 'completed',
        });
        console.log(`  Approved via Supabase (no payment settlement).`);
      }
    }
  } catch (err: any) {
    console.log(`  Error auto-approving: ${err.message?.slice(0, 80)}`);
  }
}

// =============================================================================
// Main Flow
// =============================================================================

async function main(): Promise<void> {
  const totalBounty = FIBONACCI_BOUNTIES.slice(0, TASK_COUNT).reduce((a, b) => a + b, 0);
  const totalWithFee = totalBounty * (1 + PLATFORM_FEE_PERCENT);

  console.log('\n' + '='.repeat(60));
  console.log('  Execution Market — Fibonacci x402 Payment Flow Test');
  console.log('='.repeat(60));
  console.log(`\n  Mode:         ${DIRECT_MODE ? 'Direct (Supabase)' : 'x402 via MCP API'}`);
  console.log(`  Wallet:       ${WALLET_ADDRESS}`);
  console.log(`  Tasks:        ${TASK_COUNT} (Fibonacci bounties)`);
  console.log(`  Bounties:     ${FIBONACCI_BOUNTIES.slice(0, TASK_COUNT).map((b) => `$${b.toFixed(2)}`).join(', ')}`);
  console.log(`  Total bounty: $${totalBounty.toFixed(2)} (+ ${PLATFORM_FEE_PERCENT * 100}% fee = $${totalWithFee.toFixed(2)})`);
  console.log(`  Deadline:     ${DEADLINE_MINUTES} min each`);
  console.log(`  Dashboard:    ${DASHBOARD_URL}`);
  console.log(`  MCP Server:   ${MCP_SERVER_URL}`);
  console.log(`  Facilitator:  ${FACILITATOR_URL}`);
  console.log(`  Monitor:      ${MONITOR_MODE ? 'Yes' : 'No'}`);
  console.log(`  Auto-approve: ${AUTO_APPROVE ? 'Yes' : 'No'}`);

  // =========================================================================
  // Step 1: Pre-flight checks
  // =========================================================================
  header(1, 'Pre-flight checks');

  // Check MCP server
  try {
    const healthRes = await fetch(`${MCP_SERVER_URL}/health`);
    const health = await healthRes.json();
    console.log(`  MCP Server: ${health.status} (uptime: ${Math.round(health.uptime_seconds)}s)`);

    const x402Status = health.components?.x402?.status;
    if (x402Status !== 'healthy') {
      console.log(`  x402 status: ${x402Status} — ${health.components?.x402?.message}`);
    }

    const chainStatus = health.components?.blockchain;
    if (chainStatus) {
      console.log(`  Blockchain: ${chainStatus.details?.network} @ block ${chainStatus.details?.block_number}`);
    }
  } catch {
    console.log('  MCP Server: unreachable (continuing anyway)');
  }

  // Check facilitator
  try {
    const fRes = await fetch(`${FACILITATOR_URL}/health`);
    const fHealth = await fRes.json();
    console.log(`  Facilitator: ${fHealth.status}`);
  } catch {
    console.log('  Facilitator: unreachable');
  }

  // Check USDC balance
  const usdcBalance = await publicClient.readContract({
    address: USDC_ADDRESS,
    abi: ERC20_ABI,
    functionName: 'balanceOf',
    args: [WALLET_ADDRESS],
  });
  const balanceFormatted = formatUnits(usdcBalance, 6);
  console.log(`  USDC balance: $${balanceFormatted} (Base Mainnet)`);

  if (!DIRECT_MODE) {
    const neededUnits = parseUnits(totalWithFee.toFixed(6), 6);
    if (usdcBalance < neededUnits) {
      console.log(`\n  WARNING: Insufficient USDC for x402 payments.`);
      console.log(`  Need $${totalWithFee.toFixed(2)} but have $${balanceFormatted}.`);
      console.log(`  The x402 headers will be signed but facilitator may reject them.`);
      console.log(`  Fund wallet: ${WALLET_ADDRESS} on Base Mainnet`);
    }
  }

  // =========================================================================
  // Step 2: Sign EIP-3009 authorizations (x402 mode only)
  // =========================================================================
  if (!DIRECT_MODE) {
    header(2, 'Sign EIP-3009 TransferWithAuthorization for each task');

    const apiKey = getApiKey();

    const createdTasks: CreatedTask[] = [];

    for (let i = 0; i < TASK_COUNT; i++) {
      const bounty = FIBONACCI_BOUNTIES[i];
      const totalAmount = bounty * (1 + PLATFORM_FEE_PERCENT);
      const template = TASK_TEMPLATES[i % TASK_TEMPLATES.length];

      console.log(`\n  [Fib #${i + 1}] $${bounty.toFixed(2)} (total with fee: $${totalAmount.toFixed(2)})`);

      // Sign EIP-3009
      const { authorization, signature } = await signTransferWithAuthorization(
        EM_TREASURY,
        totalAmount,
        DEADLINE_MINUTES * 60 + 300, // validity = deadline + 5min buffer
      );

      console.log(`  Signed: from=${authorization.from.slice(0, 10)}... to=${authorization.to.slice(0, 10)}... value=${authorization.value} nonce=${authorization.nonce.slice(0, 18)}...`);

      // Build x402 header
      const paymentHeader = buildX402PaymentHeader(authorization, signature);
      console.log(`  X-Payment header: ${paymentHeader.slice(0, 50)}...`);

      // Verify with facilitator directly (diagnostic)
      console.log(`  Verifying with facilitator...`);
      const verifyResult = await verifyWithFacilitator(paymentHeader, totalAmount);
      if (verifyResult.isValid || verifyResult.valid) {
        console.log(`  Facilitator: VALID (payer: ${verifyResult.payer?.slice(0, 10)}...)`);
      } else {
        console.log(`  Facilitator: ${JSON.stringify(verifyResult).slice(0, 150)}`);
      }

      // Try creating task via MCP API
      console.log(`  Creating task via MCP API...`);
      let task = await createTaskViaMCP(
        { ...template, bountyUsd: bounty },
        bounty,
        paymentHeader,
        apiKey,
      );

      if (task) {
        console.log(`  Task created via API: ${task.id}`);
        createdTasks.push({
          id: task.id,
          bountyUsd: bounty,
          fibIndex: i,
          deadline: task.deadline,
          paymentHeader,
          status: task.status || 'published',
        });
      } else {
        // Fallback to direct Supabase insert
        console.log(`  API failed, falling back to direct Supabase insert...`);
        task = await createTaskDirect(template, bounty, i);

        // Record escrow reference (simulated — the x402 auth was signed but not executed)
        const taskIdHash = keccak256(toHex(task.id));
        await supabaseRequest(`tasks?id=eq.${task.id}`, 'PATCH', {
          escrow_tx: `x402_auth_${signature.slice(0, 16)}`,
          escrow_id: taskIdHash,
        });

        const deadline = new Date(Date.now() + DEADLINE_MINUTES * 60 * 1000).toISOString();
        console.log(`  Task created via Supabase: ${task.id}`);
        createdTasks.push({
          id: task.id,
          bountyUsd: bounty,
          fibIndex: i,
          deadline,
          paymentHeader,
          status: 'published',
        });
      }
    }

    // =========================================================================
    // Step 3: Summary
    // =========================================================================
    header(3, 'Task Creation Summary');

    console.log(`\n  Created ${createdTasks.length} tasks:\n`);
    for (const t of createdTasks) {
      console.log(`  Fib #${t.fibIndex + 1}  $${t.bountyUsd.toFixed(2)}  ${t.id}  [${t.status}]`);
    }
    console.log(`\n  Total bounty: $${createdTasks.reduce((s, t) => s + t.bountyUsd, 0).toFixed(2)}`);
    console.log(`  Dashboard: ${DASHBOARD_URL}`);
    console.log(`\n  Open the dashboard, connect wallet, and accept tasks!`);

    // =========================================================================
    // Step 4: Monitor (optional)
    // =========================================================================
    if (MONITOR_MODE || AUTO_APPROVE) {
      header(4, 'Monitoring tasks');
      await monitorTasks(createdTasks, apiKey);
    }

    // =========================================================================
    // Final: Check balances
    // =========================================================================
    header(MONITOR_MODE ? 5 : 4, 'Final balance check');

    const finalBalance = await publicClient.readContract({
      address: USDC_ADDRESS,
      abi: ERC20_ABI,
      functionName: 'balanceOf',
      args: [WALLET_ADDRESS],
    });
    console.log(`  USDC balance: $${formatUnits(finalBalance, 6)} (was $${balanceFormatted})`);

    const diff = Number(finalBalance) - Number(usdcBalance);
    if (diff !== 0) {
      console.log(`  Change: ${diff > 0 ? '+' : ''}$${formatUnits(BigInt(diff < 0 ? -diff : diff), 6)}`);
    } else {
      console.log(`  No change (x402 authorizations are signed but not settled until approval)`);
    }

  } else {
    // =========================================================================
    // DIRECT MODE: Create tasks directly in Supabase
    // =========================================================================
    header(2, 'Creating tasks directly in Supabase');

    const createdTasks: CreatedTask[] = [];

    for (let i = 0; i < TASK_COUNT; i++) {
      const bounty = FIBONACCI_BOUNTIES[i];
      const template = TASK_TEMPLATES[i % TASK_TEMPLATES.length];

      console.log(`  [Fib #${i + 1}] $${bounty.toFixed(2)} — ${template.category}`);

      const task = await createTaskDirect(template, bounty, i);
      const deadline = new Date(Date.now() + DEADLINE_MINUTES * 60 * 1000).toISOString();

      // Simulated escrow reference
      const simTx = `0x${'0'.repeat(56)}fib${(i + 1).toString().padStart(2, '0')}`;
      const simId = keccak256(toHex(task.id));
      await supabaseRequest(`tasks?id=eq.${task.id}`, 'PATCH', {
        escrow_tx: simTx,
        escrow_id: simId,
      });

      console.log(`  Task: ${task.id}`);
      createdTasks.push({
        id: task.id,
        bountyUsd: bounty,
        fibIndex: i,
        deadline,
        status: 'published',
      });
    }

    header(3, 'Task Creation Summary');

    console.log(`\n  Created ${createdTasks.length} tasks (direct mode):\n`);
    for (const t of createdTasks) {
      console.log(`  Fib #${t.fibIndex + 1}  $${t.bountyUsd.toFixed(2)}  ${t.id}`);
    }
    console.log(`\n  Total bounty: $${createdTasks.reduce((s, t) => s + t.bountyUsd, 0).toFixed(2)}`);
    console.log(`  Dashboard: ${DASHBOARD_URL}`);

    if (MONITOR_MODE || AUTO_APPROVE) {
      const apiKey = getApiKey();
      header(4, 'Monitoring tasks');
      await monitorTasks(createdTasks, apiKey);
    }
  }

  // Done
  console.log('\n' + '='.repeat(60));
  console.log('  Test Complete');
  console.log('='.repeat(60));
  console.log('');
}

// =============================================================================
// Entry Point
// =============================================================================

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('\nFATAL ERROR:', err.message || err);
    if (err.stack) console.error(err.stack);
    process.exit(1);
  });
