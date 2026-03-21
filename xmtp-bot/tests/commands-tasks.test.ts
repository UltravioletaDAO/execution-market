import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock("../src/services/api-client.js", () => ({
  apiClient: { get: mockGet },
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), error: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

import { handleTasks } from "../src/commands/tasks.js";

function mockCtx() {
  return {
    getSenderAddress: vi.fn().mockResolvedValue("0xSENDER"),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("Tasks Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty message when no tasks", async () => {
    mockGet.mockResolvedValue({ tasks: [] });
    const ctx = mockCtx();
    await handleTasks(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No hay tareas disponibles en este momento."
    );
  });

  it("lists tasks with bounty and deadline", async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url.includes("/reputation/")) return { score: 4.5 };
      return {
        tasks: [
          {
            id: "task-abc-123-def",
            title: "Deliver coffee to office",
            bounty_usdc: 5.0,
            deadline: new Date(Date.now() + 3600000).toISOString(),
            agent_id: "2106",
          },
        ],
      };
    });

    const ctx = mockCtx();
    await handleTasks(ctx, []);
    expect(ctx.sendMarkdownReply).toHaveBeenCalled();
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Tareas disponibles");
    expect(reply).toContain("Deliver coffee");
    expect(reply).toContain("/apply");
  });

  it("passes category filter when provided", async () => {
    mockGet.mockResolvedValue({ tasks: [] });
    const ctx = mockCtx();
    await handleTasks(ctx, ["physical_presence"]);
    expect(mockGet).toHaveBeenCalledWith("/api/v1/tasks", {
      params: {
        status: "published",
        limit: "10",
        category: "physical_presence",
      },
    });
  });

  it("handles API errors gracefully", async () => {
    mockGet.mockRejectedValue(new Error("Network timeout"));
    const ctx = mockCtx();
    await handleTasks(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "Error al obtener tareas. Intenta de nuevo."
    );
  });

  it("handles array response format", async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url.includes("/reputation/")) throw new Error("404");
      return [
        {
          id: "task-xyz",
          title: "Simple task",
          bounty: 1.5,
          deadline: null,
        },
      ];
    });
    const ctx = mockCtx();
    await handleTasks(ctx, []);
    expect(ctx.sendMarkdownReply).toHaveBeenCalled();
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Simple task");
  });
});
