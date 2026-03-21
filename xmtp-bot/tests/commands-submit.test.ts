import { describe, it, expect, beforeEach, vi } from "vitest";

// ─── Hoisted mock variables ──────────────────────────────────────
const { mockResolveTask, mockSubmitEvidence, mockGetWorkerStore } = vi.hoisted(
  () => ({
    mockResolveTask: vi.fn(),
    mockSubmitEvidence: vi.fn(),
    mockGetWorkerStore: vi.fn(),
  })
);

// ─── Mock config ──────────────────────────────────────────────────
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
    resolveTask: mockResolveTask,
    submitEvidence: mockSubmitEvidence,
    get: vi.fn(),
    post: vi.fn(),
    getPresignedUploadUrl: vi.fn(),
    uploadToS3: vi.fn(),
  },
}));

// Worker store mock with actual store behavior
const mockStore = {
  getByAddress: vi.fn(),
  getOrCreate: vi.fn(),
  register: vi.fn(),
  getConversationState: vi.fn().mockReturnValue("idle"),
  setConversationState: vi.fn(),
  setRegistrationProgress: vi.fn(),
  getRegistrationProgress: vi.fn(),
  resetConversation: vi.fn(),
  getAllRegistered: vi.fn().mockReturnValue([]),
};

vi.mock("../src/services/worker-store.js", () => ({
  getWorkerStore: () => mockStore,
}));

import {
  getActiveDraft,
  clearDraft,
  isSubmissionTimedOut,
  collectAttachment,
  handleSubmissionText,
  handleSubmissionSkip,
  handleSubmissionCancel,
  handleSubmissionDone,
  startSubmission,
} from "../src/submission/flow.js";

// ─── Helpers ──────────────────────────────────────────────────────
function mockCtx(senderAddress: string | null = "0xWorker1") {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(senderAddress),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    sendMarkdownReply: vi.fn().mockResolvedValue(undefined),
    message: { content: "" },
  } as any;
}

function makeTask(overrides: Record<string, unknown> = {}) {
  return {
    id: "task-uuid-12345678",
    title: "Test Task",
    evidence_requirements: [
      { type: "text", description: "Describe what you did", required: true },
      {
        type: "photo",
        description: "Take a photo",
        required: true,
      },
      {
        type: "gps",
        description: "Your location",
        required: false,
      },
    ],
    ...overrides,
  };
}

// ─── Tests ────────────────────────────────────────────────────────
describe("Submit Command — startSubmission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset drafts by clearing for known addresses
    clearDraft("0xWorker1");
    clearDraft("0xWorker2");
    clearDraft("0xNoExec");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "idle",
    });
    mockStore.getConversationState.mockReturnValue("idle");
  });

  it("rejects when sender address is null", async () => {
    const ctx = mockCtx(null);
    await startSubmission(ctx, "task-1");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se pudo resolver")
    );
  });

  it("rejects unregistered workers", async () => {
    mockStore.getByAddress.mockReturnValue(undefined);
    const ctx = mockCtx("0xNoExec");
    await startSubmission(ctx, "task-1");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("registrarte primero")
    );
  });

  it("rejects workers without executorId", async () => {
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xnoexec",
      conversationState: "idle",
    });
    const ctx = mockCtx("0xNoExec");
    await startSubmission(ctx, "task-1");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("registrarte primero")
    );
  });

  it("rejects when a draft already exists", async () => {
    const task = makeTask();
    mockResolveTask.mockResolvedValueOnce(task);

    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");
    // Now try again — should be rejected
    const ctx2 = mockCtx("0xWorker1");
    await startSubmission(ctx2, "task-other");
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("submission activa")
    );
  });

  it("rejects when task not found", async () => {
    mockResolveTask.mockResolvedValueOnce(null);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "nonexistent");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se encontro")
    );
  });

  it("rejects when task has no evidence requirements", async () => {
    const task = makeTask({ evidence_requirements: [] });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("no tiene requisitos de evidencia")
    );
  });

  it("rejects when evidence_requirements is null", async () => {
    const task = makeTask({ evidence_requirements: null });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("no tiene requisitos de evidencia")
    );
  });

  it("starts submission successfully with array requirements", async () => {
    const task = makeTask();
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    // Should set conversation state
    expect(mockStore.setConversationState).toHaveBeenCalledWith(
      "0xWorker1",
      "submission"
    );
    // Should show intro
    expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviar evidencia")
    );
    // Should show piece count (2 required + 1 optional)
    expect(ctx.sendMarkdownReply).toHaveBeenCalledWith(
      expect.stringContaining("2")
    );
    // Draft should exist
    const draft = getActiveDraft("0xWorker1");
    expect(draft).toBeDefined();
    expect(draft!.taskId).toBe("task-uuid-12345678");
    expect(draft!.pieces).toHaveLength(3);
  });

  it("starts submission with object-format requirements", async () => {
    const task = makeTask({
      evidence_requirements: {
        text: "Write a summary",
        photo: { description: "Photo proof", required: true },
        gps: { description: "Location check", required: false },
      },
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker2");
    await startSubmission(ctx, "task-uuid-12345678");

    const draft = getActiveDraft("0xWorker2");
    expect(draft).toBeDefined();
    expect(draft!.pieces).toHaveLength(3);
    expect(draft!.pieces[0].type).toBe("text");
    expect(draft!.pieces[1].type).toBe("photo");
    expect(draft!.pieces[2].type).toBe("gps");
  });
});

