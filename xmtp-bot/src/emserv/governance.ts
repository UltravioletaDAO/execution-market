/**
 * EMServ Channel Governance — moderation, flood detection, user reporting.
 *
 * - @em-bot is auto-op in #task-{id} channels
 * - Publisher gets half-op (+h) in their task channels
 * - Flood detection: auto-quiet users exceeding 5 msgs / 10 sec
 * - /report system with 3-strike temp ban (1 hour)
 */

import { logger } from "../utils/logger.js";

// ─── Flood Detection ─────────────────────────────────────────────

const FLOOD_THRESHOLD = 5; // messages
const FLOOD_WINDOW_MS = 10_000; // 10 seconds
const FLOOD_QUIET_DURATION_MS = 60_000; // 1 minute quiet

// Track message timestamps per nick per channel
const messageLog = new Map<string, number[]>();
const quietedUsers = new Map<string, number>(); // nick → quiet until timestamp

/**
 * Record a message and check for flood. Returns true if user should be quieted.
 */
export function checkFlood(channel: string, nick: string): boolean {
  // Don't flood-check bots
  if (nick.startsWith("em-")) return false;

  const key = `${channel}:${nick.toLowerCase()}`;
  const now = Date.now();

  // Check if already quieted
  const quietUntil = quietedUsers.get(nick.toLowerCase());
  if (quietUntil && now < quietUntil) return true;

  let timestamps = messageLog.get(key) ?? [];
  timestamps = timestamps.filter((t) => now - t < FLOOD_WINDOW_MS);
  timestamps.push(now);
  messageLog.set(key, timestamps);

  if (timestamps.length > FLOOD_THRESHOLD) {
    quietedUsers.set(nick.toLowerCase(), now + FLOOD_QUIET_DURATION_MS);
    logger.warn({ channel, nick, count: timestamps.length }, "Flood detected, user quieted");
    return true;
  }

  return false;
}

/**
 * Check if a user is currently quieted.
 */
export function isQuieted(nick: string): boolean {
  const quietUntil = quietedUsers.get(nick.toLowerCase());
  if (!quietUntil) return false;
  if (Date.now() >= quietUntil) {
    quietedUsers.delete(nick.toLowerCase());
    return false;
  }
  return true;
}

// ─── Report System ───────────────────────────────────────────────

const REPORT_BAN_THRESHOLD = 3;
const TEMP_BAN_DURATION_MS = 60 * 60 * 1000; // 1 hour

interface Report {
  reporter: string;
  reason: string;
  timestamp: number;
}

const reports = new Map<string, Report[]>(); // nick → reports
const bannedUsers = new Map<string, number>(); // nick → banned until

/**
 * Report a user. Returns true if user crossed the ban threshold.
 */
export function reportUser(
  targetNick: string,
  reporterNick: string,
  reason: string,
): { banned: boolean; totalReports: number } {
  const key = targetNick.toLowerCase();
  const existing = reports.get(key) ?? [];

  // Prevent duplicate reports from same reporter
  if (existing.some((r) => r.reporter === reporterNick.toLowerCase())) {
    return { banned: false, totalReports: existing.length };
  }

  existing.push({
    reporter: reporterNick.toLowerCase(),
    reason,
    timestamp: Date.now(),
  });
  reports.set(key, existing);

  if (existing.length >= REPORT_BAN_THRESHOLD) {
    bannedUsers.set(key, Date.now() + TEMP_BAN_DURATION_MS);
    logger.warn(
      { nick: targetNick, reports: existing.length },
      "User temp-banned after reports threshold",
    );
    return { banned: true, totalReports: existing.length };
  }

  return { banned: false, totalReports: existing.length };
}

/**
 * Check if a user is currently banned.
 */
export function isBanned(nick: string): boolean {
  const banUntil = bannedUsers.get(nick.toLowerCase());
  if (!banUntil) return false;
  if (Date.now() >= banUntil) {
    bannedUsers.delete(nick.toLowerCase());
    reports.delete(nick.toLowerCase()); // Clear reports after ban expires
    return false;
  }
  return true;
}

// ─── Channel Permissions ─────────────────────────────────────────

/**
 * Get the IRC mode string for a user in a task channel.
 * Returns the mode to set (e.g., "+h" for half-op).
 */
export function getChannelMode(
  nick: string,
  isPublisher: boolean,
  isBot: boolean,
): string | null {
  if (isBot) return "+o"; // Full operator for bots
  if (isPublisher) return "+h"; // Half-op for publishers
  return null; // Regular user
}

// ─── Stats ───────────────────────────────────────────────────────

export function getGovernanceStats(): {
  quietedUsers: number;
  bannedUsers: number;
  totalReports: number;
} {
  const now = Date.now();
  return {
    quietedUsers: Array.from(quietedUsers.values()).filter((t) => t > now).length,
    bannedUsers: Array.from(bannedUsers.values()).filter((t) => t > now).length,
    totalReports: Array.from(reports.values()).reduce((sum, r) => sum + r.length, 0),
  };
}
