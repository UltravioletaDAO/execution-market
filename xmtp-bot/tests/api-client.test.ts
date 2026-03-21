import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock config
vi.mock("../src/config.js", () => ({
  config: {
    em: {
      apiUrl: "https://api.test.local",
      apiKey: "test-api-key-123",
      wsUrl: "",
    },
    irc: { enabled: false },
    health: { port: 3000 },
    xmtp: { env: "dev", dbPath: "./data/xmtp/bot.db3" },
    log: { level: "silent" },
  },
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

// We test the client's construction and methods by importing it
// Note: actual HTTP calls would need axios mocking for full integration tests

import { apiClient } from "../src/services/api-client.js";

describe("EMApiClient", () => {
  it("exists and has expected methods", () => {
    expect(apiClient).toBeDefined();
    expect(typeof apiClient.get).toBe("function");
    expect(typeof apiClient.post).toBe("function");
    expect(typeof apiClient.resolveTask).toBe("function");
    expect(typeof apiClient.submitEvidence).toBe("function");
    expect(typeof apiClient.getPresignedUploadUrl).toBe("function");
    expect(typeof apiClient.uploadToS3).toBe("function");
  });
});
