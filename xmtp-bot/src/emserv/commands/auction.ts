/**
 * EMServ Auction Commands — reverse auction bidding system.
 *
 * Commands: /bid, /select-bid, /bids
 *
 * Reverse auction: publisher posts task with --auction flag,
 * workers bid lower prices competitively. Anti-sniping extends deadline.
 */

import { apiClient } from "../../services/api-client.js";
import { TrustLevel } from "../../bridges/identity-store.js";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";

// In-memory auction state (tracks active auctions for anti-sniping)
const activeAuctions = new Map<
  string,
  { endsAt: number; taskId: string; bids: Array<{ nick: string; amount: number; message: string }> }
>();

const ANTI_SNIPE_WINDOW_MS = 30_000; // 30 seconds
const ANTI_SNIPE_EXTENSION_MS = 30_000;

// ─── /bid <task_id> <amount> [message] ───────────────────────────

async function handleBid(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  let taskId = "";
  let amount = 0;
  let message = "";

  if (cmd.jsonPayload) {
    taskId = (cmd.jsonPayload.task_id as string) ?? "";
    amount = parseFloat(String(cmd.jsonPayload.amount ?? 0));
    message = (cmd.jsonPayload.message as string) ?? "";
  } else {
    taskId = cmd.args[0] ?? "";
    amount = parseFloat(cmd.args[1] ?? "0");
    message = cmd.args.slice(2).join(" ");
  }

  if (!taskId || amount <= 0) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /bid <task_id> <amount_usdc> [message]`);
    return;
  }

  // Track bid in auction state
  const auction = activeAuctions.get(taskId);
  if (auction) {
    // Anti-sniping: extend if bid in last 30s
    const now = Date.now();
    if (auction.endsAt - now < ANTI_SNIPE_WINDOW_MS) {
      auction.endsAt += ANTI_SNIPE_EXTENSION_MS;
      const secsLeft = Math.round((auction.endsAt - now) / 1000);
      send(
        cmd.context.channel,
        `[ANTI-SNIPE] Late bid! Auction extended. ${secsLeft}s remaining.`,
      );
    }
    auction.bids.push({ nick: cmd.context.nick, amount, message });
  }

  // Announce bid
  const msgStr = message ? ` — "${message}"` : "";
  send(
    cmd.context.channel,
    `[BID] ${cmd.context.nick} bids $${amount.toFixed(2)} USDC for task ${taskId.slice(0, 8)}${msgStr}`,
  );

  logger.info({ nick: cmd.context.nick, taskId, amount }, "Auction bid placed");
}

// ─── /select-bid <task_id> <nick_or_wallet> ──────────────────────

async function handleSelectBid(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  let taskId = "";
  let selectedNickOrWallet = "";

  if (cmd.jsonPayload) {
    taskId = (cmd.jsonPayload.task_id as string) ?? "";
    selectedNickOrWallet = (cmd.jsonPayload.winner as string) ?? "";
  } else {
    taskId = cmd.args[0] ?? "";
    selectedNickOrWallet = cmd.args[1] ?? "";
  }

  if (!taskId || !selectedNickOrWallet) {
    send(
      cmd.context.channel,
      `${cmd.context.nick}: Usage: /select-bid <task_id> <nick_or_wallet>`,
    );
    return;
  }

  // Close auction
  activeAuctions.delete(taskId);

  send(
    cmd.context.channel,
    `[AUCTION] ${cmd.context.nick} selected ${selectedNickOrWallet} for task ${taskId.slice(0, 8)}. Use /assign to finalize.`,
  );

  logger.info({ nick: cmd.context.nick, taskId, winner: selectedNickOrWallet }, "Bid selected");
}

// ─── /bids [task_id] ─────────────────────────────────────────────

async function handleBids(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const taskId = cmd.args[0] ?? cmd.context.taskId ?? "";

  if (!taskId) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /bids <task_id>`);
    return;
  }

  const auction = activeAuctions.get(taskId);
  if (!auction || auction.bids.length === 0) {
    send(cmd.context.channel, `[BIDS] No bids for task ${taskId.slice(0, 8)} yet.`);
    return;
  }

  // Sort by amount ascending (lowest = best)
  const sorted = [...auction.bids].sort((a, b) => a.amount - b.amount);
  const lines = sorted.map(
    (b, i) => `${i + 1}. ${b.nick}: $${b.amount.toFixed(2)}${b.message ? ` — ${b.message}` : ""}`,
  );

  send(
    cmd.context.channel,
    `[BIDS] ${sorted.length} bid(s) for task ${taskId.slice(0, 8)}:\n${lines.join("\n")}`,
  );
}

// ─── Auction Management ──────────────────────────────────────────

/**
 * Start tracking an auction for a task. Called when a task is published
 * with --auction flag.
 */
export function startAuction(taskId: string, durationMinutes: number = 10): void {
  activeAuctions.set(taskId, {
    endsAt: Date.now() + durationMinutes * 60_000,
    taskId,
    bids: [],
  });
}

export function getAuctionState(
  taskId: string,
): { endsAt: number; bids: Array<{ nick: string; amount: number; message: string }> } | undefined {
  return activeAuctions.get(taskId);
}

// ─── Command Registry ────────────────────────────────────────────

export const auctionCommands: CommandDefinition[] = [
  {
    name: "bid",
    aliases: [],
    description: "Place a bid on an auction task",
    usage: "/bid <task_id> <amount_usdc> [message]",
    minTrustLevel: TrustLevel.LINKED,
    category: "auction",
    channelScoped: true,
    handler: handleBid,
  },
  {
    name: "select-bid",
    aliases: ["pick"],
    description: "Select winning bid (publisher only)",
    usage: "/select-bid <task_id> <nick_or_wallet>",
    minTrustLevel: TrustLevel.LINKED,
    category: "auction",
    channelScoped: true,
    handler: handleSelectBid,
  },
  {
    name: "bids",
    aliases: [],
    description: "List current bids on a task",
    usage: "/bids [task_id]",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "auction",
    channelScoped: true,
    handler: handleBids,
  },
];
