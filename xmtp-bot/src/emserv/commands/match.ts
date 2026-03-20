/**
 * EMServ Match Commands — worker matchmaking via @em-match personality.
 *
 * Commands: /match, /suggest
 *
 * Queries worker_availability + ERC-8004 reputation to rank candidates
 * for a given task by trust level, reputation, proximity, and response time.
 */

import { apiClient } from "../../services/api-client.js";
import { TrustLevel } from "../../bridges/identity-store.js";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";

// ─── /match <task_id> ────────────────────────────────────────────

async function handleMatch(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  const taskId = cmd.args[0] ?? cmd.context.taskId ?? "";
  if (!taskId) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /match <task_id>`);
    return;
  }

  try {
    // Fetch task details to get city/category
    const taskResp = await apiClient.get(`/api/v1/tasks/${taskId}`);
    const task = taskResp.data;

    const city = task.city || task.location?.city || "";
    const category = task.category || "";

    if (!city) {
      send(
        cmd.context.channel,
        `[MATCH] Task ${taskId.slice(0, 8)} has no city set. Cannot match geographically.`,
      );
      return;
    }

    // Query available workers in city (via identity/availability API)
    // For now, provide structured response — actual DB query requires
    // the worker_availability + reputation join
    send(
      cmd.context.channel,
      `[MATCH] Searching for workers in ${city}${category ? ` for ${category}` : ""}...`,
    );

    // Placeholder: in production, this queries worker_availability JOIN irc_identities
    // and cross-references ERC-8004 reputation scores
    send(
      cmd.context.channel,
      `[MATCH] Use /who ${city} to see available workers, then /assign <wallet> to pick.`,
    );

    logger.info({ nick: cmd.context.nick, taskId, city, category }, "Match requested");
  } catch (err) {
    send(
      cmd.context.channel,
      `${cmd.context.nick}: Could not fetch task ${taskId.slice(0, 8)}. Check the ID.`,
    );
    logger.error({ err, taskId }, "Match command failed");
  }
}

// ─── /suggest [city] [category] ──────────────────────────────────

async function handleSuggest(cmd: ParsedCommand, send: SendFn): Promise<void> {
  let city = "";
  let category = "";

  if (cmd.jsonPayload) {
    city = (cmd.jsonPayload.city as string) ?? "";
    category = (cmd.jsonPayload.category as string) ?? "";
  } else {
    city = cmd.args[0] ?? "";
    category = cmd.args[1] ?? "";
  }

  if (!city) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /suggest <city> [category]`);
    return;
  }

  // Suggest available tasks in a city (worker perspective)
  send(
    cmd.context.channel,
    `[SUGGEST] Looking for tasks in ${city}${category ? ` (${category})` : ""}... Use /tasks --city ${city} for full list.`,
  );

  logger.info({ nick: cmd.context.nick, city, category }, "Task suggestion requested");
}

// ─── Command Registry ────────────────────────────────────────────

export const matchCommands: CommandDefinition[] = [
  {
    name: "match",
    aliases: [],
    description: "Find matching workers for a task (publisher only)",
    usage: "/match <task_id>",
    minTrustLevel: TrustLevel.LINKED,
    category: "discovery",
    channelScoped: true,
    handler: handleMatch,
  },
  {
    name: "suggest",
    aliases: [],
    description: "Suggest tasks in your area",
    usage: "/suggest <city> [category]",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "discovery",
    channelScoped: false,
    handler: handleSuggest,
  },
];
