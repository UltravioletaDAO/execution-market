/**
 * Chamba Agent Simulation - Full MCP + x402 Payment Flow
 *
 * Simulates an AI agent that:
 * 1. Connects to Chamba MCP server
 * 2. Creates a task with escrow payment
 * 3. Monitors for submissions
 * 4. Approves and releases payment
 *
 * Usage:
 *   cd scripts
 *   npx tsx simulate_agent_mcp.ts
 *
 * Requirements:
 *   - MCP server running at API_URL
 *   - WALLET_PRIVATE_KEY with USDC balance (for real payments)
 *   - Or run with --mock for simulated payments
 */

import { createClient } from '@supabase/supabase-js';
import { createWalletClient, createPublicClient, http, parseUnits, formatUnits } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { avalanche } from 'viem/chains';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { randomUUID } from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment
config({ path: resolve(__dirname, '../.env.local') });

// Configuration
const API_URL = process.env.API_URL || 'https://api.chamba.ultravioletadao.xyz';
const SUPABASE_URL = process.env.SUPABASE_URL || 'https://puyhpytmtkyevnxffksl.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY;
const PRIVATE_KEY = process.env.WALLET_PRIVATE_KEY as `0x${string}`;
const MOCK_MODE = process.argv.includes('--mock');

// Contract addresses (Avalanche)
const USDC_ADDRESS = '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E';
const ESCROW_ADDRESS = '0xedA98AF95B76293a17399Af41A499C193A8DB51A';

// USDC ABI (minimal)
const USDC_ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
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

// ChambaEscrow ABI (minimal)
const ESCROW_ABI = [
  {
    name: 'createEscrow',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'taskId', type: 'bytes32' },
      { name: 'amount', type: 'uint256' },
      { name: 'deadline', type: 'uint256' },
    ],
    outputs: [{ name: 'escrowId', type: 'uint256' }],
  },
  {
    name: 'releaseEscrow',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'escrowId', type: 'uint256' },
      { name: 'worker', type: 'address' },
    ],
    outputs: [],
  },
  {
    name: 'getEscrow',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'escrowId', type: 'uint256' }],
    outputs: [
      { name: 'agent', type: 'address' },
      { name: 'amount', type: 'uint256' },
      { name: 'deadline', type: 'uint256' },
      { name: 'status', type: 'uint8' },
    ],
  },
] as const;

interface TaskData {
  id: string;
  title: string;
  instructions: string;
  category: string;
  bounty_usd: number;
  deadline_hours: number;
  evidence_required: string[];
}

class ChambaAgentSimulator {
  private supabase;
  private walletClient;
  private publicClient;
  private account;
  private agentId: string;

  constructor() {
    if (!SUPABASE_KEY) {
      throw new Error('Missing SUPABASE_KEY');
    }

    this.supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    if (!MOCK_MODE && PRIVATE_KEY) {
      this.account = privateKeyToAccount(PRIVATE_KEY);
      this.agentId = this.account.address;

      this.publicClient = createPublicClient({
        chain: avalanche,
        transport: http('https://api.avax.network/ext/bc/C/rpc'),
      });

      this.walletClient = createWalletClient({
        account: this.account,
        chain: avalanche,
        transport: http('https://api.avax.network/ext/bc/C/rpc'),
      });

      console.log('[Wallet] Agent address:', this.agentId);
    } else {
      this.agentId = 'mock-agent-' + Date.now();
      console.log('[Mock Mode] No real blockchain transactions');
    }
  }

  async checkBalance(): Promise<{ avax: string; usdc: string }> {
    if (MOCK_MODE || !this.publicClient || !this.account) {
      return { avax: '10.00', usdc: '100.00' };
    }

    const avaxBalance = await this.publicClient.getBalance({
      address: this.account.address,
    });

    const usdcBalance = await this.publicClient.readContract({
      address: USDC_ADDRESS,
      abi: USDC_ABI,
      functionName: 'balanceOf',
      args: [this.account.address],
    });

    return {
      avax: formatUnits(avaxBalance, 18),
      usdc: formatUnits(usdcBalance, 6),
    };
  }

