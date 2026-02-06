/**
 * Execution Market - Rapid x402 Full Flow Test
 *
 * Fast end-to-end test for create -> apply -> assign -> verify evidence -> submit -> approve.
 * Designed for iteration with very small bounties and short task windows.
 *
 * Usage:
 *   npm exec -- tsx test-x402-rapid-flow.ts -- --count 1 --deadline 2
 *   npm exec -- tsx test-x402-rapid-flow.ts -- --count 3 --bounty 0.01 --auto-approve
 *   npm exec -- tsx test-x402-rapid-flow.ts -- --run-refund-check
 *   npm exec -- tsx test-x402-rapid-flow.ts -- --dry-run
 *
 * Notes:
 * - Task creation uses x402 + facilitator (no direct wallet contract calls).
 * - Worker assignment uses REST endpoint `/api/v1/tasks/{task_id}/assign` when available.
 * - Optional Supabase fallback can be used only for assignment/deadline patching.
 */

import {
  createPublicClient,
  http,
  formatUnits,
  parseUnits,
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

// ---------------------------------------------------------------------------
// CLI args
// ---------------------------------------------------------------------------

function parseArgs(): Record<string, string> {
  const args: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith('--')) continue;
    const key = arg.slice(2);
    if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
      args[key] = argv[i + 1];
      i++;
    } else {
      args[key] = 'true';
    }
  }
  return args;
}

function boolArg(args: Record<string, string>, key: string, defaultValue: boolean): boolean {
  if (!(key in args)) return defaultValue;
  const value = String(args[key]).toLowerCase();
  return value !== 'false' && value !== '0' && value !== 'no';
}

const ARGS = parseArgs();
const COUNT = Math.max(1, parseInt(ARGS.count || '1', 10));
const DEADLINE_MINUTES = Math.max(1, parseInt(ARGS.deadline || '2', 10));
const BOUNTY_USD = Number(ARGS.bounty || '0.01');
const PLATFORM_FEE_PERCENT = Number(ARGS.fee || process.env.EM_PLATFORM_FEE || '0.08');
const AUTO_APPROVE = boolArg(ARGS, 'auto-approve', true);
const STRICT = boolArg(ARGS, 'strict', true);
const RUN_REFUND_CHECK = boolArg(ARGS, 'run-refund-check', true);
const ALLOW_SUPABASE_FALLBACK = boolArg(ARGS, 'allow-supabase-fallback', true);
const DRY_RUN = boolArg(ARGS, 'dry-run', false);

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const PRIVATE_KEY = process.env.WALLET_PRIVATE_KEY as Hex | undefined;
if (!PRIVATE_KEY) {
  console.error('ERROR: WALLET_PRIVATE_KEY is missing in .env.local');
  process.exit(1);
}

const account = privateKeyToAccount(PRIVATE_KEY);
const AGENT_WALLET = account.address;

const API_URL = process.env.API_URL || 'https://mcp.execution.market';
const FACILITATOR_URL = process.env.X402_FACILITATOR_URL || 'https://facilitator.ultravioletadao.xyz';
const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';

const API_KEY = process.env.EM_API_KEY || 'em_starter_d10baa5d63f02a223494cf9a1bb0d645';
const WORKER_WALLET = (process.env.WORKER_WALLET_ADDRESS || AGENT_WALLET).toLowerCase();
const MOCK_PHOTO_URL =
  process.env.MOCK_PHOTO_URL ||
  'https://upload.wikimedia.org/wikipedia/commons/3/3f/Fronalpstock_big.jpg';

const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as Address;
const EM_TREASURY = '0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad' as Address;

const ERC20_ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

const publicClient = createPublicClient({ chain: base, transport: http() });

type JsonObject = Record<string, unknown>;

interface ApiResponse<T = unknown> {
  status: number;
  ok: boolean;
  data: T | null;
  text: string;
}

interface FlowResult {
  index: number;
  taskId: string;
  submissionId?: string;
  finalStatus?: string;
  createEscrowId?: string | null;
  createEscrowTx?: string | null;
  submissionPaymentTx?: string | null;
  approvalPaymentTx?: string | null;
  payoutEventTx?: string | null;
  payoutEventType?: string | null;
  notes: string[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function header(step: string): void {
  console.log('\n' + '='.repeat(72));
  console.log(step);
  console.log('='.repeat(72));
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, ms));
}

