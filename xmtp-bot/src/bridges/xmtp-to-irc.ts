/**
 * XMTP ↔ IRC Bridge — bidirectional message relay.
 *
 * - XMTP group message → forwarded to #task-{id} on IRC as "<XMTP:nick> message"
 * - IRC #task-{id} message → forwarded to XMTP group as "<IRC:nick> message"
 *
 * Rate limited: 1 msg/sec per user across bridge to prevent loops.
 * Only bridges task-related channels (not #bounties, not DMs).
 */

import { identityStore } from "./identity-store.js";
import { logger } from "../utils/logger.js";
import { getTaskGroup } from "../services/group-manager.js";

// Rate limiter: 1 msg/sec per user
const lastSent = new Map<string, number>();
const RATE_LIMIT_MS = 1000;

function isRateLimited(userId: string): boolean {
  const now = Date.now();
  const last = lastSent.get(userId) ?? 0;
  if (now - last < RATE_LIMIT_MS) return true;
  lastSent.set(userId, now);
  return false;
}

// ─── Types ───────────────────────────────────────────────────────

type IrcSendFn = (channel: string, message: string) => void;
type XmtpSendFn = (groupId: string, message: string) => Promise<void>;

// Channel ↔ Group mapping
const channelToGroup = new Map<string, string>(); // #task-abc → groupId
const groupToChannel = new Map<string, string>(); // groupId → #task-abc

// ─── Bridge Setup ────────────────────────────────────────────────

/**
 * Register a mapping between an IRC task channel and an XMTP group.
 */
export function linkChannelToGroup(channel: string, groupId: string): void {
  channelToGroup.set(channel, groupId);
  groupToChannel.set(groupId, channel);
  logger.info({ channel, groupId }, "Linked IRC channel to XMTP group");
}

/**
 * Remove mapping when channel/group is closed.
 */
export function unlinkChannel(channel: string): void {
  const groupId = channelToGroup.get(channel);
  if (groupId) {
    groupToChannel.delete(groupId);
  }
  channelToGroup.delete(channel);
}

// ─── XMTP → IRC ─────────────────────────────────────────────────

/**
 * Forward an XMTP group message to the linked IRC task channel.
 * Called by the XMTP message handler when a group message arrives.
 */
export function forwardXmtpToIrc(
  groupId: string,
  senderAddress: string,
  messageText: string,
  ircSend: IrcSendFn,
): boolean {
  const channel = groupToChannel.get(groupId);
  if (!channel) return false;

  // Only bridge task channels
  if (!channel.startsWith("#task-")) return false;

  if (isRateLimited(`xmtp:${senderAddress}`)) {
    logger.debug("Rate limited XMTP→IRC for %s", senderAddress.slice(0, 10));
    return false;
  }

  // Resolve nick from wallet
  const nick = identityStore.getNickByWalletSync?.(senderAddress) || senderAddress.slice(0, 10);

  ircSend(channel, `<XMTP:${nick}> ${messageText}`);
  logger.debug({ channel, nick, direction: "xmtp→irc" }, "Bridged message");
  return true;
}

// ─── IRC → XMTP ─────────────────────────────────────────────────

/**
 * Forward an IRC task channel message to the linked XMTP group.
 * Called by the IRC message handler for #task-* channels.
 */
export async function forwardIrcToXmtp(
  channel: string,
  nick: string,
  messageText: string,
  xmtpSend: XmtpSendFn,
): Promise<boolean> {
  const groupId = channelToGroup.get(channel);
  if (!groupId) return false;

  // Only bridge task channels
  if (!channel.startsWith("#task-")) return false;

  // Don't re-bridge messages that came from XMTP (prevent loops)
  if (messageText.startsWith("<XMTP:")) return false;

  if (isRateLimited(`irc:${nick}`)) {
    logger.debug("Rate limited IRC→XMTP for %s", nick);
    return false;
  }

  try {
    await xmtpSend(groupId, `<IRC:${nick}> ${messageText}`);
    logger.debug({ channel, nick, direction: "irc→xmtp" }, "Bridged message");
    return true;
  } catch (err) {
    logger.error({ err, channel, nick }, "Failed to bridge IRC→XMTP");
    return false;
  }
}

// ─── Stats ───────────────────────────────────────────────────────

export function getBridgeStats(): {
  linkedChannels: number;
  rateLimitEntries: number;
} {
  return {
    linkedChannels: channelToGroup.size,
    rateLimitEntries: lastSent.size,
  };
}
