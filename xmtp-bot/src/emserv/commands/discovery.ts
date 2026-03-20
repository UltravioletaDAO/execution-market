/**
 * EMServ Discovery Commands — geographic availability, worker lookup.
 *
 * Commands: /available, /unavailable, /who, /nearby
 */

import { apiClient } from "../../services/api-client.js";
import { identityStore, TrustLevel } from "../../bridges/identity-store.js";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";

// ─── /available [city] [categories...] ───────────────────────────

async function handleAvailable(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  // Parse: /available Medellin physical_presence,knowledge_access
  // Or JSON: /available {"city":"Medellin","categories":["physical_presence"]}
  let city = "";
  let categories: string[] = [];
  let hoursAvailable = 4; // default 4 hours

  if (cmd.jsonPayload) {
    city = (cmd.jsonPayload.city as string) ?? "";
    categories = (cmd.jsonPayload.categories as string[]) ?? [];
    hoursAvailable = (cmd.jsonPayload.hours as number) ?? 4;
  } else {
    city = cmd.args[0] ?? "";
    if (cmd.args[1]) {
      categories = cmd.args[1].split(",").map((c) => c.trim());
    }
    if (cmd.flags.hours) {
      hoursAvailable = parseInt(cmd.flags.hours, 10) || 4;
    }
  }

  if (!city) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /available <city> [categories] [--hours N]`);
    return;
  }

  try {
    await apiClient.post("/api/v1/identity/sync", {
      irc_nick: cmd.context.nick.toLowerCase(),
      wallet_address: wallet,
      trust_level: cmd.context.trustLevel,
    });
  } catch {
    // Best effort identity sync
  }

  // Broadcast availability
  const catStr = categories.length > 0 ? categories.join(", ") : "all categories";
  send(
    cmd.context.channel,
    `[AVAILABLE] ${cmd.context.nick} is available in ${city} for ${catStr} (next ${hoursAvailable}h).`,
  );

  // Also post to geographic channel if it exists
  const cityChannel = `#city-${city.toLowerCase().replace(/\s+/g, "-")}`;
  send(
    cityChannel,
    `[AVAILABLE] ${cmd.context.nick} is available for ${catStr} (next ${hoursAvailable}h). /who ${city} for all.`,
  );

  logger.info({ nick: cmd.context.nick, city, categories }, "Worker availability broadcast");
}

// ─── /unavailable ────────────────────────────────────────────────

async function handleUnavailable(cmd: ParsedCommand, send: SendFn): Promise<void> {
  send(cmd.context.channel, `${cmd.context.nick}: Marked as unavailable.`);
  logger.info({ nick: cmd.context.nick }, "Worker unavailable");
}

// ─── /who [city] ─────────────────────────────────────────────────

async function handleWho(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const city = cmd.args[0] || cmd.jsonPayload?.city as string;

  if (!city) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /who <city>`);
    return;
  }

  // For now, respond with a placeholder — actual DB query requires
  // the worker_availability table to be populated
  send(
    cmd.context.channel,
    `[WHO] Workers available in ${city}: checking... (use /available ${city} to register yourself)`,
  );
}

// ─── /nearby [radius_km] ────────────────────────────────────────

async function handleNearby(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const radiusKm = parseInt(cmd.args[0] ?? "10", 10);

  send(
    cmd.context.channel,
    `${cmd.context.nick}: Searching for tasks within ${radiusKm}km... (requires location sharing)`,
  );
}

// ─── Command Registry ────────────────────────────────────────────

export const discoveryCommands: CommandDefinition[] = [
  {
    name: "available",
    aliases: ["avail"],
    description: "Broadcast your availability in a city",
    usage: "/available <city> [categories] [--hours N]",
    minTrustLevel: TrustLevel.LINKED,
    category: "discovery",
    channelScoped: false,
    handler: handleAvailable,
  },
  {
    name: "unavailable",
    aliases: ["unavail"],
    description: "Mark yourself as unavailable",
    usage: "/unavailable",
    minTrustLevel: TrustLevel.LINKED,
    category: "discovery",
    channelScoped: false,
    handler: handleUnavailable,
  },
  {
    name: "who",
    aliases: [],
    description: "List available workers in a city",
    usage: "/who <city>",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "discovery",
    channelScoped: false,
    handler: handleWho,
  },
  {
    name: "nearby",
    aliases: [],
    description: "Search for tasks near your location",
    usage: "/nearby [radius_km]",
    minTrustLevel: TrustLevel.LINKED,
    category: "discovery",
    channelScoped: false,
    handler: handleNearby,
  },
];