function nowIso(): string {
  return new Date().toISOString();
}

function roundUsd(value: number): number {
  return Number(value.toFixed(2));
}

async function apiRequest<T = unknown>(
  path: string,
  method: 'GET' | 'POST' | 'PATCH' = 'GET',
  body?: JsonObject,
  headers?: Record<string, string>,
): Promise<ApiResponse<T>> {
  const url = path.startsWith('http') ? path : `${API_URL}${path}`;
  const reqHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers || {}),
  };
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await fetch(url, {
      method,
      headers: reqHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });

    const text = await response.text();
    let parsed: T | null = null;
    if (text) {
      try {
        parsed = JSON.parse(text) as T;
      } catch {
        parsed = null;
      }
    }

    if (response.status === 429 && attempt < 2) {
      const payloadRetry = Number((parsed as any)?.retry_after || 0);
      const headerRetry = Number(response.headers.get('retry-after') || 0);
      const retryAfter = Math.max(1, payloadRetry || headerRetry || 2);
      await sleep((retryAfter + 1) * 1000);
      continue;
    }

    return {
      status: response.status,
      ok: response.ok,
      data: parsed,
      text,
    };
  }

  return { status: 429, ok: false, data: null, text: 'Rate limited after retries' };
}

async function supabaseRequest(
  path: string,
  method: 'GET' | 'POST' | 'PATCH' = 'GET',
  body?: JsonObject,
): Promise<ApiResponse<unknown>> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    return { status: 0, ok: false, data: null, text: 'Supabase credentials not configured' };
  }
  const headers: Record<string, string> = {
    apikey: SUPABASE_ANON_KEY,
    Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
    'Content-Type': 'application/json',
  };
  if (method === 'POST' || method === 'PATCH') headers['Prefer'] = 'return=representation';
  return apiRequest(`${SUPABASE_URL}/rest/v1/${path}`, method, body, headers);
}

// ---------------------------------------------------------------------------
// x402 header builder (EIP-3009)
// ---------------------------------------------------------------------------

const USDC_EIP712_DOMAIN = {
  name: 'USD Coin',
  version: '2',
  chainId: 8453n,
  verifyingContract: USDC_ADDRESS,
} as const;

const TRANSFER_WITH_AUTH_TYPES = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' },
  ],
} as const;

async function signTransferWithAuthorization(
  to: Address,
  amountUsd: number,
  validForSeconds: number,
): Promise<{ authorization: Record<string, string>; signature: Hex }> {
  const value = parseUnits(amountUsd.toFixed(6), 6);
  const now = Math.floor(Date.now() / 1000);

  const nonceBytes = new Uint8Array(32);
  crypto.getRandomValues(nonceBytes);
  const nonce = `0x${Array.from(nonceBytes).map((b) => b.toString(16).padStart(2, '0')).join('')}` as Hex;

  const authorization = {
    from: AGENT_WALLET,
    to,
    value: value.toString(),
    validAfter: '0',
    validBefore: String(now + validForSeconds),
    nonce,
  };

  const signature = await account.signTypedData({
    domain: USDC_EIP712_DOMAIN,
    types: TRANSFER_WITH_AUTH_TYPES,
    primaryType: 'TransferWithAuthorization',
    message: {
      from: authorization.from,
      to: authorization.to,
      value: BigInt(authorization.value),
      validAfter: BigInt(authorization.validAfter),
      validBefore: BigInt(authorization.validBefore),
      nonce: authorization.nonce as Hex,
    },
  });

  return { authorization, signature };
}

function buildX402Header(authorization: Record<string, string>, signature: Hex): string {
  const payload = {
    x402Version: 1,
    scheme: 'exact',
    network: 'base',
    payload: { signature, authorization },
  };
  return Buffer.from(JSON.stringify(payload)).toString('base64');
}

