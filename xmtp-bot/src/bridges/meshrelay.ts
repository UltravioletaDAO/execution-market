import { config } from "../config.js";
import { logger } from "../utils/logger.js";
import { apiClient } from "../services/api-client.js";
import { startIrcClient, stopIrcClient, onIrcMessage, sendToChannel, getIrcHealth } from "./irc-client.js";
import { formatTaskForIrc, formatStatusForIrc, markdownToIrc } from "./formatters.js";
import { getWalletByNick, linkNickToWallet, isValidEthAddress } from "./identity-map.js";

const BOUNTIES_CHANNEL = "#bounties";
const AGENTS_CHANNEL = "#Agents";

// ─── Initialize the bridge ──────────────────────────────────────────
export function startMeshRelayBridge(): void {
  if (!config.irc.enabled) {
    logger.info("MeshRelay bridge disabled");
    return;
  }

  // Register IRC message handler
  onIrcMessage(handleIrcMessage);

  // Start IRC connection
  startIrcClient();
  logger.info("MeshRelay bridge started");
}

export function stopMeshRelayBridge(): void {
  stopIrcClient();
  logger.info("MeshRelay bridge stopped");
}

// ─── IRC → XMTP: Handle incoming IRC messages ──────────────────────
async function handleIrcMessage(channel: string, nick: string, text: string): Promise<void> {
  const trimmed = text.trim();

  // Handle /claim command
  if (trimmed.startsWith("/claim ")) {
    await handleClaimCommand(channel, nick, trimmed);
    return;
  }

  // Handle /link command (identity mapping)
  if (trimmed.startsWith("/link ")) {
    await handleLinkCommand(channel, nick, trimmed);
    return;
  }

  // Handle /tasks command
  if (trimmed === "/tasks" || trimmed.startsWith("/tasks ")) {
    await handleTasksCommand(channel, nick, trimmed);
    return;
  }

  // Handle /status command
  if (trimmed.startsWith("/status ")) {
    await handleStatusCommand(channel, nick, trimmed);
    return;
  }

  // Handle /help command
  if (trimmed === "/help") {
    sendToChannel(channel, [
      "Execution Market Bot Commands:",
      "  /tasks [category] — List available tasks",
      "  /claim <task_id> — Apply to a task (requires /link first)",
      "  /status <task_id> — Check task status",
      "  /link <wallet_address> — Link your IRC nick to a wallet",
      "  /help — Show this help message",
    ].join("\n"));
    return;
  }
}

// ─── /claim <task_id> ───────────────────────────────────────────────
async function handleClaimCommand(channel: string, nick: string, text: string): Promise<void> {
  const parts = text.split(/\s+/);
  const taskIdPartial = parts[1];

  if (!taskIdPartial) {
    sendToChannel(channel, `${nick}: Usage: /claim <task_id>`);
    return;
  }

  // Check identity mapping
  const walletAddress = getWalletByNick(nick);
  if (!walletAddress) {
    sendToChannel(channel, `${nick}: Link your wallet first: /link <your_wallet_address>`);
    return;
  }

  try {
    // Resolve task
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      sendToChannel(channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    if (task.status !== "published") {
      sendToChannel(channel, `${nick}: Task ${taskIdPartial} is not available (status: ${task.status})`);
      return;
    }

    // Apply via API
    const result = await apiClient.post<any>("/api/v1/tasks/apply", {
      task_id: task.id,
      wallet_address: walletAddress,
      message: `Applied via IRC by ${nick}`,
    });

    const shortId = task.id.slice(0, 8);
    sendToChannel(channel, `${nick}: Applied to task ${shortId} — "${task.title}". Waiting for assignment.`);

    logger.info({ nick, taskId: task.id, wallet: walletAddress.slice(0, 10) }, "IRC claim submitted");
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Application failed";
    sendToChannel(channel, `${nick}: Error: ${detail}`);
    logger.error({ err, nick, taskId: taskIdPartial }, "IRC claim failed");
  }
}

// ─── /link <wallet_address> ─────────────────────────────────────────
async function handleLinkCommand(channel: string, nick: string, text: string): Promise<void> {
  const parts = text.split(/\s+/);
  const address = parts[1];

  if (!address || !isValidEthAddress(address)) {
    sendToChannel(channel, `${nick}: Invalid address. Usage: /link 0x1234...abcd (40 hex chars)`);
    return;
  }

  linkNickToWallet(nick, address);
  const short = `${address.slice(0, 6)}...${address.slice(-4)}`;
  sendToChannel(channel, `${nick}: Wallet linked: ${short}. You can now use /claim.`);
}

// ─── /tasks [category] ─────────────────────────────────────────────
async function handleTasksCommand(channel: string, nick: string, text: string): Promise<void> {
  const parts = text.split(/\s+/);
  const category = parts[1];

  try {
    const params: Record<string, string> = { status: "published", limit: "5" };
    if (category) params.category = category;

    const data = await apiClient.get<any>("/api/v1/tasks", { params });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      sendToChannel(channel, `${nick}: No tasks available right now.`);
      return;
    }

    sendToChannel(channel, `Available tasks (${tasks.length}):`);
    for (const t of tasks) {
      sendToChannel(channel, formatTaskForIrc(t));
    }
  } catch (err) {
    sendToChannel(channel, `${nick}: Error fetching tasks.`);
    logger.error({ err }, "IRC /tasks failed");
  }
}

