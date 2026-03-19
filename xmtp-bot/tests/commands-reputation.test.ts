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

import { handleReputation } from "../src/commands/reputation.js";

function mockCtx(sender?: string | null) {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(sender === null ? undefined : (sender ?? "0xMYWALLET")),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("Reputation Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires sender address", async () => {
    const ctx = mockCtx(null);
    await handleReputation(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No se pudo resolver tu direccion."
    );
  });

  it("queries own reputation when no args", async () => {
    mockGet.mockResolvedValue({
      average_score: 4.2,
      total_ratings: 15,
      agent_id: 2106,
    });
    const ctx = mockCtx();
    await handleReputation(ctx, []);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/reputation/agents/0xMYWALLET"
    );
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Tu reputacion");
    expect(reply).toContain("4.2");
    expect(reply).toContain("15");
    expect(reply).toContain("#2106");
  });

  it("queries another address when arg provided", async () => {
    mockGet.mockResolvedValue({
      score: 3.8,
      count: 5,
    });
    const ctx = mockCtx();
    await handleReputation(ctx, ["0xOTHER_WALLET"]);
    expect(mockGet).toHaveBeenCalledWith(
      "/api/v1/reputation/agents/0xOTHER_WALLET"
    );
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Reputacion de 0xOTHE");
  });

  it("shows no-ratings message for self", async () => {
    mockGet.mockResolvedValue({ total_ratings: 0 });
    const ctx = mockCtx();
    await handleReputation(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Aun no tienes ratings")
    );
  });

  it("shows no-ratings message for other address", async () => {
    mockGet.mockResolvedValue({ count: 0 });
    const ctx = mockCtx("0xME");
    await handleReputation(ctx, ["0xOTHER"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("no tiene ratings")
    );
  });

  it("displays star visualization", async () => {
    mockGet.mockResolvedValue({
      average_score: 4,
      total_ratings: 10,
    });
    const ctx = mockCtx();
    await handleReputation(ctx, []);
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("★★★★☆");
  });

  it("displays recent reviews", async () => {
    mockGet.mockResolvedValue({
      average_score: 3.5,
      total_ratings: 8,
      recent_reviews: [
        {
          score: 5,
          comment: "Excellent work",
          from_address: "0xABCDEF1234567890",
        },
        { score: 3, comment: null, from_address: null },
      ],
    });
    const ctx = mockCtx();
    await handleReputation(ctx, []);
    const reply = ctx.sendMarkdownReply.mock.calls[0][0];
    expect(reply).toContain("Ultimos reviews");
    expect(reply).toContain("Excellent work");
    expect(reply).toContain("Anonimo");
  });

  it("handles 404 gracefully", async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } });
    const ctx = mockCtx();
    await handleReputation(ctx, ["0xUNKNOWN"]);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se encontro")
    );
  });

  it("handles other API errors", async () => {
    mockGet.mockRejectedValue(new Error("Server error"));
    const ctx = mockCtx();
    await handleReputation(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "Error consultando reputacion. Intenta de nuevo."
    );
  });
});