async function verifyWithFacilitator(paymentHeader: string, amountUsd: number): Promise<ApiResponse<unknown>> {
  const paymentPayload = JSON.parse(Buffer.from(paymentHeader, 'base64').toString());
  const verifyBody = {
    x402Version: 1,
    paymentPayload,
    paymentRequirements: {
      scheme: 'exact',
      network: 'base',
      maxAmountRequired: parseUnits(amountUsd.toFixed(6), 6).toString(),
      resource: `${API_URL}/api/v1/tasks`,
      description: 'Execution Market rapid task payment',
      mimeType: 'application/json',
      payTo: EM_TREASURY,
      maxTimeoutSeconds: 3600,
      asset: USDC_ADDRESS,
      extra: {},
    },
  };
  return apiRequest(`${FACILITATOR_URL}/verify`, 'POST', verifyBody);
}

// ---------------------------------------------------------------------------
// Flow operations
// ---------------------------------------------------------------------------

async function registerWorker(walletAddress: string): Promise<{ id: string }> {
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await apiRequest<{ executor: { id: string } }>(
      '/api/v1/executors/register',
      'POST',
      {
        wallet_address: walletAddress,
        display_name: `Rapid Worker ${walletAddress.slice(2, 8)}`,
      },
    );

    if (response.ok && response.data && (response.data as any).executor?.id) {
      return { id: (response.data as any).executor.id };
    }

    if (response.status === 429 && attempt < 2) {
      const retryAfter = Number((response.data as any)?.retry_after || 2);
      await sleep((Math.max(1, retryAfter) + 1) * 1000);
      continue;
    }

    throw new Error(`Worker register failed (${response.status}): ${response.text}`);
  }
  throw new Error('Worker register failed after retries');
}

async function createPaidTask(index: number, bountyUsd: number): Promise<any> {
  const totalWithFee = roundUsd(bountyUsd * (1 + PLATFORM_FEE_PERCENT));
  const auth = await signTransferWithAuthorization(EM_TREASURY, totalWithFee, DEADLINE_MINUTES * 60 + 600);
  const paymentHeader = buildX402Header(auth.authorization, auth.signature);

  const verify = await verifyWithFacilitator(paymentHeader, totalWithFee);
  const verifyPayload = verify.data as any;
  const verifyOk = Boolean((verifyPayload || {}).isValid || (verifyPayload || {}).valid);
  if (!verifyOk) {
    const reason = verify.text || 'Facilitator rejected payment header';
    if (STRICT) throw new Error(`Facilitator verify failed: ${reason}`);
    console.log(`  WARN verify failed (non-strict): ${reason.slice(0, 180)}`);
  }

  const taskReq = {
    title: `[RAPID x402 #${index + 1}] Mock verification flow ${nowIso()}`,
    instructions:
      'Automated test task. Submit a photo URL and a brief text response. ' +
      'This task is used to validate end-to-end escrow/payment behavior.',
    category: 'simple_action',
    bounty_usd: bountyUsd,
    deadline_hours: Math.max(1, Math.ceil(DEADLINE_MINUTES / 60)),
    evidence_required: ['photo', 'text_response'],
    location_hint: 'Remote',
    min_reputation: 0,
    payment_token: 'USDC',
  };

  for (let attempt = 0; attempt < 2; attempt++) {
    const response = await apiRequest('/api/v1/tasks', 'POST', taskReq, {
      Authorization: `Bearer ${API_KEY}`,
      'X-Payment': paymentHeader,
    });

    if (response.ok && response.data) {
      return response.data;
    }

    if (response.status === 429 && attempt === 0) {
      const retryAfter = Number((response.data as any)?.retry_after || 15);
      const waitMs = Math.max(5, retryAfter + 1) * 1000;
      console.log(`  API rate-limited on create task. Retrying in ${Math.round(waitMs / 1000)}s...`);
      await sleep(waitMs);
      continue;
    }

    throw new Error(`Create task failed (${response.status}): ${response.text}`);
  }

  throw new Error('Create task failed after retry');
}

async function tryPatchShortDeadline(taskId: string): Promise<boolean> {
  if (!ALLOW_SUPABASE_FALLBACK || !SUPABASE_URL || !SUPABASE_ANON_KEY) return false;
  const deadline = new Date(Date.now() + DEADLINE_MINUTES * 60 * 1000).toISOString();
  const patch = await supabaseRequest(`tasks?id=eq.${taskId}`, 'PATCH', { deadline });
  return patch.ok;
}

