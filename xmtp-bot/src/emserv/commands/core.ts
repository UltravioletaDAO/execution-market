/**
 * EMServ Core Commands — claim, tasks, status, submit, approve, reject, cancel.
 *
 * Migrated from legacy handlers in meshrelay.ts.
 */

import { apiClient } from "../../services/api-client.js";
import { identityStore, TrustLevel } from "../../bridges/identity-store.js";
import { getWalletByNick } from "../../bridges/identity-map.js";
import { formatTaskForIrc } from "../../bridges/formatters.js";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";

// ─── /claim <task_id> ──────────────────────────────────────────

async function handleClaim(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const taskIdPartial = cmd.args[0];
  const nick = cmd.context.nick;

  if (!taskIdPartial) {
    send(cmd.context.channel, `${nick}: Usage: /claim <task_id>`);
    return;
  }

  const walletAddress = getWalletByNick(nick);
  if (!walletAddress) {
    send(cmd.context.channel, `${nick}: Link your wallet first: /link <your_wallet_address>`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      send(cmd.context.channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    if (task.status !== "published") {
      send(cmd.context.channel, `${nick}: Task ${taskIdPartial} is not available (status: ${task.status})`);
      return;
    }

    await apiClient.post<any>(`/api/v1/tasks/${task.id}/apply`, {
      executor_id: walletAddress,
      message: `Applied via IRC by ${nick}`,
    });

    const shortId = task.id.slice(0, 8);
    send(cmd.context.channel, `${nick}: Applied to task ${shortId} — "${task.title}". Waiting for assignment.`);
    logger.info({ nick, taskId: task.id, wallet: walletAddress.slice(0, 10) }, "IRC claim submitted");
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Application failed";
    send(cmd.context.channel, `${nick}: Error: ${detail}`);
    logger.error({ err, nick, taskId: taskIdPartial }, "IRC claim failed");
  }
}

// ─── /tasks [category] ────────────────────────────────────────

async function handleTasks(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const category = cmd.args[0];

  try {
    const params: Record<string, string> = { status: "published", limit: "5" };
    if (category) params.category = category;

    const data = await apiClient.get<any>("/api/v1/tasks", { params });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      send(cmd.context.channel, `${cmd.context.nick}: No tasks available right now.`);
      return;
    }

    send(cmd.context.channel, `Available tasks (${tasks.length}):`);
    for (const t of tasks) {
      send(cmd.context.channel, formatTaskForIrc(t));
    }
  } catch {
    send(cmd.context.channel, `${cmd.context.nick}: Error fetching tasks.`);
  }
}

// ─── /status [task_id] (channel-scoped) ────────────────────────

async function handleStatus(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const taskIdPartial = cmd.args[0] || cmd.context.taskId;
  const nick = cmd.context.nick;

  if (!taskIdPartial) {
    send(cmd.context.channel, `${nick}: Usage: /status <task_id>`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      send(cmd.context.channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    const bounty = parseFloat(String(task.bounty_usdc ?? task.bounty ?? 0)).toFixed(2);
    send(cmd.context.channel, [
      `Task ${task.id.slice(0, 8)}: ${task.title}`,
      `  Status: ${task.status} | Bounty: $${bounty} USDC | Category: ${task.category ?? "general"}`,
      task.executor_id ? `  Executor: ${task.executor_id.slice(0, 8)}` : "  No executor assigned",
    ].join("\n"));
  } catch {
    send(cmd.context.channel, `${nick}: Error fetching task status.`);
  }
}

// ─── /submit [task_id] <evidence_url> (channel-scoped) ─────────

async function handleSubmit(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const channelTaskId = cmd.context.taskId;

  let taskIdPartial: string | undefined;
  let evidenceUrl: string | undefined;

  if (channelTaskId) {
    evidenceUrl = cmd.args[0];
    taskIdPartial = channelTaskId;
  } else {
    taskIdPartial = cmd.args[0];
    evidenceUrl = cmd.args[1];
  }

  if (!taskIdPartial) {
    send(cmd.context.channel, `${nick}: Usage: /submit <task_id> <evidence_url>`);
    return;
  }

  const walletAddress = await identityStore.getWalletByNick(nick);
  if (!walletAddress) {
    send(cmd.context.channel, `${nick}: Link your wallet first: /link <address>`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      send(cmd.context.channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    const evidence: Record<string, unknown> = {};
    if (evidenceUrl) {
      evidence.url = evidenceUrl;
      evidence.submitted_via = "irc";
    }

    await apiClient.submitEvidence(task.id, walletAddress, evidence);
    send(cmd.context.channel, `${nick}: Evidence submitted for task ${task.id.slice(0, 8)}.`);
    logger.info({ nick, taskId: task.id }, "IRC evidence submitted");
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Submission failed";
    send(cmd.context.channel, `${nick}: Error: ${detail}`);
    logger.error({ err, nick }, "IRC /submit failed");
  }
}

// ─── /approve [task_id] (channel-scoped, publisher) ────────────

async function handleApprove(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const taskIdPartial = cmd.args[0] || cmd.context.taskId;

  if (!taskIdPartial) {
    send(cmd.context.channel, `${nick}: Usage: /approve <task_id>`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      send(cmd.context.channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    const subs = await apiClient.get<any>(`/api/v1/tasks/${task.id}/submissions`);
    const submissions = Array.isArray(subs) ? subs : subs.submissions ?? [];
    const pending = submissions.find((s: any) => s.status === "submitted" || s.status === "pending");

    if (!pending) {
      send(cmd.context.channel, `${nick}: No pending submission to approve.`);
      return;
    }

    await apiClient.post(`/api/v1/submissions/${pending.id}/approve`, { verdict: "approved" });
    send(cmd.context.channel, `${nick}: Submission approved for task ${task.id.slice(0, 8)}! Payment releasing.`);
    logger.info({ nick, taskId: task.id }, "IRC submission approved");
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Approval failed";
    send(cmd.context.channel, `${nick}: Error: ${detail}`);
    logger.error({ err, nick }, "IRC /approve failed");
  }
}

// ─── /reject [task_id] [reason] (channel-scoped, publisher) ────

async function handleReject(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const channelTaskId = cmd.context.taskId;

  let taskIdPartial: string | undefined;
  let reason: string;

  if (channelTaskId) {
    taskIdPartial = channelTaskId;
    reason = cmd.args.join(" ") || "Rejected via IRC";
  } else {
    taskIdPartial = cmd.args[0];
    reason = cmd.args.slice(1).join(" ") || "Rejected via IRC";
  }

  if (!taskIdPartial) {
    send(cmd.context.channel, `${nick}: Usage: /reject <task_id> [reason]`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      send(cmd.context.channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    const subs = await apiClient.get<any>(`/api/v1/tasks/${task.id}/submissions`);
    const submissions = Array.isArray(subs) ? subs : subs.submissions ?? [];
    const pending = submissions.find((s: any) => s.status === "submitted" || s.status === "pending");

    if (!pending) {
      send(cmd.context.channel, `${nick}: No pending submission to reject.`);
      return;
    }

    await apiClient.post(`/api/v1/submissions/${pending.id}/reject`, { verdict: "rejected", reason });
    send(cmd.context.channel, `${nick}: Submission rejected for task ${task.id.slice(0, 8)}. Reason: ${reason}`);
    logger.info({ nick, taskId: task.id }, "IRC submission rejected");
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Rejection failed";
    send(cmd.context.channel, `${nick}: Error: ${detail}`);
    logger.error({ err, nick }, "IRC /reject failed");
  }
}

// ─── /cancel [task_id] (channel-scoped) ────────────────────────

async function handleCancel(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const taskIdPartial = cmd.args[0] || cmd.context.taskId;

  if (!taskIdPartial) {
    send(cmd.context.channel, `${nick}: Usage: /cancel <task_id>`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      send(cmd.context.channel, `${nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    await apiClient.post(`/api/v1/tasks/${task.id}/cancel`, { reason: "Cancelled via IRC" });
    send(cmd.context.channel, `${nick}: Task ${task.id.slice(0, 8)} cancelled.`);
    logger.info({ nick, taskId: task.id }, "IRC task cancelled");
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Cancellation failed";
    send(cmd.context.channel, `${nick}: Error: ${detail}`);
    logger.error({ err, nick }, "IRC /cancel failed");
  }
}

// ─── Command Definitions ───────────────────────────────────────

export const coreCommands: CommandDefinition[] = [
  {
    name: "claim",
    aliases: [],
    description: "Apply to a task (requires /link)",
    usage: "/claim <task_id>",
    minTrustLevel: TrustLevel.LINKED,
    category: "task_ops",
    channelScoped: false,
    handler: handleClaim,
  },
  {
    name: "tasks",
    aliases: ["list"],
    description: "List available tasks",
    usage: "/tasks [category]",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "discovery",
    channelScoped: false,
    handler: handleTasks,
  },
  {
    name: "status",
    aliases: ["st"],
    description: "Check task status (ID optional in #task-* channels)",
    usage: "/status [task_id]",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "discovery",
    channelScoped: true,
    handler: handleStatus,
  },
  {
    name: "submit",
    aliases: [],
    description: "Submit evidence for a task",
    usage: "/submit [task_id] <evidence_url>",
    minTrustLevel: TrustLevel.LINKED,
    category: "task_ops",
    channelScoped: true,
    handler: handleSubmit,
  },
  {
    name: "approve",
    aliases: [],
    description: "Approve submission (publisher only)",
    usage: "/approve [task_id]",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "publisher",
    channelScoped: true,
    handler: handleApprove,
  },
  {
    name: "reject",
    aliases: [],
    description: "Reject submission with reason",
    usage: "/reject [task_id] [reason]",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "publisher",
    channelScoped: true,
    handler: handleReject,
  },
  {
    name: "cancel",
    aliases: [],
    description: "Cancel a published task",
    usage: "/cancel [task_id]",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "publisher",
    channelScoped: true,
    handler: handleCancel,
  },
];
