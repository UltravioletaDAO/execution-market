import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockPost, mockResolveTask, mockWorkerStore } = vi.hoisted(() => ({
  mockPost: vi.fn(),
  mockResolveTask: vi.fn(),
  mockWorkerStore: {
    getByAddress: vi.fn(),
  },
}));

vi.mock("../src/services/api-client.js", () => ({
  apiClient: { post: mockPost, resolveTask: mockResolveTask },
}));

vi.mock("../src/services/worker-store.js", () => ({
  getWorkerStore: () => mockWorkerStore,
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), error: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

import { handleApply } from "../src/commands/apply.js";

function mockCtx(sender?: string | null) {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(sender === null ? undefined : (sender ?? "0xWORKER")),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("Apply Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows usage when no args", async () => {
    const ctx = mockCtx();
    await handleApply(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Uso: /apply")
    );
  });

  it("requires sender address", async () => {
    const ctx = mockCtx(null);
    await handleApply(ctx, ["task-123"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No se pudo resolver tu direccion."
    );
  });

  it("requires registration", async () => {
    mockWorkerStore.getByAddress.mockReturnValue(undefined);
    const ctx = mockCtx();
    await handleApply(ctx, ["task-123"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("/register")
    );
  });

  it("requires executorId in worker record", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ name: "Bob" });
    const ctx = mockCtx();
    await handleApply(ctx, ["task-123"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("/register")
    );
  });

  it("handles unresolved task", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue(null);
    const ctx = mockCtx();
    await handleApply(ctx, ["nonexistent"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se encontro")
    );
  });

  it("successfully applies to task", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({
      executorId: "ex-1",
      name: "Alice",
    });
    mockResolveTask.mockResolvedValue({
      id: "full-task-uuid",
      title: "Take photo of park",
    });
    mockPost.mockResolvedValue({ success: true });

    const ctx = mockCtx();
    await handleApply(ctx, ["full-task"]);

    expect(mockPost).toHaveBeenCalledWith(
      "/api/v1/tasks/full-task-uuid/apply",
      expect.objectContaining({
        executor_id: "ex-1",
        message: "Applied via XMTP bot",
      })
    );
    expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
      expect.stringContaining("Solicitud enviada")
    );
  });

  it("handles API error with detail", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue({
      id: "uuid",
      title: "Task",
    });
    mockPost.mockRejectedValue({
      response: { data: { detail: "Already applied" } },
    });

    const ctx = mockCtx();
    await handleApply(ctx, ["uuid"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Already applied")
    );
  });
});
