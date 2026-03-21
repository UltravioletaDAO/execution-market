/**
 * EMServ Task Commands — Discovery, Task Ops, Publisher Ops, Status.
 *
 * 15 core commands organized by category from protocol spec.
 */

import { apiClient } from "../../services/api-client.js";
import { identityStore, TrustLevel } from "../../bridges/identity-store.js";
import { formatTaskForIrc, trustBadge } from "../../bridges/formatters.js";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";
import {
  startWizard,
  getWizardSession,
  advanceWizard,
  cancelWizard,
  getWizardData,
} from "../wizard-state.js";

// ─── Discovery Commands ──────────────────────────────────────────

async function handleSearch(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const query = cmd.args.join(" ") || cmd.jsonPayload?.query as string;
  if (!query) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /search <query>`);
    return;
  }

  try {
    const data = await apiClient.get<any>("/api/v1/tasks", {
      params: { status: "published", limit: "5", search: query },
    });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      send(cmd.context.channel, `${cmd.context.nick}: No tasks matching "${query}".`);
      return;
    }

    send(cmd.context.channel, `Search results for "${query}" (${tasks.length}):`);
    for (const t of tasks) {
      send(cmd.context.channel, formatTaskForIrc(t));
    }
  } catch {
    send(cmd.context.channel, `${cmd.context.nick}: Search failed.`);
  }
}

async function handleDetails(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const taskIdPartial = cmd.args[0] || cmd.context.taskId;
  if (!taskIdPartial) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /details <task_id>`);
    return;
  }

  try {
    const task = await apiClient.resolveTask(taskIdPartial);
    if (!task) {
      send(cmd.context.channel, `${cmd.context.nick}: Task not found: ${taskIdPartial}`);
      return;
    }

    const bounty = parseFloat(String(task.bounty_usdc ?? task.bounty ?? 0)).toFixed(2);
    const lines = [
      `Task ${task.id.slice(0, 8)}: ${task.title}`,
      `  Status: ${task.status} | Bounty: $${bounty} USDC`,
      `  Category: ${task.category ?? "general"} | Network: ${task.payment_network ?? "base"}`,
    ];
    if (task.description) lines.push(`  Description: ${task.description.slice(0, 200)}`);
    if (task.executor_id) lines.push(`  Executor: ${task.executor_id.slice(0, 8)}`);
    if (task.deadline) lines.push(`  Deadline: ${task.deadline}`);

    send(cmd.context.channel, lines.join("\n"));
  } catch {
    send(cmd.context.channel, `${cmd.context.nick}: Error fetching task details.`);
  }
}

// ─── Task Ops Commands ───────────────────────────────────────────

async function handleUnclaim(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const taskIdPartial = cmd.args[0] || cmd.context.taskId;
  if (!taskIdPartial) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /unclaim <task_id>`);
    return;
  }

  send(cmd.context.channel, `${cmd.context.nick}: Unclaim not yet supported via API. Use the dashboard.`);
}

async function handleExtend(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const taskIdPartial = cmd.args[0] || cmd.context.taskId;
  const minutes = cmd.args[1] || cmd.flags.minutes;

  if (!taskIdPartial || !minutes) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /extend <task_id> <minutes>`);
    return;
  }

  send(cmd.context.channel, `${cmd.context.nick}: Deadline extension not yet supported via API.`);
}

// ─── Publisher Commands ──────────────────────────────────────────

