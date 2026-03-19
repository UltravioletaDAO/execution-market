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

import { handleBalance } from "../src/commands/balance.js";
import { handleEarnings } from "../src/commands/earnings.js";

function mockCtx(sender?: string | null) {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(sender === null ? undefined : (sender ?? "0xWALLET")),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("Balance Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires sender address", async () => {
    const ctx = mockCtx(null);
    await handleBalance(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No se pudo resolver tu direccion."
    );
  });

  it("shows loading message", async () => {
    mockGet.mockResolvedValue({ balance: "0" });
    const ctx = mockCtx();
    await handleBalance(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith("Consultando balances...");
  });

  it("shows zero balance message when no funds", async () => {
    mockGet.mockResolvedValue({ balance: "0" });
    const ctx = mockCtx();
    await handleBalance(ctx, []);
    const calls = ctx.sendTextReply.mock.calls;
    expect(calls.some((c: string[]) => c[0].includes("No tienes balance"))).toBe(true);
  });

  it("shows balances for chains with funds", async () => {
    let callCount = 0;
    mockGet.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) return { balance: "10.5" };
      if (callCount === 3) return { balance: "5.25" };
      return { balance: "0" };
    });

    const ctx = mockCtx();
    await handleBalance(ctx, []);

    expect(ctx.sendMarkdownReply).toHaveBeenCalled();
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Balance USDC");
    expect(reply).toContain("Total");
  });

  it("handles API errors for individual chains", async () => {
    mockGet.mockRejectedValue(new Error("Network error"));
    const ctx = mockCtx();
    await handleBalance(ctx, []);
    const calls = ctx.sendTextReply.mock.calls;
    expect(calls.some((c: string[]) => c[0].includes("No tienes balance"))).toBe(true);
  });
});

describe("Earnings Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires sender address", async () => {
    const ctx = mockCtx(null);
    await handleEarnings(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No se pudo resolver tu direccion."
    );
  });

  it("requires registration", async () => {
    mockWorkerStore.getByAddress.mockReturnValue(undefined);
    const ctx = mockCtx();
    await handleEarnings(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("/register")
    );
  });

  it("shows no-earnings message when empty", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockResolvedValue({ events: [] });
    const ctx = mockCtx();
    await handleEarnings(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No tienes pagos")
    );
  });

  it("shows earnings summary with chain breakdown", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockResolvedValue({
      events: [
        { amount: "5.00", chain: "base", created_at: "2026-03-18T10:00:00Z" },
        { amount: "3.50", chain: "polygon", created_at: "2026-03-17T10:00:00Z" },
        { amount: "2.00", chain: "base", created_at: "2026-03-16T10:00:00Z" },
      ],
    });

    const ctx = mockCtx();
    await handleEarnings(ctx, []);

    expect(ctx.sendMarkdownReply).toHaveBeenCalled();
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Ganancias en Execution Market");
    expect(reply).toContain("Tareas pagadas: **3**");
    expect(reply).toContain("base");
    expect(reply).toContain("polygon");
    expect(reply).toContain("Ultimos pagos");
  });

  it("handles array response format", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockResolvedValue([
      { amount: "1.00", payment_network: "arbitrum" },
    ]);

    const ctx = mockCtx();
    await handleEarnings(ctx, []);

    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("arbitrum");
  });

  it("handles API errors", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ executorId: "ex-1" });
    mockGet.mockRejectedValue(new Error("Server error"));
    const ctx = mockCtx();
    await handleEarnings(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "Error consultando ganancias. Intenta de nuevo."
    );
  });
});
