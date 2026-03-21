import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockGet, mockWorkerStore } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockWorkerStore: {
    getByAddress: vi.fn(),
  },
}));

vi.mock("../src/services/api-client.js", () => ({
  apiClient: { get: mockGet },
}));

vi.mock("../src/services/worker-store.js", () => ({
  getWorkerStore: () => mockWorkerStore,
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), error: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

import { handleMyTasks } from "../src/commands/mytasks.js";

function mockCtx(sender?: string | null) {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(sender === null ? undefined : (sender ?? "0xWORKER")),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("MyTasks Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires sender address", async () => {
    const ctx = mockCtx(null);
    await handleMyTasks(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No se pudo resolver tu direccion."
    );
  });

  it("requires registration", async () => {
    mockWorkerStore.getByAddress.mockReturnValue(undefined);
    const ctx = mockCtx();
    await handleMyTasks(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("/register")
    );
  });

  it("shows empty message when no tasks", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockResolvedValue({ tasks: [] });
    const ctx = mockCtx();
    await handleMyTasks(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No tienes tareas activas")
    );
  });

  it("lists assigned tasks with status", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockResolvedValue({
      tasks: [
        {
          id: "task-uuid-1",
          title: "Deliver package to downtown",
          status: "assigned",
          bounty_usdc: 8.5,
        },
        {
          id: "task-uuid-2",
          title: "Take photo of storefront verification",
          status: "submitted",
          bounty: 3.0,
        },
      ],
    });

    const ctx = mockCtx();
    await handleMyTasks(ctx, []);

    expect(mockGet).toHaveBeenCalledWith("/api/v1/tasks", {
      params: { executor_id: "ex-1", limit: "20" },
    });
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Mis tareas");
    expect(reply).toContain("assigned");
    expect(reply).toContain("submitted");
    expect(reply).toContain("Deliver package");
  });

  it("handles array response format", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockResolvedValue([
      {
        id: "t-1",
        title: "Task A",
        status: "assigned",
        bounty_usdc: 1.0,
      },
    ]);
    const ctx = mockCtx();
    await handleMyTasks(ctx, []);
    expect(ctx.sendMarkdownReply).toHaveBeenCalled();
  });

  it("handles API errors", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockRejectedValue(new Error("timeout"));
    const ctx = mockCtx();
    await handleMyTasks(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "Error al obtener tus tareas. Intenta de nuevo."
    );
  });
});
