/**
 * EMServ Rate Limiter — per-command sliding window rate limiting.
 *
 * Prevents spam and abuse on IRC commands. Each (nick, command) pair
 * has a configurable window and max invocations.
 */

import { logger } from "../utils/logger.js";

// ─── Rate Limit Configuration ────────────────────────────────────

interface RateLimitConfig {
  max: number;
  windowSec: number;
}

const RATE_LIMITS: Record<string, RateLimitConfig> = {
  tasks: { max: 10, windowSec: 60 },
  search: { max: 10, windowSec: 60 },
  claim: { max: 5, windowSec: 60 },
  publish: { max: 3, windowSec: 300 },
  bid: { max: 10, windowSec: 60 },
  submit: { max: 3, windowSec: 300 },
  approve: { max: 5, windowSec: 60 },
  reject: { max: 5, windowSec: 60 },
  available: { max: 5, windowSec: 60 },
  match: { max: 5, windowSec: 60 },
  handoff: { max: 5, windowSec: 60 },
};

const DEFAULT_LIMIT: RateLimitConfig = { max: 20, windowSec: 60 };

// ─── Sliding Window Counter ──────────────────────────────────────

// Key: "nick:command", Value: array of timestamps (ms)
const counters = new Map<string, number[]>();

/**
 * Check if a command invocation is rate-limited.
 * Returns remaining cooldown in seconds, or 0 if allowed.
 */
export function checkRateLimit(nick: string, command: string): number {
  const key = `${nick.toLowerCase()}:${command}`;
  const config = RATE_LIMITS[command] ?? DEFAULT_LIMIT;
  const now = Date.now();
  const windowMs = config.windowSec * 1000;

  // Get or create counter
  let timestamps = counters.get(key) ?? [];

  // Remove expired entries
  timestamps = timestamps.filter((t) => now - t < windowMs);

  if (timestamps.length >= config.max) {
    // Rate limited — compute cooldown
    const oldestInWindow = timestamps[0];
    const cooldownMs = windowMs - (now - oldestInWindow);
    const cooldownSec = Math.ceil(cooldownMs / 1000);
    logger.debug({ nick, command, cooldownSec }, "Rate limited");
    counters.set(key, timestamps);
    return cooldownSec;
  }

  // Allow and record
  timestamps.push(now);
  counters.set(key, timestamps);
  return 0;
}

/**
 * Reset rate limit for a specific nick+command (admin use).
 */
export function resetRateLimit(nick: string, command: string): void {
  const key = `${nick.toLowerCase()}:${command}`;
  counters.delete(key);
}

/**
 * Clear all rate limit counters.
 */
export function clearAllRateLimits(): void {
  counters.clear();
}

/**
 * Get current rate limit stats (for metrics).
 */
export function getRateLimitStats(): { trackedPairs: number } {
  return { trackedPairs: counters.size };
}
