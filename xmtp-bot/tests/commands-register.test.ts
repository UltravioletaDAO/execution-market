import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Use vi.hoisted for mock variables (hoisted above vi.mock) ────
const { mockPost, mockGet, mockWorkerStore } = vi.hoisted(() => ({
  mockPost: vi.fn(),
  mockGet: vi.fn(),
  mockWorkerStore: {
    getByAddress: vi.fn(),
    setRegistrationProgress: vi.fn(),
    getRegistrationProgress: vi.fn(),
    register: vi.fn(),
    resetConversation: vi.fn(),
  },
}));

vi.mock("../src/services/api-client.js", () => ({
  apiClient: { post: mockPost, get: mockGet },
}));

vi.mock("../src/services/worker-store.js", () => ({
  getWorkerStore: () => mockWorkerStore,
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), error: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

import { handleRegister, handleRegistrationText } from "../src/commands/register.js";

// ─── Helper: create a mock MessageContext ─────────────────────────
function mockCtx(senderAddress?: string | null) {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(senderAddress === null ? undefined : (senderAddress ?? "0xABC123DEF456")),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
  } as any;
}

describe("Register Command", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejects when sender address is not resolvable", async () => {
    const ctx = mockCtx(null);
    await handleRegister(ctx, []);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      "No se pudo resolver tu direccion."
    );
  });

  it("tells already-registered users their info", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({
      executorId: "exec-789",
      name: "Alice",
    });
    const ctx = mockCtx("0xWALLET123");
    await handleRegister(ctx, []);
    expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
      expect.stringContaining("Ya estas registrado")
    );
    expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
      expect.stringContaining("exec-789")
    );
  });

  it("starts registration flow for new users", async () => {
    mockWorkerStore.getByAddress.mockReturnValue(undefined);
    const ctx = mockCtx("0xNEWUSER");
    await handleRegister(ctx, []);
    expect(mockWorkerStore.setRegistrationProgress).toHaveBeenCalledWith(
      "0xNEWUSER",
      { step: "name" }
    );
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Paso 1/2")
    );
  });

  it("starts registration even when worker exists but has no executorId", async () => {
    mockWorkerStore.getByAddress.mockReturnValue({ name: "Bob" });
    const ctx = mockCtx("0xBOBWALLET");
    await handleRegister(ctx, []);
    expect(mockWorkerStore.setRegistrationProgress).toHaveBeenCalledWith(
      "0xBOBWALLET",
      { step: "name" }
    );
  });
});

