/**
 * EMServ — Execution Market IRC Service.
 *
 * Command registry with dual-parse parser, personality routing,
 * wire format output, and wizard state machine.
 *
 * Entry point: handleCommand() — replaces inline if/else in meshrelay.ts
 */

import { parseCommand, getTaskIdFromChannel } from "./parser.js";
import { routeToPersonality, formatWithPersonality } from "./personalities.js";
import { taskCommands, handleWizardInput } from "./commands/tasks.js";
import { discoveryCommands } from "./commands/discovery.js";
import { auctionCommands } from "./commands/auction.js";
import { matchCommands } from "./commands/match.js";
import { getWizardSession } from "./wizard-state.js";
import { setOutputFormat, getOutputFormat } from "./wire.js";
import { identityStore, TrustLevel } from "../bridges/identity-store.js";
import { logger } from "../utils/logger.js";
import type { CommandDefinition, SendFn, CommandContext } from "./types.js";

// ─── Command Registry ────────────────────────────────────────────

const registry = new Map<string, CommandDefinition>();

function registerCommand(def: CommandDefinition): void {
  registry.set(def.name, def);
  for (const alias of def.aliases) {
    registry.set(alias, def);
  }
}

// Register all command modules
for (const cmd of taskCommands) {
  registerCommand(cmd);
}
for (const cmd of discoveryCommands) {
  registerCommand(cmd);
}
for (const cmd of auctionCommands) {
  registerCommand(cmd);
}
for (const cmd of matchCommands) {
  registerCommand(cmd);
}

// Built-in /format command
registerCommand({
  name: "format",
  aliases: [],
  description: "Set output format (human or json)",
  usage: "/format <human|json>",
  minTrustLevel: TrustLevel.ANONYMOUS,
  category: "system",
  channelScoped: false,
  handler: async (cmd, send) => {
    const format = cmd.args[0]?.toLowerCase();
    if (format === "json" || format === "human") {
      setOutputFormat(cmd.context.nick, format);
      send(cmd.context.channel, `${cmd.context.nick}: Output format set to ${format}.`);
    } else {
      const current = getOutputFormat(cmd.context.nick);
      send(cmd.context.channel, `${cmd.context.nick}: Current format: ${current}. Usage: /format <human|json>`);
    }
  },
});

// ─── Main Handler ────────────────────────────────────────────────

/**
 * Handle an EMServ command from IRC.
 * Returns true if handled, false if the command should fall through
 * to legacy handlers in meshrelay.ts.
 */
export async function handleCommand(
  channel: string,
  nick: string,
  text: string,
  send: SendFn,
): Promise<boolean> {
  const trimmed = text.trim();

  // Check for active wizard first (wizard captures all input)
  if (getWizardSession(nick)) {
    return handleWizardInput(channel, nick, trimmed, send);
  }

  if (!trimmed.startsWith("/")) return false;

  // Build context
  const taskId = getTaskIdFromChannel(channel) ?? undefined;
  const trustLevel = await identityStore.getTrustLevel(nick);
  const walletAddress = (await identityStore.getWalletByNick(nick)) ?? undefined;

  const context: CommandContext = {
    channel,
    nick,
    taskId,
    trustLevel,
    walletAddress,
  };

  const parsed = parseCommand(trimmed, context);
  if (!parsed) return false;

  // Look up in registry
  const def = registry.get(parsed.command);
  if (!def) return false; // Unknown to EMServ — fall through to legacy

  // Trust level check
  if (trustLevel < def.minTrustLevel) {
    const levelNames = ["ANONYMOUS", "LINKED", "VERIFIED", "REGISTERED"];
    send(
      channel,
      `${nick}: /${parsed.command} requires ${levelNames[def.minTrustLevel]} (L${def.minTrustLevel}).`,
    );
    return true;
  }

  // Channel-scoped task ID injection
  if (def.channelScoped && taskId && parsed.args.length === 0 && !parsed.jsonPayload) {
    parsed.args.unshift(taskId);
  }

  // Route to personality
  const personality = routeToPersonality(parsed.command);

  // Execute with personality-formatted output
  const personalSend: SendFn = (ch, msg) => {
    send(ch, formatWithPersonality(personality, msg));
  };

  try {
    await def.handler(parsed, personalSend);
  } catch (err) {
    logger.error({ err, command: parsed.command, nick }, "EMServ command failed");
    send(channel, `${nick}: Internal error processing /${parsed.command}.`);
  }

  return true;
}

/**
 * Get all registered commands for /help display.
 */
export function getRegisteredCommands(): CommandDefinition[] {
  const seen = new Set<string>();
  const commands: CommandDefinition[] = [];

  for (const [name, def] of registry) {
    if (!seen.has(def.name)) {
      seen.add(def.name);
      commands.push(def);
    }
  }

  return commands.sort((a, b) => a.name.localeCompare(b.name));
}

export { parseCommand, getTaskIdFromChannel } from "./parser.js";
export { routeToPersonality } from "./personalities.js";
export { formatTaskEvent, formatChannelAnnouncement, WIRE_PATTERNS, setOutputFormat, getOutputFormat } from "./wire.js";
export type { ParsedCommand, CommandDefinition, CommandContext } from "./types.js";
