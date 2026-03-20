/**
 * EMServ Identity Commands — wallet linking, verification, ERC-8004 binding.
 *
 * Migrated from legacy handlers in meshrelay.ts.
 */

import { apiClient } from "../../services/api-client.js";
import { identityStore, TrustLevel } from "../../bridges/identity-store.js";
import { linkNickToWallet, isValidEthAddress } from "../../bridges/identity-map.js";
import { trustBadge } from "../../bridges/formatters.js";
import { verifyMessage } from "viem";
import { randomBytes } from "crypto";
import { logger } from "../../utils/logger.js";
import type { ParsedCommand, SendFn, CommandDefinition } from "../types.js";

// ─── /link <wallet_address> ─────────────────────────────────────

async function handleLink(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const address = cmd.args[0];

  if (!address || !isValidEthAddress(address)) {
    send(cmd.context.channel, `${cmd.context.nick}: Invalid address. Usage: /link 0x1234...abcd (40 hex chars)`);
    return;
  }

  linkNickToWallet(cmd.context.nick, address);
  const short = `${address.slice(0, 6)}...${address.slice(-4)}`;
  send(cmd.context.channel, `${cmd.context.nick}: Wallet linked: ${short} (L1). You can now /claim tasks. Run /verify for L2.`);
}

// ─── /verify (initiate challenge-response) ─────────────────────

async function handleVerify(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const wallet = await identityStore.getWalletByNick(cmd.context.nick);
  if (!wallet) {
    send(cmd.context.channel, `${cmd.context.nick}: Link your wallet first: /link <address>`);
    return;
  }

  const trustLevel = await identityStore.getTrustLevel(cmd.context.nick);
  if (trustLevel >= TrustLevel.VERIFIED) {
    send(cmd.context.channel, `${cmd.context.nick}: Already verified ${trustBadge(trustLevel)}`);
    return;
  }

  const nonce = randomBytes(16).toString("hex");
  const timestamp = Math.floor(Date.now() / 1000);
  await identityStore.storeChallenge(cmd.context.nick, nonce, 5);

  const message = `EM-VERIFY:${nonce}:${cmd.context.nick.toLowerCase()}:${timestamp}`;
  send(
    cmd.context.channel,
    `${cmd.context.nick}: Sign this message with your wallet: "${message}" — then /verify-sig <signature> (5 min TTL)`,
  );
  logger.info({ nick: cmd.context.nick }, "Verification challenge issued");
}

// ─── /verify-sig <signature> (complete challenge) ──────────────

async function handleVerifySig(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const signature = cmd.args[0];
  const nick = cmd.context.nick;

  if (!signature || !signature.startsWith("0x")) {
    send(cmd.context.channel, `${nick}: Usage: /verify-sig 0x<signature>`);
    return;
  }

  const challenge = await identityStore.getChallenge(nick);
  if (!challenge) {
    send(cmd.context.channel, `${nick}: No pending challenge. Run /verify first.`);
    return;
  }

  if (new Date(challenge.expiresAt) < new Date()) {
    await identityStore.clearChallenge(nick);
    send(cmd.context.channel, `${nick}: Challenge expired. Run /verify again.`);
    return;
  }

  const message = `EM-VERIFY:${challenge.nonce}:${nick.toLowerCase()}:`;

  try {
    const isValid = await verifyMessage({
      address: challenge.wallet as `0x${string}`,
      message: { raw: Buffer.from(message) as any },
      signature: signature as `0x${string}`,
    }).catch(() => false);

    let verified = isValid;
    if (!verified) {
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
      send(cmd.context.channel, `${nick}[V]: Wallet ${short} verified! Trust level: VERIFIED.`);
      logger.info({ nick, wallet: challenge.wallet.slice(0, 10) }, "Identity verified via signature");
    } else {
      send(cmd.context.channel, `${nick}: Signature does not match linked wallet. Try again.`);
      logger.warn({ nick }, "Verification signature mismatch");
    }
  } catch (err) {
    send(cmd.context.channel, `${nick}: Verification error. Check signature format.`);
    logger.error({ err, nick }, "Verification failed");
  }
}

// ─── /register (ERC-8004 binding) ──────────────────────────────

async function handleRegister(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const trustLevel = await identityStore.getTrustLevel(nick);

  if (trustLevel >= TrustLevel.REGISTERED) {
    send(cmd.context.channel, `${nick}[R]: Already registered with ERC-8004.`);
    return;
  }

  const wallet = await identityStore.getWalletByNick(nick);
  if (!wallet) {
    send(cmd.context.channel, `${nick}: No wallet linked. Run /link first.`);
    return;
  }

  try {
    const data = await apiClient.get<any>("/api/v1/reputation/lookup", {
      params: { wallet },
    });

    if (data?.agent_id) {
      await identityStore.setAgentId(nick, data.agent_id);
      send(
        cmd.context.channel,
        `${nick}[R]: ERC-8004 Agent #${data.agent_id} bound! Trust level: REGISTERED. Full marketplace access.`,
      );
      logger.info({ nick, agentId: data.agent_id }, "ERC-8004 identity bound");
    } else {
      send(
        cmd.context.channel,
        `${nick}: No ERC-8004 agent found for your wallet. Register at execution.market/register or via /em-register-identity.`,
      );
    }
  } catch (err: any) {
    const status = err?.response?.status;
    if (status === 404) {
      send(cmd.context.channel, `${nick}: No ERC-8004 agent found. Register at execution.market/register.`);
    } else {
      send(cmd.context.channel, `${nick}: Error checking registration. Try again later.`);
      logger.error({ err, nick }, "ERC-8004 lookup failed");
    }
  }
}

// ─── /whoami (identity info) ───────────────────────────────────

async function handleWhoami(cmd: ParsedCommand, send: SendFn): Promise<void> {
  const nick = cmd.context.nick;
  const identity = await identityStore.getIdentity(nick);

  if (!identity) {
    send(cmd.context.channel, `${nick}: No identity found. Run /link <wallet> to get started.`);
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

  send(cmd.context.channel, lines.join("\n"));
}

// ─── Command Definitions ───────────────────────────────────────

export const identityCommands: CommandDefinition[] = [
  {
    name: "link",
    aliases: [],
    description: "Link IRC nick to wallet address",
    usage: "/link <0x_wallet_address>",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "identity",
    channelScoped: false,
    handler: handleLink,
  },
  {
    name: "verify",
    aliases: [],
    description: "Start wallet verification (L1 -> L2)",
    usage: "/verify",
    minTrustLevel: TrustLevel.LINKED,
    category: "identity",
    channelScoped: false,
    handler: handleVerify,
  },
  {
    name: "verify-sig",
    aliases: ["verifysig"],
    description: "Complete verification with signature",
    usage: "/verify-sig 0x<signature>",
    minTrustLevel: TrustLevel.LINKED,
    category: "identity",
    channelScoped: false,
    handler: handleVerifySig,
  },
  {
    name: "register",
    aliases: [],
    description: "Bind ERC-8004 identity (L2 -> L3)",
    usage: "/register",
    minTrustLevel: TrustLevel.VERIFIED,
    category: "identity",
    channelScoped: false,
    handler: handleRegister,
  },
  {
    name: "whoami",
    aliases: ["me", "identity"],
    description: "Show identity info and trust level",
    usage: "/whoami",
    minTrustLevel: TrustLevel.ANONYMOUS,
    category: "identity",
    channelScoped: false,
    handler: handleWhoami,
  },
];
