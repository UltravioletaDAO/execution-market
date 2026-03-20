/**
 * EMServ Negotiation Commands — mutual cancellation, help.
 *
 * Migrated from legacy handlers in meshrelay.ts.
 */

import { apiClient } from "../../services/api-client.js";
import { TrustLevel } from "../../bridges/identity-store.js";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";

// ─── Mutual cancellation state ─────────────────────────────────
// taskShortId -> { proposer, expiresAt, timeoutHandle }
const mutualCancelProposals = new Map<
  string,
  { proposer: string; expiresAt: number; timeoutHandle: ReturnType<typeof setTimeout> }
>();

// ─── /mutual-cancel [reason] (task channel only) ───────────────

async function handleMutualCancel(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const channelTaskId = cmd.context.taskId;

  if (!channelTaskId) {
    send(cmd.context.channel, `${nick}: /mutual-cancel only works in #task-{id} channels.`);
    return;
  }

  const existing = mutualCancelProposals.get(channelTaskId);
  if (existing && existing.expiresAt > Date.now()) {
    send(
      cmd.context.channel,
      `${nick}: A mutual cancellation is already pending (from ${existing.proposer}). Use /confirm-cancel to accept.`,
    );
    return;
  }

  const reason = cmd.args.join(" ") || "No reason given";

  const timeoutHandle = setTimeout(() => {
    const proposal = mutualCancelProposals.get(channelTaskId);
    if (proposal && proposal.proposer === nick) {
      mutualCancelProposals.delete(channelTaskId);
      send(cmd.context.channel, `Mutual cancellation proposal by ${nick} expired. Use /cancel for unilateral.`);
    }
  }, 15 * 60 * 1000);

  mutualCancelProposals.set(channelTaskId, {
    proposer: nick,
    expiresAt: Date.now() + 15 * 60 * 1000,
    timeoutHandle,
  });

  send(cmd.context.channel, [
    `${nick} proposes mutual cancellation: ${reason}`,
    `Other party: /confirm-cancel to accept (15 min TTL). No reputation penalty.`,
  ].join("\n"));

  logger.info({ nick, taskId: channelTaskId, reason }, "Mutual cancel proposed");
}

// ─── /confirm-cancel (accept mutual cancellation) ──────────────

async function handleConfirmCancel(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const channelTaskId = cmd.context.taskId;

  if (!channelTaskId) {
    send(cmd.context.channel, `${nick}: /confirm-cancel only works in #task-{id} channels.`);
    return;
  }

  const proposal = mutualCancelProposals.get(channelTaskId);
  if (!proposal) {
    send(cmd.context.channel, `${nick}: No pending mutual cancellation proposal.`);
    return;
  }

  if (proposal.expiresAt < Date.now()) {
    clearTimeout(proposal.timeoutHandle);
    mutualCancelProposals.delete(channelTaskId);
    send(cmd.context.channel, `${nick}: Mutual cancellation proposal expired.`);
    return;
  }

  if (proposal.proposer === nick) {
    send(cmd.context.channel, `${nick}: You proposed the cancellation — the OTHER party must confirm.`);
    return;
  }

  clearTimeout(proposal.timeoutHandle);
  mutualCancelProposals.delete(channelTaskId);

  try {
    const task = await apiClient.resolveTask(channelTaskId);
    if (!task) {
      send(cmd.context.channel, `${nick}: Task not found.`);
      return;
    }

    await apiClient.post(`/api/v1/tasks/${task.id}/cancel`, {
      reason: `Mutual cancellation agreed by ${proposal.proposer} and ${nick}`,
      mutual: true,
    });

    send(cmd.context.channel, [
      `Mutual cancellation confirmed by ${nick}.`,
      `Escrow refunded. No reputation penalty. Channel closing in 5 minutes.`,
    ].join("\n"));

    logger.info(
      { taskId: channelTaskId, proposer: proposal.proposer, confirmer: nick },
      "Mutual cancellation confirmed",
    );
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Cancellation failed";
    send(cmd.context.channel, `${nick}: Error: ${detail}`);
    logger.error({ err, nick }, "Mutual cancel execution failed");
  }
}

// ─── /help ─────────────────────────────────────────────────────

async function handleHelp(cmd: ParsedCommand, send: SendFn): Promise<void> {
  // Lazy import to avoid circular dependency
  const { getRegisteredCommands } = await import("../index.js");
  const commands = getRegisteredCommands();

  const categories = new Map<string, typeof commands>();
  for (const c of commands) {
    const cat = c.category;
    if (!categories.has(cat)) categories.set(cat, []);
    categories.get(cat)!.push(c);
  }

  const lines = ["Execution Market Bot Commands:"];
  const categoryOrder = [
    "discovery",
    "task_ops",
    "publisher",
    "identity",
    "auction",
    "relay",
    "reputation",
    "dispute",
    "system",
  ];

  for (const cat of categoryOrder) {
    const cmds = categories.get(cat);
    if (!cmds || cmds.length === 0) continue;
    lines.push(`  [${cat}]`);
    for (const c of cmds) {
      const trustTag = c.minTrustLevel > 0 ? ` [L${c.minTrustLevel}]` : "";
      lines.push(`    ${c.usage} — ${c.description}${trustTag}`);
    }
  }

  lines.push("In #task-* channels, task_id is auto-detected.");
  send(cmd.context.channel, lines.join("\n"));
}

// ─── Command Definitions ───────────────────────────────────────

export const negotiationCommands: CommandDefinition[] = [
  {
    name: "mutual-cancel",
    aliases: ["mutualcancel"],
    description: "Propose zero-penalty cancellation (#task-* only)",
    usage: "/mutual-cancel [reason]",
    minTrustLevel: TrustLevel.LINKED,
    category: "task_ops",
    channelScoped: true,
    handler: handleMutualCancel,
  },
  {
    name: "confirm-cancel",
    aliases: ["confirmcancel"],
    description: "Accept mutual cancellation",
    usage: "/confirm-cancel",
    minTrustLevel: TrustLevel.LINKED,
    category: "task_ops",
    channelScoped: true,
    handler: handleConfirmCancel,
  },
  {
    name: "help",
    aliases: ["h", "commands"],
    description: "Show all available commands",
    usage: "/help",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "system",
    channelScoped: false,
    handler: handleHelp,
  },
];
