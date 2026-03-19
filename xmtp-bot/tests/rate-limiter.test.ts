import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { RateLimiter } from "../src/utils/rate-limiter.js";

describe("RateLimiter", () => {
  let limiter: RateLimiter;

  beforeEach(() => {
    limiter = new RateLimiter(60_000);
  });

  afterEach(() => {
    limiter.destroy();
  });

  it("allows requests under the limit", () => {
    expect(limiter.allow("user1", 3, 1000)).toBe(true);
    expect(limiter.allow("user1", 3, 1000)).toBe(true);
    expect(limiter.allow("user1", 3, 1000)).toBe(true);
  });

  it("blocks requests over the limit", () => {
    expect(limiter.allow("user1", 2, 1000)).toBe(true);
    expect(limiter.allow("user1", 2, 1000)).toBe(true);
    expect(limiter.allow("user1", 2, 1000)).toBe(false);
  });

  it("is case-insensitive for keys", () => {
    expect(limiter.allow("User1", 1, 1000)).toBe(true);
    expect(limiter.allow("user1", 1, 1000)).toBe(false);
    expect(limiter.allow("USER1", 1, 1000)).toBe(false);
  });

  it("tracks different keys independently", () => {
    expect(limiter.allow("user1", 1, 1000)).toBe(true);
    expect(limiter.allow("user2", 1, 1000)).toBe(true);
    expect(limiter.allow("user1", 1, 1000)).toBe(false);
    expect(limiter.allow("user2", 1, 1000)).toBe(false);
  });

  it("allows again after window expires", () => {
    vi.useFakeTimers();

    expect(limiter.allow("user1", 1, 1000)).toBe(true);
    expect(limiter.allow("user1", 1, 1000)).toBe(false);

    vi.advanceTimersByTime(1001);

    expect(limiter.allow("user1", 1, 1000)).toBe(true);

    vi.useRealTimers();
  });

  it("cleanup removes stale entries", () => {
    vi.useFakeTimers();

    limiter.allow("user1", 5, 1000);
    limiter.allow("user2", 5, 1000);

    vi.advanceTimersByTime(61_000); // Past 60s cleanup threshold
    limiter.cleanup();

    // After cleanup, both should be allowed again
    expect(limiter.allow("user1", 1, 1000)).toBe(true);
    expect(limiter.allow("user2", 1, 1000)).toBe(true);

    vi.useRealTimers();
  });

  it("uses default params (5 reqs, 1000ms window)", () => {
    for (let i = 0; i < 5; i++) {
      expect(limiter.allow("test")).toBe(true);
    }
    expect(limiter.allow("test")).toBe(false);
  });
});
