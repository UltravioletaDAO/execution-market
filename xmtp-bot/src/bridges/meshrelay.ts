import { config } from "../config.js";
import { logger } from "../utils/logger.js";
import { startIrcClient, stopIrcClient, onIrcMessage, sendToChannel, getIrcHealth } from "./irc-client.js";
import { formatTaskForIrc, formatStatusForIrc } from "./formatters.js";
import { identityStore } from "./identity-store.js";
import { handleCommand as emservHandleCommand } from "../emserv/index.js";

const BOUNTIES_CHANNEL = "#bounties";

// ─── Initialize the bridge ──────────────────────────────────────────
export function startMeshRelayBridge(): void {
  if (!config.irc.enabled) {
    logger.info("MeshRelay bridge disabled");
    return;
  }

  // Initialize persistent identity store
  identityStore.init();
  identityStore.loadAllToCache().catch((err) => {
    logger.error({ err }, "Failed to load identities on startup");
  });

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

  // Skip non-commands
  if (!trimmed.startsWith("/")) return;

  // All commands handled by EMServ registry (identity, core, negotiation, discovery, etc.)
  const handled = await emservHandleCommand(channel, nick, trimmed, sendToChannel);
  if (handled) {
    // Update last seen on any successful command
    identityStore.touchLastSeen(nick).catch(() => {});
  }
}

// Legacy command handlers removed — all commands now in emserv/commands/
// (identity.ts, core.ts, negotiation.ts, tasks.ts, discovery.ts, auction.ts, match.ts, relay.ts)

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