describe("Submit Command — handleSubmissionText", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  async function setupDraft() {
    const task = makeTask();
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");
    return getActiveDraft("0xWorker1")!;
  }

  it("resets conversation when no draft exists", async () => {
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(ctx, "0xWorker1", "some text");
    expect(mockStore.resetConversation).toHaveBeenCalledWith("0xWorker1");
  });

  it("handles timeout during submission", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "Answer", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    // Manually expire the draft
    const draft = getActiveDraft("0xWorker1")!;
    draft.startedAt = Date.now() - 31 * 60 * 1000;

    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionText(ctx2, "0xWorker1", "my answer");
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("expirada")
    );
    expect(getActiveDraft("0xWorker1")).toBeUndefined();
  });

  it("rejects text shorter than 5 chars", async () => {
    await setupDraft();
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(ctx, "0xWorker1", "hi");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Texto muy corto")
    );
  });

  it("rejects text longer than 5000 chars", async () => {
    await setupDraft();
    const ctx = mockCtx("0xWorker1");
    const longText = "a".repeat(5001);
    await handleSubmissionText(ctx, "0xWorker1", longText);
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Texto muy largo")
    );
  });

  it("accepts valid text and advances to next piece", async () => {
    await setupDraft();
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx,
      "0xWorker1",
      "I completed the task by going to the location."
    );
    const draft = getActiveDraft("0xWorker1")!;
    // First piece should be collected
    expect(draft.pieces[0].collected).toBe(true);
    expect(draft.pieces[0].value).toBe(
      "I completed the task by going to the location."
    );
    // Should advance to next (photo piece)
    expect(draft.currentPieceIndex).toBe(1);
    // Should prompt for next piece
    expect(ctx.sendMarkdownReply).toHaveBeenCalled();
  });

  it("rejects text input for photo-type pieces", async () => {
    await setupDraft();
    // Advance past text piece
    const draft = getActiveDraft("0xWorker1")!;
    draft.pieces[0].collected = true;
    draft.currentPieceIndex = 1; // Now on photo piece
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(ctx, "0xWorker1", "this is text not a photo");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("requiere un archivo")
    );
  });

  it("rejects text input for video-type pieces", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "video", description: "Record a video", required: true },
      ],
    });
    clearDraft("0xWorker1");
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionText(ctx2, "0xWorker1", "text instead of video");
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("requiere un archivo")
    );
  });
});