describe("Registration Text Flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Name Step", () => {
    it("rejects names shorter than 2 characters", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({ step: "name" });
      const ctx = mockCtx("0xUSER1");
      await handleRegistrationText(ctx, "0xUSER1", "A");
      expect(ctx.sendTextReply).toHaveBeenCalledWith(
        expect.stringContaining("entre 2 y 50")
      );
    });

    it("rejects names longer than 50 characters", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({ step: "name" });
      const ctx = mockCtx("0xUSER1");
      await handleRegistrationText(ctx, "0xUSER1", "A".repeat(51));
      expect(ctx.sendTextReply).toHaveBeenCalledWith(
        expect.stringContaining("entre 2 y 50")
      );
    });

    it("accepts valid name and moves to email step", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({ step: "name" });
      const ctx = mockCtx("0xUSER1");
      await handleRegistrationText(ctx, "0xUSER1", "Carlos");
      expect(mockWorkerStore.setRegistrationProgress).toHaveBeenCalledWith(
        "0xUSER1",
        { step: "email", name: "Carlos" }
      );
      expect(ctx.sendTextReply).toHaveBeenCalledWith(
        expect.stringContaining("Paso 2/2")
      );
    });
  });

  describe("Email Step", () => {
    it("rejects invalid emails", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "email",
        name: "Carlos",
      });
      const ctx = mockCtx("0xUSER2");
      await handleRegistrationText(ctx, "0xUSER2", "notanemail");
      expect(ctx.sendTextReply).toHaveBeenCalledWith(
        expect.stringContaining("Email invalido")
      );
    });

    it("accepts skip and moves to confirm", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "email",
        name: "Carlos",
      });
      const ctx = mockCtx("0xUSER2");
      await handleRegistrationText(ctx, "0xUSER2", "skip");
      expect(mockWorkerStore.setRegistrationProgress).toHaveBeenCalledWith(
        "0xUSER2",
        { step: "confirm", name: "Carlos", email: undefined }
      );
    });

    it("accepts 'omitir' as skip", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "email",
        name: "Ana",
      });
      const ctx = mockCtx("0xUSER3");
      await handleRegistrationText(ctx, "0xUSER3", "omitir");
      expect(mockWorkerStore.setRegistrationProgress).toHaveBeenCalledWith(
        "0xUSER3",
        { step: "confirm", name: "Ana", email: undefined }
      );
    });

    it("accepts valid email and moves to confirm", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "email",
        name: "Diana",
      });
      const ctx = mockCtx("0xUSER4");
      await handleRegistrationText(ctx, "0xUSER4", "diana@example.com");
      expect(mockWorkerStore.setRegistrationProgress).toHaveBeenCalledWith(
        "0xUSER4",
        { step: "confirm", name: "Diana", email: "diana@example.com" }
      );
      expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
        expect.stringContaining("Confirmar registro")
      );
    });
  });

  describe("Confirm Step", () => {
    it("registers on 'si' confirmation", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "confirm",
        name: "Carlos",
        email: "carlos@test.com",
      });
      mockPost.mockResolvedValue({ executor_id: "ex-100" });
      const ctx = mockCtx("0xCONFIRM");
      await handleRegistrationText(ctx, "0xCONFIRM", "si");
      expect(mockPost).toHaveBeenCalledWith("/api/v1/workers/register", {
        wallet_address: "0xCONFIRM",
        name: "Carlos",
        email: "carlos@test.com",
      });
      expect(mockWorkerStore.register).toHaveBeenCalledWith(
        "0xCONFIRM",
        "ex-100",
        "Carlos"
      );
      expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
        expect.stringContaining("Registro exitoso")
      );
    });

    it("registers on 'yes' confirmation", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "confirm",
        name: "Bob",
      });
      mockPost.mockResolvedValue({ id: "ex-200" });
      const ctx = mockCtx("0xYES");
      await handleRegistrationText(ctx, "0xYES", "yes");
      expect(mockWorkerStore.register).toHaveBeenCalledWith(
        "0xYES",
        "ex-200",
        "Bob"
      );
    });

    it("cancels on 'no'", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "confirm",
        name: "Eve",
      });
      const ctx = mockCtx("0xCANCEL");
      await handleRegistrationText(ctx, "0xCANCEL", "no");
      expect(ctx.sendTextReply).toHaveBeenCalledWith(
        expect.stringContaining("cancelado")
      );
      expect(mockWorkerStore.resetConversation).toHaveBeenCalledWith("0xCANCEL");
    });

    it("handles API registration failure", async () => {
      mockWorkerStore.getRegistrationProgress.mockReturnValue({
        step: "confirm",
        name: "Fail",
      });
      mockPost.mockRejectedValue({
        response: { data: { detail: "Duplicate wallet" } },
      });
      const ctx = mockCtx("0xFAIL");
      await handleRegistrationText(ctx, "0xFAIL", "si");
      expect(ctx.sendTextReply).toHaveBeenCalledWith(
        expect.stringContaining("Duplicate wallet")
      );
      expect(mockWorkerStore.resetConversation).toHaveBeenCalledWith("0xFAIL");
    });
  });

  it("resets conversation when no progress exists", async () => {
    mockWorkerStore.getRegistrationProgress.mockReturnValue(undefined);
    const ctx = mockCtx("0xNOPROGRESS");
    await handleRegistrationText(ctx, "0xNOPROGRESS", "hello");
    expect(mockWorkerStore.resetConversation).toHaveBeenCalledWith("0xNOPROGRESS");
  });
});