// ─── /status <task_id> ──────────────────────────────────────────────
async function handleStatusCommand(channel: string, nick: string, text: string): Promise<void> {
  const parts = text.split(/\s+/);
  const taskIdPartial = parts[1];

  if (!taskIdPartial) {
    sendToChannel(channel, `${nick}: Usage: /status <task_id>`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      sendToChannel(channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    const bounty = parseFloat(String(task.bounty_usdc ?? task.bounty ?? 0)).toFixed(2);
    sendToChannel(channel, [
      `Task ${task.id.slice(0, 8)}: ${task.title}`,
      `  Status: ${task.status} | Bounty: $${bounty} USDC | Category: ${task.category ?? "general"}`,
      task.executor_id ? `  Executor: ${task.executor_id.slice(0, 8)}` : "  No executor assigned",
    ].join("\n"));
  } catch (err) {
    sendToChannel(channel, `${nick}: Error fetching task status.`);
    logger.error({ err }, "IRC /status failed");
  }
}

// ─── XMTP → IRC: Publish task notifications ────────────────────────
export function broadcastTaskToIrc(task: any): void {
  if (!config.irc.enabled) return;

  const msg = formatTaskForIrc(task);
  sendToChannel(BOUNTIES_CHANNEL, msg);
  logger.debug({ taskId: task.id }, "Task broadcast to IRC");
}

// ─── XMTP → IRC: Status updates ────────────────────────────────────
export function broadcastStatusToIrc(taskId: string, status: string, extra?: string): void {
  if (!config.irc.enabled) return;

  const msg = formatStatusForIrc(taskId, status, extra);

  // Status updates go to #bounties
  sendToChannel(BOUNTIES_CHANNEL, msg);
}

// ─── XMTP → IRC: Payment notification ──────────────────────────────
export function broadcastPaymentToIrc(task: any, txHash: string): void {
  if (!config.irc.enabled) return;

  const bounty = parseFloat(String(task.bounty_usdc ?? task.bounty ?? 0)).toFixed(2);
  const chain = task.payment_network ?? "base";
  const id = (task.id ?? task.task_id ?? "?").slice(0, 8);
  const msg = `[PAID] Task ${id} | $${bounty} USDC (${chain}) | TX: ${txHash.slice(0, 14)}...`;

  sendToChannel(BOUNTIES_CHANNEL, msg);
}

// ─── Bridge health ──────────────────────────────────────────────────
export function getBridgeHealth(): {
  enabled: boolean;
  irc: ReturnType<typeof getIrcHealth>;
} {
  return {
    enabled: config.irc.enabled,
    irc: getIrcHealth(),
  };
}
