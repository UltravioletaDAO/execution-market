import { describe, it, expect, beforeEach, vi } from "vitest";

describe("Config", () => {
  beforeEach(() => {
    vi.resetModules();
    // Clear env vars that might interfere
    delete process.env.EM_API_URL;
    delete process.env.EM_WS_URL;
    delete process.env.HEALTH_PORT;
    delete process.env.IRC_ENABLED;
    delete process.env.IRC_CHANNELS;
    delete process.env.XMTP_ENV;
    delete process.env.LOG_LEVEL;
  });

  it("has correct defaults", async () => {
    const { config } = await import("../src/config.js");

    expect(config.em.apiUrl).toBe("https://api.execution.market");
    expect(config.em.wsUrl).toBe("wss://api.execution.market/ws");
    expect(config.health.port).toBe(8090);
    expect(config.irc.enabled).toBe(false);
    expect(config.irc.host).toBe("irc.meshrelay.xyz");
    expect(config.irc.port).toBe(6697);
    expect(config.irc.tls).toBe(true);
    expect(config.irc.nick).toBe("em-bot");
    expect(config.irc.channels).toEqual(["#bounties", "#Agents"]);
    expect(config.xmtp.env).toBe("dev");
    expect(config.log.level).toBe("info");
  });

  it("IRC channels split correctly", async () => {
    process.env.IRC_CHANNELS = "#test, #tasks, #general";
    vi.resetModules();
    const { config } = await import("../src/config.js");
    expect(config.irc.channels).toEqual(["#test", "#tasks", "#general"]);
  });
});
