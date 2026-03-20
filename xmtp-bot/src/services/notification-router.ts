/**
 * Notification Router — priority-based cross-protocol notification delivery.
 *
 * Routes notifications to users based on event priority and user preference:
 * - CRITICAL: push to ALL channels (IRC + XMTP)
 * - IMPORTANT: push to preferred channel only
 * - INFO: push to subscribed channels only
 *
 * User preference stored in irc_identities.metadata.preferred_channel.
 */

import { identityStore } from "../bridges/identity-store.js";
import { logger } from "../utils/logger.js";

// ─── Priority Levels ─────────────────────────────────────────────

export type NotificationPriority = "critical" | "important" | "info";
export type ChannelPreference = "irc" | "xmtp" | "both";

/**
 * Event → priority mapping.
 * Critical events go to ALL channels regardless of preference.
 */
const EVENT_PRIORITIES: Record<string, NotificationPriority> = {
  "payment.released": "critical",
  "task.assigned": "critical",
  "dispute.opened": "critical",
  "submission.received": "important",
  "submission.approved": "important",
  "submission.rejected": "important",
  "bid.received": "important",
  "task.created": "info",
  "availability.match": "info",
  "task.cancelled": "important",
  "task.completed": "important",
};

// ─── Notification Targets ────────────────────────────────────────

interface NotificationTarget {
  wallet: string;
  channels: ChannelPreference[];
}

type IrcNotifyFn = (nick: string, message: string) => void;
type XmtpNotifyFn = (address: string, message: string) => Promise<void>;

// ─── Router ──────────────────────────────────────────────────────

let ircNotify: IrcNotifyFn | null = null;
let xmtpNotify: XmtpNotifyFn | null = null;

export function setNotificationHandlers(
  irc: IrcNotifyFn,
  xmtp: XmtpNotifyFn,
): void {
  ircNotify = irc;
  xmtpNotify = xmtp;
}

/**
 * Route a notification to the appropriate channels based on event type
 * and user preference.
 */
export async function routeNotification(
  eventType: string,
  walletAddress: string,
  message: string,
): Promise<{ sent: string[] }> {
  const priority = EVENT_PRIORITIES[eventType] ?? "info";
  const sent: string[] = [];

  // Get user preference
  const identity = await identityStore.getIdentity(walletAddress);
  const preference: ChannelPreference =
    (identity?.metadata?.preferred_channel as ChannelPreference) ?? "both";

  const shouldSendIrc = shouldNotify(priority, preference, "irc");
  const shouldSendXmtp = shouldNotify(priority, preference, "xmtp");

  if (shouldSendIrc && ircNotify && identity?.irc_nick) {
    try {
      ircNotify(identity.irc_nick, message);
      sent.push("irc");
    } catch (err) {
      logger.error({ err, wallet: walletAddress.slice(0, 10) }, "IRC notification failed");
    }
  }

  if (shouldSendXmtp && xmtpNotify) {
    try {
      await xmtpNotify(walletAddress, message);
      sent.push("xmtp");
    } catch (err) {
      logger.error({ err, wallet: walletAddress.slice(0, 10) }, "XMTP notification failed");
    }
  }

  logger.debug(
    { eventType, priority, preference, sent },
    "Notification routed",
  );

  return { sent };
}

/**
 * Determine if a notification should be sent to a specific channel
 * based on priority and user preference.
 */
function shouldNotify(
  priority: NotificationPriority,
  preference: ChannelPreference,
  channel: "irc" | "xmtp",
): boolean {
  // Critical: ALWAYS send to all channels
  if (priority === "critical") return true;

  // Important: send to preferred channel(s)
  if (priority === "important") {
    if (preference === "both") return true;
    return preference === channel;
  }

  // Info: only send to preferred channel(s)
  if (preference === "both") return true;
  return preference === channel;
}

/**
 * Get the priority level for an event type.
 */
export function getEventPriority(eventType: string): NotificationPriority {
  return EVENT_PRIORITIES[eventType] ?? "info";
}