async function handlePublish(cmd: ParsedCommand, send: SendFn): Promise<void> {
  // Agent JSON mode — direct publish
  if (cmd.jsonPayload) {
    const wallet = cmd.context.walletAddress;
    if (!wallet) {
      send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
      return;
    }

    try {
      const payload = {
        title: cmd.jsonPayload.title as string,
        description: cmd.jsonPayload.description as string || "",
        category: cmd.jsonPayload.category as string || "simple_action",
        bounty_usdc: cmd.jsonPayload.bounty_usdc as number,
        deadline_minutes: cmd.jsonPayload.deadline_minutes as number || 15,
        payment_network: cmd.jsonPayload.payment_network as string || "base",
        agent_wallet: wallet,
      };

      const result = await apiClient.post<any>("/api/v1/tasks", payload);
      const taskId = result?.id?.slice(0, 8) ?? "?";
      send(cmd.context.channel, `[NEW TASK] Published: ${payload.title} | $${payload.bounty_usdc} USDC | /claim ${taskId}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Publish failed";
      send(cmd.context.channel, `${cmd.context.nick}: Error: ${detail}`);
    }
    return;
  }

  // Human wizard mode
  const existing = getWizardSession(cmd.context.nick);
  if (existing) {
    send(cmd.context.channel, `${cmd.context.nick}: Wizard already active. /cancel to abort.`);
    return;
  }

  startWizard(cmd.context.nick, cmd.context.channel);
  send(cmd.context.channel, `${cmd.context.nick}: Starting task publish wizard. What's the task title?`);
}

async function handleConfirm(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const data = getWizardData(cmd.context.nick);
  if (!data || !data.title) {
    send(cmd.context.channel, `${cmd.context.nick}: No active wizard.`);
    return;
  }

  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  cancelWizard(cmd.context.nick);

  try {
    const payload = {
      title: data.title,
      category: data.category || "simple_action",
      bounty_usdc: data.bounty_usdc || 0.10,
      deadline_minutes: data.deadline_minutes || 15,
      payment_network: data.payment_network || "base",
      agent_wallet: wallet,
    };

    const result = await apiClient.post<any>("/api/v1/tasks", payload);
    const taskId = result?.id?.slice(0, 8) ?? "?";
    send(cmd.context.channel, `[NEW TASK] Published: ${payload.title} | $${payload.bounty_usdc} USDC | /claim ${taskId}`);
    logger.info({ nick: cmd.context.nick, taskId }, "Task published via wizard");
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Publish failed";
    send(cmd.context.channel, `${cmd.context.nick}: Error: ${detail}`);
  }
}

// ─── Status Commands ─────────────────────────────────────────────

async function handleMyTasks(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  try {
    const data = await apiClient.get<any>("/api/v1/tasks", {
      params: { agent_wallet: wallet, limit: "5" },
    });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      send(cmd.context.channel, `${cmd.context.nick}: No tasks found.`);
      return;
    }

    send(cmd.context.channel, `Your tasks (${tasks.length}):`);
    for (const t of tasks) {
      const bounty = parseFloat(String(t.bounty_usdc ?? t.bounty ?? 0)).toFixed(2);
      send(cmd.context.channel, `  ${t.id.slice(0, 8)} | ${t.status} | $${bounty} | ${t.title?.slice(0, 50)}`);
    }
  } catch {
    send(cmd.context.channel, `${cmd.context.nick}: Error fetching tasks.`);
  }
}

async function handleMyClaims(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  try {
    const data = await apiClient.get<any>("/api/v1/tasks", {
      params: { executor_wallet: wallet, limit: "5" },
    });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      send(cmd.context.channel, `${cmd.context.nick}: No active claims.`);
      return;
    }

    send(cmd.context.channel, `Your claims (${tasks.length}):`);
    for (const t of tasks) {
      const bounty = parseFloat(String(t.bounty_usdc ?? t.bounty ?? 0)).toFixed(2);
      send(cmd.context.channel, `  ${t.id.slice(0, 8)} | ${t.status} | $${bounty} | ${t.title?.slice(0, 50)}`);
    }
  } catch {
    send(cmd.context.channel, `${cmd.context.nick}: Error fetching claims.`);
  }
}

// ─── Wizard Input Handler ────────────────────────────────────────

export async function handleWizardInput(
  channel: string,
  nick: string,
  text: string,
  send: SendFn,
): Promise<boolean> {
  const session = getWizardSession(nick);
  if (!session || session.channel !== channel) return false;

  if (text.trim().toLowerCase() === "/cancel") {
    cancelWizard(nick);
    send(channel, `${nick}: Wizard cancelled.`);
    return true;
  }

  const result = advanceWizard(nick, text);

  if (result.done) {
    // Wizard complete — publish the task
    const wallet = await identityStore.getWalletByNick(nick);
    const data = getWizardData(nick) || session.data;

    if (!wallet) {
      send(channel, `${nick}: Wallet not linked. Run /link first.`);
      cancelWizard(nick);
      return true;
    }

    cancelWizard(nick);

    try {
      const payload = {
        title: data.title,
        category: data.category || "simple_action",
        bounty_usdc: data.bounty_usdc || 0.10,
        deadline_minutes: data.deadline_minutes || 15,
        payment_network: "base",
        agent_wallet: wallet,
      };

      const res = await apiClient.post<any>("/api/v1/tasks", payload);
      const taskId = res?.id?.slice(0, 8) ?? "?";
      send(channel, `[NEW TASK] Published: ${payload.title} | $${payload.bounty_usdc} USDC | /claim ${taskId}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Publish failed";
      send(channel, `${nick}: Error: ${detail}`);
    }
    return true;
  }

  if (result.prompt) {
    send(channel, `${nick}: ${result.prompt}`);
  }
  return true;
}

// ─── Command Registry ────────────────────────────────────────────

export const taskCommands: CommandDefinition[] = [
  {
    name: "search",
    aliases: ["find"],
    description: "Search tasks by keyword",
    usage: "/search <query>",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "discovery",
    channelScoped: false,
    handler: handleSearch,
  },
  {
    name: "details",
    aliases: ["info", "detail"],
    description: "Get detailed task info",
    usage: "/details <task_id>",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "discovery",
    channelScoped: true,
    handler: handleDetails,
  },
  {
    name: "unclaim",
    aliases: [],
    description: "Withdraw from a claimed task",
    usage: "/unclaim <task_id>",
    minTrustLevel: TrustLevel.LINKED,
    category: "task_ops",
    channelScoped: true,
    handler: handleUnclaim,
  },
  {
    name: "extend",
    aliases: [],
    description: "Extend task deadline",
    usage: "/extend <task_id> <minutes>",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "task_ops",
    channelScoped: true,
    handler: handleExtend,
  },
  {
    name: "publish",
    aliases: ["pub"],
    description: "Publish a new task",
    usage: '/publish or /publish {"title":"...","bounty_usdc":0.10}',
    minTrustLevel: TrustLevel.VERIFIED,
    category: "publisher",
    channelScoped: false,
    handler: handlePublish,
  },
  {
    name: "confirm",
    aliases: [],
    description: "Confirm wizard action",
    usage: "/confirm",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "publisher",
    channelScoped: false,
    handler: handleConfirm,
  },
  {
    name: "my-tasks",
    aliases: ["mytasks"],
    description: "List your published tasks",
    usage: "/my-tasks",
    minTrustLevel: TrustLevel.LINKED,
    category: "discovery",
    channelScoped: false,
    handler: handleMyTasks,
  },
  {
    name: "my-claims",
    aliases: ["myclaims"],
    description: "List your claimed tasks",
    usage: "/my-claims",
    minTrustLevel: TrustLevel.LINKED,
    category: "discovery",
    channelScoped: false,
    handler: handleMyClaims,
  },
];
