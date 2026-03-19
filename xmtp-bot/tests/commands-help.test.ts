import { describe, it, expect, vi } from "vitest";

// ─── Mock XMTP agent-sdk native bindings ────────────────────────
vi.mock("@xmtp/agent-sdk", () => ({
  Agent: vi.fn(),
  CommandRouter: vi.fn(),
}));

// ─── Hoisted mocks ──────────────────────────────────────────────
vi.mock("../src/config.js", () => ({
  config: {
    em: { apiUrl: "https://api.test.local", apiKey: "test-key", wsUrl: "" },
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
    trace: vi.fn(),
  },
}));

vi.mock("../src/services/api-client.js", () => ({
  apiClient: {
    resolveTask: vi.fn(),
    submitEvidence: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("../src/services/worker-store.js", () => ({
  getWorkerStore: () => ({
    getByAddress: vi.fn(),
    getOrCreate: vi.fn(),
    register: vi.fn(),
    getConversationState: vi.fn().mockReturnValue("idle"),
    setConversationState: vi.fn(),
    resetConversation: vi.fn(),
    getAllRegistered: vi.fn().mockReturnValue([]),
  }),
}));

import { handleHelp } from "../src/commands/help.js";
import { getCommandList, findCommand } from "../src/commands/index.js";

function mockCtx() {
  return {
    getSenderAddress: vi.fn().mockResolvedValue("0xTest"),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
    message: { content: "/help" },
  } as any;
}

describe("Help Command", () => {
  it("sends markdown reply with command list", async () => {
    const ctx = mockCtx();
    await handleHelp(ctx, []);
    expect(ctx.sendMarkdownReply).toHaveBeenCalledTimes(1);
    const reply = ctx.sendMarkdownReply.mock.calls[0][0] as string;
    expect(reply).toContain("Execution Market Bot");
    expect(reply).toContain("Comandos disponibles");
  });

  it("lists all 14 commands", async () => {
    const ctx = mockCtx();
    await handleHelp(ctx, []);
    const reply = ctx.sendMarkdownReply.mock.calls[0][0] as string;
    const commandNames = [
      "/help",
      "/tasks",
      "/apply",
      "/submit",
      "/status",
      "/mytasks",
      "/balance",
      "/earnings",
      "/rate",
      "/reputation",
      "/register",
      "/skip",
      "/cancel",
      "/done",
    ];
    for (const cmd of commandNames) {
      expect(reply).toContain(cmd);
    }
  });
});

describe("Command Registry", () => {
  it("getCommandList returns all 14 commands", () => {
    const commands = getCommandList();
    expect(commands).toHaveLength(14);
  });

  it("findCommand finds existing commands", () => {
    expect(findCommand("help")).toBeDefined();
    expect(findCommand("register")).toBeDefined();
    expect(findCommand("tasks")).toBeDefined();
    expect(findCommand("submit")).toBeDefined();
  });

  it("findCommand returns undefined for unknown commands", () => {
    expect(findCommand("nonexistent")).toBeUndefined();
    expect(findCommand("")).toBeUndefined();
  });

  it("findCommand is case-insensitive", () => {
    expect(findCommand("HELP")).toBeDefined();
    expect(findCommand("Register")).toBeDefined();
  });

  it("every command has usage and description", () => {
    const commands = getCommandList();
    for (const cmd of commands) {
      expect(cmd.usage).toBeTruthy();
      expect(cmd.description).toBeTruthy();
      expect(cmd.handler).toBeInstanceOf(Function);
    }
  });

  it("every command usage starts with /", () => {
    const commands = getCommandList();
    for (const cmd of commands) {
      expect(cmd.usage.startsWith("/")).toBe(true);
    }
  });
});
