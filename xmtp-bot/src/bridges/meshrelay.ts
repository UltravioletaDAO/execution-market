import { config } from "../config.js";
import { logger } from "../utils/logger.js";
import { apiClient } from "../services/api-client.js";
import { startIrcClient, stopIrcClient, onIrcMessage, sendToChannel, getIrcHealth } from "./irc-client.js";
import { formatTaskForIrc, formatStatusForIrc, markdownToIrc, trustBadge, checkTrustLevel } from "./formatters.js";
import { getWalletByNick, linkNickToWallet, isValidEthAddress } from "./identity-map.js";
import { identityStore, TrustLevel } from "./identity-store.js";
import { verifyMessage } from "viem";
import { randomBytes } from "crypto";

const BOUNTIES_CHANNEL = "#bounties";
const AGENTS_CHANNEL = "#Agents";

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

  // Trust level enforcement for commands
  const trustLevel = await identityStore.getTrustLevel(nick);
  const { allowed, required } = checkTrustLevel(trimmed, trustLevel);
  if (!allowed) {
    const levelNames = ["ANONYMOUS", "LINKED", "VERIFIED", "REGISTERED"];
    sendToChannel(
      channel,
      `${nick}: Requires ${levelNames[required]} (L${required}). ${required === TrustLevel.LINKED ? "Run /link first." : required === TrustLevel.VERIFIED ? "Run /verify first." : "Run /register first."}`,
    );
    return;
  }

  // Update last seen
  identityStore.touchLastSeen(nick).catch(() => {});

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

  // Handle /verify command (initiate challenge)
  if (trimmed === "/verify") {
    await handleVerifyCommand(channel, nick);
    return;
  }

  // Handle /verify-sig <signature> (complete challenge)
  if (trimmed.startsWith("/verify-sig ")) {
    await handleVerifySigCommand(channel, nick, trimmed);
    return;
  }

  // Handle /register command (ERC-8004 binding)
  if (trimmed === "/register") {
    await handleRegisterCommand(channel, nick);
    return;
  }

  // Handle /whoami command (show identity info)
  if (trimmed === "/whoami") {
    await handleWhoamiCommand(channel, nick);
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
      "  /claim <task_id> — Apply to a task (requires /link)",
      "  /status <task_id> — Check task status",
      "  /link <wallet_address> — Link IRC nick to wallet [L1]",
      "  /verify — Start wallet verification [L1->L2]",
      "  /verify-sig <sig> — Complete verification with signature",
      "  /register — Bind ERC-8004 identity [L2->L3]",
      "  /whoami — Show your identity info and trust level",
      "  /help — Show this help message",
      "Trust levels: (anon) (linked) [V]erified [R]egistered",
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
    const result = await apiClient.post<any>(`/api/v1/tasks/${task.id}/apply`, {
      executor_id: walletAddress,
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
  sendToChannel(channel, `${nick}: Wallet linked: ${short} (L1). You can now /claim tasks. Run /verify for L2.`);
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

// ─── /verify (initiate challenge-response) ────────────────────────
async function handleVerifyCommand(channel: string, nick: string): Promise<void> {
  const wallet = await identityStore.getWalletByNick(nick);
  if (!wallet) {
    sendToChannel(channel, `${nick}: Link your wallet first: /link <address>`);
    return;
  }

  const trustLevel = await identityStore.getTrustLevel(nick);
  if (trustLevel >= TrustLevel.VERIFIED) {
    sendToChannel(channel, `${nick}: Already verified ${trustBadge(trustLevel)}`);
    return;
  }

  // Generate nonce
  const nonce = randomBytes(16).toString("hex");
  const timestamp = Math.floor(Date.now() / 1000);
  await identityStore.storeChallenge(nick, nonce, 5);

  const message = `EM-VERIFY:${nonce}:${nick.toLowerCase()}:${timestamp}`;
  sendToChannel(
    channel,
    `${nick}: Sign this message with your wallet: "${message}" — then /verify-sig <signature> (5 min TTL)`,
  );
  logger.info({ nick }, "Verification challenge issued");
}

// ─── /verify-sig <signature> (complete challenge) ─────────────────
async function handleVerifySigCommand(channel: string, nick: string, text: string): Promise<void> {
  const parts = text.split(/\s+/);
  const signature = parts[1];

  if (!signature || !signature.startsWith("0x")) {
    sendToChannel(channel, `${nick}: Usage: /verify-sig 0x<signature>`);
    return;
  }

  const challenge = await identityStore.getChallenge(nick);
  if (!challenge) {
    sendToChannel(channel, `${nick}: No pending challenge. Run /verify first.`);
    return;
  }

  // Check expiry
  if (new Date(challenge.expiresAt) < new Date()) {
    await identityStore.clearChallenge(nick);
    sendToChannel(channel, `${nick}: Challenge expired. Run /verify again.`);
    return;
  }

  // Reconstruct the message that was signed
  // The nonce contains only the hex — we need to try the full message format
  const timestamp = challenge.nonce; // We stored just the nonce, need to reconstruct
  const message = `EM-VERIFY:${challenge.nonce}:${nick.toLowerCase()}:`;

  try {
    // Verify signature — viem's verifyMessage checks ecrecover
    const isValid = await verifyMessage({
      address: challenge.wallet as `0x${string}`,
      message: { raw: Buffer.from(message) as any },
      signature: signature as `0x${string}`,
    }).catch(() => false);

    // Also try with the full message as a regular string (more common wallet behavior)
    let verified = isValid;
    if (!verified) {
      // Try all recent timestamps (within 5 min window)
      const now = Math.floor(Date.now() / 1000);
      for (let t = now - 300; t <= now; t++) {
        const fullMsg = `EM-VERIFY:${challenge.nonce}:${nick.toLowerCase()}:${t}`;
        const check = await verifyMessage({
          address: challenge.wallet as `0x${string}`,
          message: fullMsg,
          signature: signature as `0x${string}`,
        }).catch(() => false);
        if (check) {
          verified = true;
          break;
        }
      }
    }

    if (verified) {
      await identityStore.setTrustLevel(nick, TrustLevel.VERIFIED);
      await identityStore.clearChallenge(nick);
      const short = `${challenge.wallet.slice(0, 6)}...${challenge.wallet.slice(-4)}`;
      sendToChannel(channel, `${nick}[V]: Wallet ${short} verified! Trust level: VERIFIED.`);
      logger.info({ nick, wallet: challenge.wallet.slice(0, 10) }, "Identity verified via signature");
    } else {
      sendToChannel(channel, `${nick}: Signature does not match linked wallet. Try again.`);
      logger.warn({ nick }, "Verification signature mismatch");
    }
  } catch (err) {
    sendToChannel(channel, `${nick}: Verification error. Check signature format.`);
    logger.error({ err, nick }, "Verification failed");
  }
}

// ─── /register (ERC-8004 binding) ────────────────────────────────
async function handleRegisterCommand(channel: string, nick: string): Promise<void> {
  const trustLevel = await identityStore.getTrustLevel(nick);

  if (trustLevel < TrustLevel.VERIFIED) {
    sendToChannel(channel, `${nick}: Must be verified first. Run /verify.`);
    return;
  }

  if (trustLevel >= TrustLevel.REGISTERED) {
    sendToChannel(channel, `${nick}[R]: Already registered with ERC-8004.`);
    return;
  }

  const wallet = await identityStore.getWalletByNick(nick);
  if (!wallet) {
    sendToChannel(channel, `${nick}: No wallet linked. Run /link first.`);
    return;
  }

  try {
    // Check ERC-8004 registration via API
    const data = await apiClient.get<any>("/api/v1/reputation/lookup", {
      params: { wallet },
    });

    if (data?.agent_id) {
      await identityStore.setAgentId(nick, data.agent_id);
      sendToChannel(
        channel,
        `${nick}[R]: ERC-8004 Agent #${data.agent_id} bound! Trust level: REGISTERED. Full marketplace access.`,
      );
      logger.info({ nick, agentId: data.agent_id }, "ERC-8004 identity bound");
    } else {
      sendToChannel(
        channel,
        `${nick}: No ERC-8004 agent found for your wallet. Register at execution.market/register or via /em-register-identity.`,
      );
    }
  } catch (err: any) {
    const status = err?.response?.status;
    if (status === 404) {
      sendToChannel(
        channel,
        `${nick}: No ERC-8004 agent found. Register at execution.market/register.`,
      );
    } else {
      sendToChannel(channel, `${nick}: Error checking registration. Try again later.`);
      logger.error({ err, nick }, "ERC-8004 lookup failed");
    }
  }
}

// ─── /whoami (identity info) ──────────────────────────────────────
async function handleWhoamiCommand(channel: string, nick: string): Promise<void> {
  const identity = await identityStore.getIdentity(nick);

  if (!identity) {
    sendToChannel(channel, `${nick}: No identity found. Run /link <wallet> to get started.`);
    return;
  }

  const badge = trustBadge(identity.trust_level as TrustLevel);
  const short = `${identity.wallet_address.slice(0, 6)}...${identity.wallet_address.slice(-4)}`;
  const lines = [
    `${nick}${badge}: Trust L${identity.trust_level} | Wallet: ${short}`,
  ];
  if (identity.agent_id) lines.push(`  ERC-8004 Agent #${identity.agent_id}`);
  if (identity.verified_at) lines.push(`  Verified: ${identity.verified_at.slice(0, 10)}`);
  lines.push(`  Channel pref: ${identity.preferred_channel}`);

  sendToChannel(channel, lines.join("\n"));
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