async function applyToTask(taskId: string, executorId: string): Promise<void> {
  const response = await apiRequest(
    `/api/v1/tasks/${taskId}/apply`,
    'POST',
    { executor_id: executorId, message: 'Rapid E2E application' },
  );
  if (!response.ok) throw new Error(`Apply failed (${response.status}): ${response.text}`);
}

async function assignTask(taskId: string, executorId: string): Promise<{ mode: string }> {
  const response = await apiRequest(
    `/api/v1/tasks/${taskId}/assign`,
    'POST',
    { executor_id: executorId, notes: 'Assigned by rapid x402 test script' },
    { Authorization: `Bearer ${API_KEY}` },
  );

  if (response.ok) return { mode: 'api' };

  if (!ALLOW_SUPABASE_FALLBACK || !SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error(`Assign failed (${response.status}): ${response.text}`);
  }

  // Backward-compatible fallback for environments without the new assign endpoint.
  const updateTask = await supabaseRequest(`tasks?id=eq.${taskId}`, 'PATCH', {
    executor_id: executorId,
    status: 'accepted',
  });

  if (!updateTask.ok) {
    throw new Error(`Assign fallback failed: ${updateTask.text}`);
  }

  return { mode: 'supabase-fallback' };
}

async function verifyEvidence(taskId: string): Promise<ApiResponse<unknown>> {
  return apiRequest('/api/v1/evidence/verify', 'POST', {
    task_id: taskId,
    evidence_url: MOCK_PHOTO_URL,
    evidence_type: 'photo',
  });
}

async function submitWork(taskId: string, executorId: string): Promise<any> {
  const payload = {
    executor_id: executorId,
    evidence: {
      photo: MOCK_PHOTO_URL,
      text_response: `Rapid flow verification ${nowIso()}`,
    },
    notes: 'Submitted by rapid x402 test script',
  };
  const response = await apiRequest(`/api/v1/tasks/${taskId}/submit`, 'POST', payload);
  if (!response.ok) throw new Error(`Submit failed (${response.status}): ${response.text}`);
  return response.data;
}

function extractMissingColumn(errorText: string): string | null {
  let raw = errorText;
  try {
    const parsed = JSON.parse(errorText);
    raw = String(parsed?.message || parsed?.error || errorText);
  } catch {
    // Keep raw as-is.
  }
  const match = raw.match(/Could not find the '([^']+)' column/i);
  return match ? match[1] : null;
}

async function submitWorkFallback(taskId: string, executorId: string): Promise<{ submission_id: string; status: string; fallback: boolean }> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error('submit fallback unavailable: supabase credentials missing');
  }

  const baseEvidence = {
    photo: MOCK_PHOTO_URL,
    text_response: `Rapid flow fallback submission ${nowIso()}`,
  };

  const insertPayload: Record<string, unknown> = {
    task_id: taskId,
    executor_id: executorId,
    evidence: baseEvidence,
    submitted_at: nowIso(),
    agent_verdict: 'pending',
  };

  let submissionRow: any = null;
  let payload = { ...insertPayload };

  while (Object.keys(payload).length > 0) {
    const response = await supabaseRequest('submissions', 'POST', payload);
    if (response.ok) {
      const rows = Array.isArray(response.data) ? response.data : [];
      submissionRow = rows[0] || null;
      break;
    }

    const missingColumn = extractMissingColumn(response.text);
    if (missingColumn && missingColumn in payload) {
      delete payload[missingColumn];
      continue;
    }
    throw new Error(`Submit fallback failed (${response.status}): ${response.text}`);
  }

  if (!submissionRow?.id) {
    throw new Error('Submit fallback did not return a submission row');
  }

  const taskPatch = await supabaseRequest(`tasks?id=eq.${taskId}`, 'PATCH', { status: 'submitted' });
  if (!taskPatch.ok) {
    throw new Error(`Submit fallback could not mark task as submitted: ${taskPatch.text}`);
  }

  return {
    submission_id: submissionRow.id,
    status: 'submitted',
    fallback: true,
  };
}

async function approveSubmission(submissionId: string): Promise<any> {
  const response = await apiRequest(
    `/api/v1/submissions/${submissionId}/approve`,
    'POST',
    { notes: 'Auto-approved by rapid x402 test script' },
    { Authorization: `Bearer ${API_KEY}` },
  );
  if (!response.ok) throw new Error(`Approve failed (${response.status}): ${response.text}`);
  return response.data;
}