  async callMcpTool(tool: string, params: Record<string, unknown>): Promise<unknown> {
    console.log(`\n[MCP] Calling ${tool}...`);

    const response = await fetch(`${API_URL}/mcp/tools/${tool}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Agent-ID': this.agentId,
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`MCP call failed: ${response.status} - ${error}`);
    }

    return response.json();
  }

  async createTaskViaMcp(task: TaskData): Promise<string> {
    // Try MCP first
    try {
      const result = await this.callMcpTool('chamba_publish_task', {
        agent_id: this.agentId,
        ...task,
      });
      console.log('[MCP] Task created:', result);
      return (result as { task_id: string }).task_id;
    } catch (error) {
      console.log('[MCP] MCP call failed, falling back to direct Supabase...');
    }

    // Fallback to direct Supabase
    const taskId = randomUUID();
    const deadline = new Date(Date.now() + task.deadline_hours * 60 * 60 * 1000);

    const { data, error } = await this.supabase
      .from('tasks')
      .insert({
        id: taskId,
        agent_id: this.agentId,
        title: task.title,
        instructions: task.instructions,
        category: task.category,
        status: 'published',
        bounty_usd: task.bounty_usd,
        deadline: deadline.toISOString(),
        evidence_required: task.evidence_required,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) throw error;
    return data.id;
  }

  async createEscrow(taskId: string, amountUsd: number): Promise<string> {
    if (MOCK_MODE || !this.walletClient || !this.account) {
      console.log('[Mock] Simulating escrow creation...');
      const mockEscrowId = 'mock-escrow-' + Date.now();

      // Update task with mock escrow
      await this.supabase
        .from('tasks')
        .update({
          escrow_id: mockEscrowId,
          escrow_status: 'funded',
          updated_at: new Date().toISOString(),
        })
        .eq('id', taskId);

      return mockEscrowId;
    }

    console.log('[Blockchain] Creating escrow on Avalanche...');

    // Convert USD to USDC (6 decimals)
    const amountUsdc = parseUnits(amountUsd.toString(), 6);

    // Check allowance
    const allowance = await this.publicClient!.readContract({
      address: USDC_ADDRESS,
      abi: USDC_ABI,
      functionName: 'allowance',
      args: [this.account.address, ESCROW_ADDRESS],
    });

    // Approve if needed
    if (allowance < amountUsdc) {
      console.log('[Blockchain] Approving USDC spend...');
      const approveHash = await this.walletClient.writeContract({
        address: USDC_ADDRESS,
        abi: USDC_ABI,
        functionName: 'approve',
        args: [ESCROW_ADDRESS, amountUsdc * 10n], // Approve 10x for future tasks
      });
      console.log('[Blockchain] Approve tx:', approveHash);
      await this.publicClient!.waitForTransactionReceipt({ hash: approveHash });
    }

    // Create escrow
    const taskIdBytes = ('0x' + taskId.replace(/-/g, '').padEnd(64, '0')) as `0x${string}`;
    const deadline = BigInt(Math.floor(Date.now() / 1000) + 24 * 60 * 60); // 24 hours

    const createHash = await this.walletClient.writeContract({
      address: ESCROW_ADDRESS,
      abi: ESCROW_ABI,
      functionName: 'createEscrow',
      args: [taskIdBytes, amountUsdc, deadline],
    });

    console.log('[Blockchain] Create escrow tx:', createHash);
    const receipt = await this.publicClient!.waitForTransactionReceipt({ hash: createHash });

    // Parse escrow ID from logs (simplified)
    const escrowId = receipt.logs[0]?.topics[1] || createHash;

    // Update task with escrow info
    await this.supabase
      .from('tasks')
      .update({
        escrow_id: escrowId,
        escrow_tx: createHash,
        escrow_status: 'funded',
        updated_at: new Date().toISOString(),
      })
      .eq('id', taskId);

    return escrowId as string;
  }

  async monitorSubmissions(taskId: string, timeoutMs: number = 60000): Promise<unknown | null> {
    console.log('\n[Monitor] Waiting for submissions...');
    console.log('[Monitor] Task ID:', taskId);
    console.log('[Monitor] Timeout:', timeoutMs / 1000, 'seconds');

    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      const { data: submissions } = await this.supabase
        .from('submissions')
        .select('*')
        .eq('task_id', taskId)
        .order('created_at', { ascending: false })
        .limit(1);

      if (submissions && submissions.length > 0) {
        console.log('[Monitor] Submission found!');
        return submissions[0];
      }

      // Wait 5 seconds before checking again
      await new Promise((resolve) => setTimeout(resolve, 5000));
      process.stdout.write('.');
    }

    console.log('\n[Monitor] No submissions received within timeout');
    return null;
  }

  async approveSubmission(submissionId: string, taskId: string): Promise<void> {
    console.log('\n[Approve] Approving submission:', submissionId);

    // Update submission status
    await this.supabase
      .from('submissions')
      .update({
        status: 'accepted',
        verified_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .eq('id', submissionId);

    // Update task status
    await this.supabase
      .from('tasks')
      .update({
        status: 'completed',
        completed_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .eq('id', taskId);

    console.log('[Approve] Submission approved, task completed');
  }

  async releasePayment(taskId: string, workerAddress: string): Promise<void> {
    if (MOCK_MODE || !this.walletClient) {
      console.log('[Mock] Simulating payment release to:', workerAddress);
      return;
    }

    console.log('[Blockchain] Releasing payment to:', workerAddress);

    // Get escrow ID from task
    const { data: task } = await this.supabase
      .from('tasks')
      .select('escrow_id')
      .eq('id', taskId)
      .single();

    if (!task?.escrow_id) {
      throw new Error('No escrow found for task');
    }

    // Release escrow
    const releaseHash = await this.walletClient.writeContract({
      address: ESCROW_ADDRESS,
      abi: ESCROW_ABI,
      functionName: 'releaseEscrow',
      args: [BigInt(task.escrow_id), workerAddress as `0x${string}`],
    });

    console.log('[Blockchain] Release tx:', releaseHash);
    await this.publicClient!.waitForTransactionReceipt({ hash: releaseHash });

    // Update escrow status
    await this.supabase
      .from('tasks')
      .update({
        escrow_status: 'released',
        payment_tx: releaseHash,
        updated_at: new Date().toISOString(),
      })
      .eq('id', taskId);

    console.log('[Blockchain] Payment released successfully');
  }
}

async function main() {
  console.log('=============================================');
  console.log('  Chamba Agent Simulation');
  console.log('  Full MCP + x402 Payment Flow');
  console.log('=============================================\n');

  if (MOCK_MODE) {
    console.log('[MODE] Running in MOCK mode (no real transactions)\n');
  } else {
    console.log('[MODE] Running in LIVE mode (real blockchain transactions)\n');
  }

  const agent = new ChambaAgentSimulator();

  // Step 1: Check balance
  console.log('\n--- Step 1: Check Wallet Balance ---');
  const balance = await agent.checkBalance();
  console.log('AVAX:', balance.avax);
  console.log('USDC:', balance.usdc);

  if (!MOCK_MODE && parseFloat(balance.usdc) < 5) {
    console.error('\n[Error] Insufficient USDC balance. Need at least $5 USDC.');
    console.log('Run with --mock for simulated payments.');
    process.exit(1);
  }

  // Step 2: Create task
  console.log('\n--- Step 2: Create Task via MCP ---');
  const taskData: TaskData = {
    id: randomUUID(),
    title: 'Agent Test - Photo of Local Landmark',
    instructions: `
Please take a clear photo of any local landmark in your area.

Requirements:
- Photo must be taken today (timestamp will be verified)
- Include GPS location data
- Landmark should be clearly visible
- Brief description of the landmark

This is an automated test task from the Chamba Agent Simulator.
Created: ${new Date().toISOString()}
    `.trim(),
    category: 'physical_presence',
    bounty_usd: 5.0,
    deadline_hours: 24,
    evidence_required: ['photo_geo', 'text_response'],
  };

  const taskId = await agent.createTaskViaMcp(taskData);
  console.log('[Task] Created with ID:', taskId);

  // Step 3: Create escrow
  console.log('\n--- Step 3: Create Escrow Payment ---');
  const escrowId = await agent.createEscrow(taskId, taskData.bounty_usd);
  console.log('[Escrow] Created with ID:', escrowId);

  // Step 4: Monitor for submissions
  console.log('\n--- Step 4: Monitor for Submissions ---');
  console.log('Waiting for a worker to submit evidence...');
  console.log('(Press Ctrl+C to skip and complete simulation)\n');

  // Short timeout for demo purposes
  const submission = await agent.monitorSubmissions(taskId, 30000);

  if (submission) {
    // Step 5: Approve submission
    console.log('\n--- Step 5: Approve Submission ---');
    await agent.approveSubmission((submission as { id: string }).id, taskId);

    // Step 6: Release payment
    console.log('\n--- Step 6: Release Payment ---');
    const workerAddress = (submission as { worker_id: string }).worker_id;
    await agent.releasePayment(taskId, workerAddress);
  } else {
    console.log('\n[Simulation] No submissions received (normal for testing)');
    console.log('[Simulation] Task remains published for workers to find');
  }

  // Summary
  console.log('\n=============================================');
  console.log('  Simulation Complete');
  console.log('=============================================\n');
  console.log('Task ID:', taskId);
  console.log('Escrow ID:', escrowId);
  console.log('Mode:', MOCK_MODE ? 'Mock' : 'Live');
  console.log('');
  console.log('View task:');
  console.log('  https://app.chamba.ultravioletadao.xyz/tasks/' + taskId);
  console.log('');
}

main().catch((error) => {
  console.error('\n[Error]', error.message);
  process.exit(1);
});
