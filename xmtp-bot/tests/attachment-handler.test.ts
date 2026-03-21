import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock dependencies ────────────────────────────────────────

const mockGetActiveDraft = vi.fn();
const mockAdvanceToNextPiece = vi.fn().mockResolvedValue(false);
const mockCollectAttachment = vi.fn().mockReturnValue(true);
const mockIsSubmissionTimedOut = vi.fn().mockReturnValue(false);
const mockClearDraft = vi.fn();

vi.mock("../src/submission/flow.js", () => ({
  getActiveDraft: (...args: any[]) => mockGetActiveDraft(...args),
  advanceToNextPiece: (...args: any[]) => mockAdvanceToNextPiece(...args),
  collectAttachment: (...args: any[]) => mockCollectAttachment(...args),
  isSubmissionTimedOut: (...args: any[]) => mockIsSubmissionTimedOut(...args),
  clearDraft: (...args: any[]) => mockClearDraft(...args),
}));

const mockResetConversation = vi.fn();
vi.mock("../src/services/worker-store.js", () => ({
  getWorkerStore: () => ({
    resetConversation: mockResetConversation,
  }),
}));

const mockGetPresignedUploadUrl = vi.fn().mockResolvedValue("https://s3.example.com/presigned");
const mockUploadToS3 = vi.fn().mockResolvedValue("https://cdn.example.com/evidence.jpg");

vi.mock("../src/services/api-client.js", () => ({
  apiClient: {
    getPresignedUploadUrl: (...args: any[]) => mockGetPresignedUploadUrl(...args),
    uploadToS3: (...args: any[]) => mockUploadToS3(...args),
  },
}));

const mockDownloadRemoteAttachment = vi.fn().mockResolvedValue({
  mimeType: "image/jpeg",
  content: new Uint8Array(1024),
  filename: "photo.jpg",
});

vi.mock("@xmtp/agent-sdk", () => ({
  downloadRemoteAttachment: (...args: any[]) => mockDownloadRemoteAttachment(...args),
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

import { handleAttachment } from "../src/submission/attachment-handler.js";

// ── Helper to create mock MessageContext ─────────────────────

function createMockCtx(senderAddress: string | null = "0xSender") {
  return {
    getSenderAddress: vi.fn().mockResolvedValue(senderAddress),
    sendTextReply: vi.fn().mockResolvedValue(undefined),
    message: {
      content: { url: "https://xmtp.example.com/attachment" },
    },
  } as any;
}

function createDraft(overrides: any = {}) {
  return {
    taskId: "task-att-001",
    executorId: "exec-001",
    currentPieceIndex: 0,
    pieces: [
      { type: "photo", label: "Front photo", required: true, value: null },
      { type: "text_response", label: "Description", required: true, value: null },
    ],
    startedAt: Date.now(),
    ...overrides,
  };
}

describe("attachment-handler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does nothing when no sender address", async () => {
    const ctx = createMockCtx(null);

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).not.toHaveBeenCalled();
  });

  it("tells user to start submission when no draft", async () => {
    mockGetActiveDraft.mockReturnValue(null);
    const ctx = createMockCtx();

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("/submit"),
    );
  });

  it("clears draft on timeout", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(true);
    const ctx = createMockCtx();

    await handleAttachment(ctx);

    expect(mockClearDraft).toHaveBeenCalledWith("0xSender");
    expect(mockResetConversation).toHaveBeenCalledWith("0xSender");
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("expirada"),
    );
  });

  it("rejects attachment when current piece expects text", async () => {
    const draft = createDraft({
      currentPieceIndex: 1, // text_response piece
    });
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("text_response"),
    );
  });

  it("downloads, validates, uploads and collects a photo attachment", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "image/jpeg",
      content: new Uint8Array(2048),
      filename: "evidence_photo.jpg",
    });

    await handleAttachment(ctx);

    expect(mockDownloadRemoteAttachment).toHaveBeenCalled();
    expect(mockGetPresignedUploadUrl).toHaveBeenCalledWith(
      "evidence_photo.jpg",
      "image/jpeg",
      "task-att-001",
      "exec-001",
    );
    expect(mockUploadToS3).toHaveBeenCalled();
    expect(mockCollectAttachment).toHaveBeenCalledWith(
      "0xSender",
      "https://cdn.example.com/evidence.jpg",
      "image/jpeg",
    );
    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Archivo recibido"),
    );
  });

  it("rejects invalid MIME type for photo", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "application/pdf",
      content: new Uint8Array(512),
      filename: "doc.pdf",
    });

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Tipo de archivo no valido"),
    );
    expect(mockCollectAttachment).not.toHaveBeenCalled();
  });

  it("accepts video/mp4 for video piece type", async () => {
    const draft = createDraft({
      pieces: [{ type: "video", label: "Video", required: true, value: null }],
    });
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "video/mp4",
      content: new Uint8Array(4096),
      filename: "clip.mp4",
    });

    await handleAttachment(ctx);

    expect(mockCollectAttachment).toHaveBeenCalled();
  });

  it("accepts PDF for document piece type", async () => {
    const draft = createDraft({
      pieces: [{ type: "document", label: "Receipt", required: true, value: null }],
    });
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "application/pdf",
      content: new Uint8Array(1024),
      filename: "receipt.pdf",
    });

    await handleAttachment(ctx);

    expect(mockCollectAttachment).toHaveBeenCalled();
  });

  it("rejects file exceeding 25MB", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "image/jpeg",
      content: new Uint8Array(26 * 1024 * 1024), // 26MB
      filename: "huge.jpg",
    });

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("muy grande"),
    );
    expect(mockCollectAttachment).not.toHaveBeenCalled();
  });

  it("generates filename when attachment has none", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "image/png",
      content: new Uint8Array(512),
      filename: undefined,
    });

    await handleAttachment(ctx);

    expect(mockGetPresignedUploadUrl).toHaveBeenCalledWith(
      expect.stringMatching(/^evidence_\d+\.png$/),
      "image/png",
      "task-att-001",
      "exec-001",
    );
  });

  it("handles collectAttachment failure", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    mockCollectAttachment.mockReturnValueOnce(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "image/jpeg",
      content: new Uint8Array(512),
      filename: "photo.jpg",
    });

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Error actualizando"),
    );
  });

  it("notifies when all pieces collected", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    mockAdvanceToNextPiece.mockResolvedValueOnce(true);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "image/jpeg",
      content: new Uint8Array(512),
      filename: "last_photo.jpg",
    });

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("/done"),
    );
  });

  it("handles download error gracefully", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    mockDownloadRemoteAttachment.mockRejectedValueOnce(
      new Error("Network error"),
    );

    await handleAttachment(ctx);

    expect(ctx.sendTextReply).toHaveBeenCalledWith(
      expect.stringContaining("Error procesando"),
    );
  });

  it("accepts image/* broadly via fallback for photo type", async () => {
    const draft = createDraft();
    mockGetActiveDraft.mockReturnValue(draft);
    mockIsSubmissionTimedOut.mockReturnValue(false);
    const ctx = createMockCtx();

    // image/gif is not in the explicit allow list but starts with "image/"
    mockDownloadRemoteAttachment.mockResolvedValueOnce({
      mimeType: "image/gif",
      content: new Uint8Array(256),
      filename: "anim.gif",
    });

    await handleAttachment(ctx);

    expect(mockCollectAttachment).toHaveBeenCalled();
  });
});