async function getTask(taskId: string): Promise<any> {
  const response = await apiRequest(`/api/v1/tasks/${taskId}`, 'GET', undefined, {
    Authorization: `Bearer ${API_KEY}`,
  });
  if (!response.ok) throw new Error(`Get task failed (${response.status}): ${response.text}`);
  return response.data;
}

async function getTaskPayment(taskId: string): Promise<any> {
  const response = await apiRequest(`/api/v1/tasks/${taskId}/payment`, 'GET', undefined, {
    Authorization: `Bearer ${API_KEY}`,
  });
  if (!response.ok) throw new Error(`Get payment failed (${response.status}): ${response.text}`);
  return response.data;
}

async function cancelTask(taskId: string): Promise<any> {
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await apiRequest(
      `/api/v1/tasks/${taskId}/cancel`,
      'POST',
      { reason: 'Rapid flow refund check' },
      { Authorization: `Bearer ${API_KEY}` },
    );
    if (response.ok) return response.data;
    if (response.status === 429 && attempt < 2) {
      const retryAfter = Number((response.data as any)?.retry_after || 10);
      await sleep((Math.max(1, retryAfter) + 1) * 1000);
      continue;
    }
    throw new Error(`Cancel failed (${response.status}): ${response.text}`);
  }
  throw new Error('Cancel failed after retries');
}