describe("Submit Command — GPS Parsing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  async function setupGpsDraft() {
    const task = makeTask({
      evidence_requirements: [
        { type: "gps", description: "Your location", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");
  }

  it("parses direct coordinates", async () => {
    await setupGpsDraft();
    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(ctx, "0xWorker1", "25.7617,-80.1918");
    const draft = getActiveDraft("0xWorker1");
    // Draft should be auto-submitted (only 1 piece, all done)
    // The piece should have been collected
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("parses Google Maps @lat,lng URL", async () => {
    await setupGpsDraft();
    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx,
      "0xWorker1",
      "https://www.google.com/maps/@25.7617,-80.1918,15z"
    );
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("parses Google Maps ?q=lat,lng URL", async () => {
    await setupGpsDraft();
    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx,
      "0xWorker1",
      "https://maps.google.com/?q=25.7617,-80.1918"
    );
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("parses Google Maps place URL", async () => {
    await setupGpsDraft();
    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx,
      "0xWorker1",
      "https://www.google.com/maps/place/Miami/@25.7617,-80.1918,12z"
    );
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("parses Waze URL", async () => {
    await setupGpsDraft();
    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx,
      "0xWorker1",
      "https://waze.com/ul?ll=25.7617,-80.1918"
    );
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("parses Apple Maps URL", async () => {
    await setupGpsDraft();
    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx,
      "0xWorker1",
      "https://maps.apple.com/?ll=25.7617,-80.1918"
    );
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("rejects invalid GPS input", async () => {
    await setupGpsDraft();
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(ctx, "0xWorker1", "not a location");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se pudo leer la ubicacion")
    );
  });

  it("rejects out-of-range latitude", async () => {
    await setupGpsDraft();
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(ctx, "0xWorker1", "91.0,-80.0");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se pudo leer la ubicacion")
    );
  });

  it("rejects out-of-range longitude", async () => {
    await setupGpsDraft();
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionText(ctx, "0xWorker1", "25.0,-181.0");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No se pudo leer la ubicacion")
    );
  });
});

describe("Submit Command — JSON Response", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  it("accepts valid JSON", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "json_response", description: "API response", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx2,
      "0xWorker1",
      '{"status": "ok", "data": [1, 2, 3]}'
    );
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("accepts invalid JSON as text with warning", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "json_response", description: "API response", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx2,
      "0xWorker1",
      "this is not valid json at all"
    );
    // Should warn about invalid JSON
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No es JSON valido")
    );
  });
});

describe("Submit Command — handleSubmissionSkip", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  it("prevents skipping required pieces", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "Answer", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionSkip(ctx2, "0xWorker1");
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("obligatoria")
    );
  });

  it("allows skipping optional pieces", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "gps", description: "Location", required: false },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionSkip(ctx2, "0xWorker1");
    // Should advance/complete since only 1 optional piece was skipped
    // With 0 required pieces, compileAndSubmit should accept
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Enviando")
    );
  });

  it("does nothing when no draft exists", async () => {
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionSkip(ctx, "0xWorker1");
    expect(ctx.sendTextReply).not.toHaveBeenCalled();
  });
});

describe("Submit Command — handleSubmissionCancel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  it("cancels an active submission", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "Answer", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionCancel(ctx2, "0xWorker1");
    expect(ctx2.sendTextReply).toHaveBeenCalledWith("Submission cancelada.");
    expect(getActiveDraft("0xWorker1")).toBeUndefined();
  });

  it("reports no active submission", async () => {
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionCancel(ctx, "0xWorker1");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No hay submission activa")
    );
  });
});

describe("Submit Command — handleSubmissionDone", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  it("reports no active submission", async () => {
    const ctx = mockCtx("0xWorker1");
    await handleSubmissionDone(ctx, "0xWorker1");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("No hay submission activa")
    );
  });

  it("rejects when required pieces are missing", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "Answer", required: true },
        { type: "photo", description: "Photo proof", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    // Try /done without filling any pieces
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionDone(ctx2, "0xWorker1");
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Faltan")
    );
    // Draft should still exist (not cleared)
    expect(getActiveDraft("0xWorker1")).toBeDefined();
  });

  it("submits successfully when all required pieces are collected", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "Answer", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    // Fill the text piece
    const draft = getActiveDraft("0xWorker1")!;
    draft.pieces[0].collected = true;
    draft.pieces[0].value = "My completed work";
    draft.currentPieceIndex = 1; // Past the last piece

    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionDone(ctx2, "0xWorker1");
    expect(mockSubmitEvidence).toHaveBeenCalledWith(
      "task-uuid-12345678",
      "exec-1",
      { text: "My completed work" }
    );
    expect(ctx2.sendMarkdownReply).toHaveBeenCalledWith(
      expect.stringContaining("Evidencia enviada")
    );
    // Draft should be cleared
    expect(getActiveDraft("0xWorker1")).toBeUndefined();
  });

  it("handles API error gracefully", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "Answer", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const draft = getActiveDraft("0xWorker1")!;
    draft.pieces[0].collected = true;
    draft.pieces[0].value = "Work done";
    draft.currentPieceIndex = 1;

    mockSubmitEvidence.mockRejectedValueOnce({
      response: { data: { detail: "Task not assigned to this worker" } },
    });
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionDone(ctx2, "0xWorker1");
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Error al enviar evidencia")
    );
    expect(ctx2.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Task not assigned")
    );
    // Draft should still exist so user can retry
    expect(getActiveDraft("0xWorker1")).toBeDefined();
  });

  it("handles duplicate evidence types with indexed keys", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "First answer", required: true },
        { type: "text", description: "Second answer", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const draft = getActiveDraft("0xWorker1")!;
    draft.pieces[0].collected = true;
    draft.pieces[0].value = "Answer 1";
    draft.pieces[1].collected = true;
    draft.pieces[1].value = "Answer 2";
    draft.currentPieceIndex = 2;

    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionDone(ctx2, "0xWorker1");
    expect(mockSubmitEvidence).toHaveBeenCalledWith(
      "task-uuid-12345678",
      "exec-1",
      { text: "Answer 1", text_2: "Answer 2" }
    );
  });
});

