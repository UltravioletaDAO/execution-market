/**
 * EMServ Relay Commands — multi-worker chained execution handoff protocol.
 *
 * Commands: /relay-status, /handoff, /confirm-handoff
 *
 * Workers in a relay chain use handoff codes (QR/manual) to verify
 * physical package transfers. Each handoff completes a leg and releases
 * payment for that segment.
 */

import { apiClient } from "../../services/api-client.js";
import { TrustLevel } from "../../bridges/identity-store.js";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";

// ─── /relay-status [chain_id] ────────────────────────────────────

async function handleRelayStatus(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const chainId = cmd.args[0] ?? "";

  if (!chainId) {
    send(cmd.context.channel, `${cmd.context.nick}: Usage: /relay-status <chain_id>`);
    return;
  }

  try {
    const resp = await apiClient.get(`/api/v1/relay-chains/${chainId}`);
    const chain = resp.data;

    const legLines = chain.legs.map((leg: any) => {
      const worker = leg.worker_nick || leg.worker_wallet?.slice(0, 10) || "unassigned";
      const statusIcon =
        leg.status === "completed" || leg.status === "handed_off"
          ? "[done]"
          : leg.status === "in_transit"
            ? "[transit]"
            : leg.status === "assigned"
              ? "[ready]"
              : "[waiting]";
      return `  Leg ${leg.leg_number}: ${statusIcon} ${worker} | $${parseFloat(leg.bounty_usdc).toFixed(2)}`;
    });

    send(
      cmd.context.channel,
      `[RELAY] Chain ${chainId.slice(0, 8)} — ${chain.completed_legs}/${chain.total_legs} legs complete (${chain.status})\n${legLines.join("\n")}`,
    );
  } catch {
    send(cmd.context.channel, `${cmd.context.nick}: Could not fetch relay chain ${chainId.slice(0, 8)}.`);
  }
}

// ─── /handoff <leg_number> ───────────────────────────────────────

async function handleHandoff(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  let chainId = "";
  let legNumber = 0;

  if (cmd.jsonPayload) {
    chainId = (cmd.jsonPayload.chain_id as string) ?? "";
    legNumber = (cmd.jsonPayload.leg_number as number) ?? 0;
  } else {
    chainId = cmd.args[0] ?? "";
    legNumber = parseInt(cmd.args[1] ?? "0", 10);
  }

  if (!chainId || !legNumber) {
    send(
      cmd.context.channel,
      `${cmd.context.nick}: Usage: /handoff <chain_id> <leg_number>`,
    );
    return;
  }

  // Fetch the leg to show the handoff code to the outgoing worker
  try {
    const resp = await apiClient.get(`/api/v1/relay-chains/${chainId}`);
    const chain = resp.data;
    const leg = chain.legs.find((l: any) => l.leg_number === legNumber);

    if (!leg) {
      send(cmd.context.channel, `${cmd.context.nick}: Leg ${legNumber} not found.`);
      return;
    }

    if (leg.handoff_code) {
      // Send handoff code privately (in production, via DM)
      send(
        cmd.context.channel,
        `[HANDOFF] ${cmd.context.nick} initiating handoff for Leg ${legNumber}. ` +
          `Next worker: use /confirm-handoff ${chainId.slice(0, 8)} ${legNumber} <code> to confirm receipt.`,
      );
    }
  } catch {
    send(cmd.context.channel, `${cmd.context.nick}: Could not initiate handoff.`);
  }

  logger.info({ nick: cmd.context.nick, chainId, legNumber }, "Handoff initiated");
}

// ─── /confirm-handoff <chain_id> <leg_number> <code> ─────────────

async function handleConfirmHandoff(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = cmd.context.walletAddress;
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  let chainId = "";
  let legNumber = 0;
  let code = "";

  if (cmd.jsonPayload) {
    chainId = (cmd.jsonPayload.chain_id as string) ?? "";
    legNumber = (cmd.jsonPayload.leg_number as number) ?? 0;
    code = (cmd.jsonPayload.code as string) ?? "";
  } else {
    chainId = cmd.args[0] ?? "";
    legNumber = parseInt(cmd.args[1] ?? "0", 10);
    code = cmd.args[2] ?? "";
  }

  if (!chainId || !legNumber || !code) {
    send(
      cmd.context.channel,
      `${cmd.context.nick}: Usage: /confirm-handoff <chain_id> <leg_number> <code>`,
    );
    return;
  }

  try {
    const resp = await apiClient.post(
      `/api/v1/relay-chains/${chainId}/legs/${legNumber}/handoff`,
      { handoff_code: code },
    );
    const result = resp.data;

    send(
      cmd.context.channel,
      `[HANDOFF] Leg ${legNumber} confirmed by ${cmd.context.nick}. ` +
        `Chain progress: ${result.completed_legs}/${result.total_legs}. ` +
        `${result.chain_status === "completed" ? "All legs complete!" : "Next leg ready."}`,
    );
  } catch (err: any) {
    const msg = err?.response?.data?.detail || "Handoff verification failed";
    send(cmd.context.channel, `${cmd.context.nick}: ${msg}`);
  }

  logger.info({ nick: cmd.context.nick, chainId, legNumber }, "Handoff confirmed");
}

// ─── Command Registry ────────────────────────────────────────────

export const relayCommands: CommandDefinition[] = [
  {
    name: "relay-status",
    aliases: ["relay"],
    description: "Show relay chain progress",
    usage: "/relay-status <chain_id>",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "relay",
    channelScoped: false,
    handler: handleRelayStatus,
  },
  {
    name: "handoff",
    aliases: [],
    description: "Initiate handoff to next worker",
    usage: "/handoff <chain_id> <leg_number>",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "relay",
    channelScoped: false,
    handler: handleHandoff,
  },
  {
    name: "confirm-handoff",
    aliases: ["confirm-relay"],
    description: "Confirm receipt with handoff code",
    usage: "/confirm-handoff <chain_id> <leg_number> <code>",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "relay",
    channelScoped: false,
    handler: handleConfirmHandoff,
  },
];