async function waitForTerminal(taskId: string, timeoutMs = 120000): Promise<any> {
  const start = Date.now();
  let lastStatus = 'unknown';
  while (Date.now() - start < timeoutMs) {
    const task = await getTask(taskId);
    const status = task?.status || 'unknown';
    if (status !== lastStatus) {
      lastStatus = status;
      console.log(`    Task ${taskId.slice(0, 8)} status -> ${status}`);
    }
    if (['completed', 'cancelled', 'expired'].includes(status)) return task;
    await sleep(3000);
  }
  return getTask(taskId);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  header('Rapid x402 Full Flow');
  console.log(`API URL: ${API_URL}`);
  console.log(`Facilitator: ${FACILITATOR_URL}`);
  console.log(`Agent wallet: ${AGENT_WALLET}`);
  console.log(`Worker wallet: ${WORKER_WALLET}`);
  console.log(`Count: ${COUNT}, bounty: $${BOUNTY_USD.toFixed(2)}, deadline: ${DEADLINE_MINUTES}m`);
  console.log(`Strict: ${STRICT ? 'yes' : 'no'}, auto-approve: ${AUTO_APPROVE ? 'yes' : 'no'}`);
  console.log(`Supabase fallback: ${ALLOW_SUPABASE_FALLBACK ? 'enabled' : 'disabled'}`);
  if (DRY_RUN) {
    console.log('Dry run enabled. No remote writes will be executed.');
    return;
  }

  const health = await apiRequest<{ status?: string }>('/health');
  if (!health.ok) {
    throw new Error(`API health failed (${health.status}): ${health.text}`);
  }
  console.log(`Health: ${(health.data as any)?.status || 'ok'}`);

  const usdcBalance = await publicClient.readContract({
    address: USDC_ADDRESS,
    abi: ERC20_ABI,
    functionName: 'balanceOf',
    args: [AGENT_WALLET],
  });
  console.log(`USDC balance: ${formatUnits(usdcBalance, 6)}`);

  const worker = await registerWorker(WORKER_WALLET);
  console.log(`Worker executor_id: ${worker.id}`);

  const results: FlowResult[] = [];

  for (let i = 0; i < COUNT; i++) {
    header(`Flow ${i + 1}/${COUNT}`);
    const result: FlowResult = { index: i + 1, taskId: '', notes: [] };
    try {
      const task = await createPaidTask(i, BOUNTY_USD);
      result.taskId = task.id;
      result.createEscrowId = task.escrow_id || null;
      result.createEscrowTx = task.escrow_tx || null;
      console.log(`  Created task: ${task.id}`);

      const patched = await tryPatchShortDeadline(task.id);
      if (patched) result.notes.push(`deadline patched to ~${DEADLINE_MINUTES}m`);

      await applyToTask(task.id, worker.id);
      console.log('  Applied as worker');

      const assign = await assignTask(task.id, worker.id);
      console.log(`  Assigned (${assign.mode})`);
      result.notes.push(`assign mode=${assign.mode}`);

      const verification = await verifyEvidence(task.id);
      if (verification.ok) {
        const payload = verification.data as any;
        result.notes.push(`verify=${payload?.decision || 'ok'} confidence=${payload?.confidence ?? 'n/a'}`);
      } else if (STRICT) {
        throw new Error(`Evidence verify failed (${verification.status}): ${verification.text}`);
      } else {
        result.notes.push(`verify-failed=${verification.status}`);
      }

      let submitData: any;
      try {
        const submit = await submitWork(task.id, worker.id);
        submitData = (submit as any)?.data || {};
      } catch (submitError: any) {
        if (!ALLOW_SUPABASE_FALLBACK) throw submitError;
        const fallback = await submitWorkFallback(task.id, worker.id);
        submitData = fallback;
        result.notes.push('submit mode=supabase-fallback');
      }

      result.submissionId = submitData.submission_id;
      result.submissionPaymentTx = submitData.payment_tx || null;
      console.log(`  Submitted evidence (submission=${result.submissionId || 'n/a'})`);

      if (!result.submissionPaymentTx && AUTO_APPROVE && result.submissionId) {
        const approval = await approveSubmission(result.submissionId);
        const approvalData = (approval as any)?.data || {};
        result.approvalPaymentTx = approvalData.payment_tx || null;
        console.log(`  Approved submission (payment_tx=${result.approvalPaymentTx || 'pending'})`);
      }

      const terminal = await waitForTerminal(task.id);
      result.finalStatus = terminal?.status || 'unknown';

      const payment = await getTaskPayment(task.id);
      const events: any[] = Array.isArray(payment?.events) ? payment.events : [];
      const payoutEvent =
        events.find((ev) => String(ev?.type || '').includes('release')) ||
        events.find((ev) => String(ev?.type || '').includes('payment'));
      result.payoutEventTx = payoutEvent?.tx_hash || null;
      result.payoutEventType = payoutEvent?.type || null;

      results.push(result);
    } catch (error: any) {
      console.error(`  Flow ${i + 1} failed: ${error.message || error}`);
      if (STRICT) throw error;
      result.notes.push(`error=${error.message || error}`);
      results.push(result);
    }
  }

  let refundCheck: any = null;
  if (RUN_REFUND_CHECK) {
    header('Refund Check');
    try {
      const task = await createPaidTask(999, BOUNTY_USD);
      console.log(`  Refund task created: ${task.id}`);
      const cancel = await cancelTask(task.id);
      const payment = await getTaskPayment(task.id);
      const events: any[] = Array.isArray(payment?.events) ? payment.events : [];
      const refundEvent = events.find((ev) => String(ev?.type || '').includes('refund'));
      refundCheck = {
        task_id: task.id,
        cancel_response: cancel,
        refund_event_type: refundEvent?.type || null,
        refund_tx: refundEvent?.tx_hash || null,
      };
      console.log(`  Refund status: ${(cancel as any)?.data?.escrow?.status || 'n/a'}`);
      if (refundEvent?.tx_hash) {
        console.log(`  Refund tx: ${refundEvent.tx_hash}`);
      }
    } catch (error: any) {
      refundCheck = { error: error.message || String(error) };
      if (STRICT) throw error;
      console.error(`  Refund check failed (non-strict): ${refundCheck.error}`);
    }
  }

  header('Summary');
  const payload = {
    mode: 'live',
    api_url: API_URL,
    facilitator: FACILITATOR_URL,
    agent_wallet: AGENT_WALLET,
    worker_wallet: WORKER_WALLET,
    count: COUNT,
    bounty_usd: BOUNTY_USD,
    deadline_minutes: DEADLINE_MINUTES,
    flows: results,
    refund_check: refundCheck,
    generated_at: nowIso(),
  };
  console.log(JSON.stringify(payload, null, 2));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error('\nFATAL:', error.message || error);
    if (error?.stack) console.error(error.stack);
    process.exit(1);
  });