describe("Submit Command — collectAttachment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  it("returns false with no active draft", () => {
    const result = collectAttachment(
      "0xWorker1",
      "https://cdn.example.com/img.jpg",
      "image/jpeg"
    );
    expect(result).toBe(false);
  });

  it("collects photo attachment on photo piece", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "photo", description: "Photo proof", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const result = collectAttachment(
      "0xWorker1",
      "https://cdn.example.com/img.jpg",
      "image/jpeg"
    );
    expect(result).toBe(true);
    const draft = getActiveDraft("0xWorker1")!;
    expect(draft.pieces[0].collected).toBe(true);
    expect(draft.pieces[0].fileUrl).toBe("https://cdn.example.com/img.jpg");
  });

  it("rejects wrong mime type — video on photo piece", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "photo", description: "Photo proof", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const result = collectAttachment(
      "0xWorker1",
      "https://cdn.example.com/vid.mp4",
      "video/mp4"
    );
    expect(result).toBe(false);
  });

  it("rejects attachment for text piece", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "text", description: "Write something", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const result = collectAttachment(
      "0xWorker1",
      "https://cdn.example.com/img.jpg",
      "image/jpeg"
    );
    expect(result).toBe(false);
  });

  it("collects video attachment on video piece", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "video", description: "Video proof", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const result = collectAttachment(
      "0xWorker1",
      "https://cdn.example.com/vid.mp4",
      "video/mp4"
    );
    expect(result).toBe(true);
  });

  it("collects document attachment on document piece", async () => {
    const task = makeTask({
      evidence_requirements: [
        { type: "document", description: "Upload PDF", required: true },
      ],
    });
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx = mockCtx("0xWorker1");
    await startSubmission(ctx, "task-uuid-12345678");

    const result = collectAttachment(
      "0xWorker1",
      "https://cdn.example.com/doc.pdf",
      "application/pdf"
    );
    expect(result).toBe(true);
  });
});

describe("Submit Command — Full Submission Flow Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearDraft("0xWorker1");
    mockStore.getByAddress.mockReturnValue({
      xmtpAddress: "0xworker1",
      executorId: "exec-1",
      conversationState: "submission",
    });
  });

  it("completes end-to-end: text → photo → GPS → submit", async () => {
    const task = makeTask(); // 3 pieces: text(req), photo(req), gps(opt)
    mockResolveTask.mockResolvedValueOnce(task);
    const ctx1 = mockCtx("0xWorker1");
    await startSubmission(ctx1, "task-uuid-12345678");

    // Step 1: Fill text piece
    const ctx2 = mockCtx("0xWorker1");
    await handleSubmissionText(
      ctx2,
      "0xWorker1",
      "I went to the location and completed the task."
    );
    let draft = getActiveDraft("0xWorker1")!;
    expect(draft.pieces[0].collected).toBe(true);
    expect(draft.currentPieceIndex).toBe(1);

    // Step 2: Fill photo via attachment
    collectAttachment(
      "0xWorker1",
      "https://cdn.example.com/proof.jpg",
      "image/jpeg"
    );
    draft = getActiveDraft("0xWorker1")!;
    expect(draft.pieces[1].collected).toBe(true);

    // Step 3: Skip optional GPS
    const ctx3 = mockCtx("0xWorker1");
    // Advance to GPS piece manually (attachment doesn't auto-advance without ctx)
    draft.currentPieceIndex = 2;
    await handleSubmissionSkip(ctx3, "0xWorker1");

    // Step 4: Submit
    mockSubmitEvidence.mockResolvedValueOnce({ ok: true });
    // After skip of the last piece, compileAndSubmit should be called automatically
    // Verify the submission happened
    expect(mockSubmitEvidence).toHaveBeenCalledWith(
      "task-uuid-12345678",
      "exec-1",
      expect.objectContaining({
        text: "I went to the location and completed the task.",
        photo: "https://cdn.example.com/proof.jpg",
      })
    );
  });
});
