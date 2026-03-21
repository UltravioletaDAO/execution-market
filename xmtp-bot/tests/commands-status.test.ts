import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockResolveTask } = vi.hoisted(() => ({
  mockResolveTask: vi.fn(),
}));

vi.mock("../src/services/api-client.js", () => ({
  apiClient: { resolveTask: mockResolveTask },
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), error: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

import { handleStatus } from "../src/commands/status.js";

function mockCtx() {
  return {
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("Status Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows usage when no args", async () => {
    const ctx = mockCtx();
    await handleStatus(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith("Uso: /status <task-id>");
  });

  it("handles unresolved task", async () => {
    mockResolveTask.mockResolvedValue(null);
    const ctx = mockCtx();
    await handleStatus(ctx, ["nonexistent"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se encontro")
    );
  });

  it("displays task details", async () => {
    mockResolveTask.mockResolvedValue({
      id: "uuid-abc-def",
      title: "Verify address",
      status: "assigned",
      bounty_usdc: 3.5,
      deadline: "2026-03-20T12:00:00Z",
      category: "physical_presence",
      executor_id: "exec-42",
    });

    const ctx = mockCtx();
    await handleStatus(ctx, ["abc"]);

    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Verify address");
    expect(reply).toContain("assigned");
    expect(reply).toContain("physical_presence");
    expect(reply).toContain("exec-42");
  });

  it("omits executor when not assigned", async () => {
    mockResolveTask.mockResolvedValue({
      id: "uuid-xyz",
      title: "Open task",
      status: "published",
      bounty: 2.0,
      category: "simple_action",
    });

    const ctx = mockCtx();
    await handleStatus(ctx, ["xyz"]);

    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Open task");
    expect(reply).not.toContain("Executor");
  });

  it("handles API errors", async () => {
    mockResolveTask.mockRejectedValue(new Error("timeout"));
    const ctx = mockCtx();
    await handleStatus(ctx, ["xyz"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "Error al obtener estado. Intenta de nuevo."
    );
  });
});
