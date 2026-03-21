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

import { handleRate } from "../src/commands/rate.js";

function mockCtx(sender?: string | null) {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(sender === null ? undefined : (sender ?? "0xRATER")),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("Rate Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows usage with insufficient args", async () => {
    const ctx = mockCtx();
    await handleRate(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Uso: /rate")
    );
  });

  it("shows usage with only one arg", async () => {
    const ctx = mockCtx();
    await handleRate(ctx, ["task-id"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Uso: /rate")
    );
  });

  it("requires sender address", async () => {
    const ctx = mockCtx(null);
    await handleRate(ctx, ["task-1", "5"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No se pudo resolver tu direccion."
    );
  });

  it("requires registration", async () => {
    mockWorkerStore.getByAddress.mockReturnValue(undefined);
    const ctx = mockCtx();
    await handleRate(ctx, ["task-1", "5"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("/register")
    );
  });

  it("rejects score below 1", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    const ctx = mockCtx();
    await handleRate(ctx, ["task-1", "0"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("entre 1 y 5")
    );
  });

  it("rejects score above 5", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    const ctx = mockCtx();
    await handleRate(ctx, ["task-1", "6"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("entre 1 y 5")
    );
  });

  it("rejects non-numeric score", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    const ctx = mockCtx();
    await handleRate(ctx, ["task-1", "great"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("entre 1 y 5")
    );
  });

  it("rejects rating for non-completed task", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue({
      id: "uuid",
      title: "Still in progress",
      status: "assigned",
    });
    const ctx = mockCtx();
    await handleRate(ctx, ["uuid", "5"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("completada")
    );
  });

  it("submits rating with correct score conversion", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue({
      id: "uuid-123",
      title: "Completed task",
      status: "completed",
      agent_id: "2106",
      payment_tx: "0xTX",
    });
    mockPost.mockResolvedValue({ success: true });

    const ctx = mockCtx();
    await handleRate(ctx, ["uuid", "4", "Great", "work!"]);

    expect(mockPost).toHaveBeenCalledWith(
      "/api/v1/reputation/agents/rate",
      expect.objectContaining({
        task_id: "uuid-123",
        agent_id: 2106,
        score: 80,
        comment: "Great work!",
        proof_tx: "0xTX",
      })
    );
    expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
      expect.stringContaining("Rating enviado")
    );
  });

  it("submits rating without comment", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue({
      id: "uuid-456",
      title: "Task",
      status: "completed",
    });
    mockPost.mockResolvedValue({});

    const ctx = mockCtx();
    await handleRate(ctx, ["uuid", "3"]);

    expect(mockPost).toHaveBeenCalledWith(
      "/api/v1/reputation/agents/rate",
      expect.objectContaining({
        score: 60,
        comment: undefined,
      })
    );
  });

  it("defaults agent_id to 2106 when not present", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue({
      id: "uuid-no-agent",
      title: "Task",
      status: "completed",
    });
    mockPost.mockResolvedValue({});

    const ctx = mockCtx();
    await handleRate(ctx, ["uuid", "5"]);

    expect(mockPost).toHaveBeenCalledWith(
      "/api/v1/reputation/agents/rate",
      expect.objectContaining({
        agent_id: 2106,
      })
    );
  });

  it("handles task not found", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue(null);
    const ctx = mockCtx();
    await handleRate(ctx, ["nope", "5"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("no encontrada")
    );
  });

  it("handles API error", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockResolveTask.mockResolvedValue({
      id: "uuid",
      title: "T",
      status: "completed",
    });
    mockPost.mockRejectedValue({
      response: { data: { detail: "Already rated" } },
    });

    const ctx = mockCtx();
    await handleRate(ctx, ["uuid", "5"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Already rated")
    );
  });
});
