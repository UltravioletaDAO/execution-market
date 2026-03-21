export class RateLimiter {
  private windows: Map<string, number[]> = new Map();
  private cleanupTimer: ReturnType<typeof setInterval>;

  constructor(cleanupIntervalMs = 60_000) {
    this.cleanupTimer = setInterval(() => this.cleanup(), cleanupIntervalMs);
    this.cleanupTimer.unref(); // Don't prevent process exit
  }

  /**
   * Check if a request is allowed under the rate limit.
   * @param key - Identifier (e.g., wallet address)
   * @param maxReqs - Maximum requests allowed in the window
   * @param windowMs - Window duration in milliseconds
   * @returns true if allowed, false if rate limited
   */
  allow(key: string, maxReqs = 5, windowMs = 1000): boolean {
    const now = Date.now();
    const k = key.toLowerCase();
    const timestamps = (this.windows.get(k) ?? []).filter((t) => now - t < windowMs);

    if (timestamps.length >= maxReqs) {
      this.windows.set(k, timestamps);
      return false;
    }

    timestamps.push(now);
    this.windows.set(k, timestamps);
    return true;
  }

  /**
   * Remove stale entries older than 60 seconds.
   */
  cleanup(): void {
    const now = Date.now();
    for (const [key, ts] of this.windows) {
      const valid = ts.filter((t) => now - t < 60_000);
      if (valid.length === 0) {
        this.windows.delete(key);
      } else {
        this.windows.set(key, valid);
      }
    }
  }

  /**
   * Stop the cleanup timer (for graceful shutdown).
   */
  destroy(): void {
    clearInterval(this.cleanupTimer);
  }
}

/** Global rate limiter instance — 5 messages per second per user */
export const messageLimiter = new RateLimiter();
