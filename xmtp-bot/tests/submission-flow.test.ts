import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock config BEFORE any other imports that depend on it
vi.mock("../src/config.js", () => ({
  config: {
    em: {
      apiUrl: "https://api.test.local",
      apiKey: "test-key",
      wsUrl: "",
    },
    irc: { enabled: false },
    health: { port: 3000 },
    xmtp: { env: "dev", dbPath: "./data/xmtp/bot.db3" },
    log: { level: "silent" },
  },
}));

// Mock logger to avoid pino initialization issues
vi.mock("../src/utils/logger.js", () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    trace: vi.fn(),
  },
}));

// Mock api-client
vi.mock("../src/services/api-client.js", () => ({
  apiClient: {
    resolveTask: vi.fn(),
    submitEvidence: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    getPresignedUploadUrl: vi.fn(),
    uploadToS3: vi.fn(),
  },
}));

import {
  getActiveDraft,
  clearDraft,
  isSubmissionTimedOut,
  collectAttachment,
} from "../src/submission/flow.js";
import type { SubmissionDraft } from "../src/submission/types.js";

describe("Submission Flow - Draft Management", () => {
  it("returns undefined for non-existent draft", () => {
    expect(getActiveDraft("0x001")).toBeUndefined();
  });

  it("clears a draft without error", () => {
    clearDraft("0x001");
    expect(getActiveDraft("0x001")).toBeUndefined();
  });

  it("isSubmissionTimedOut returns true for old drafts", () => {
    const draft: SubmissionDraft = {
      taskId: "t1",
      taskTitle: "Test",
      executorId: "e1",
      pieces: [],
      currentPieceIndex: 0,
      startedAt: Date.now() - 31 * 60 * 1000, // 31 min ago
    };
    expect(isSubmissionTimedOut(draft)).toBe(true);
  });

  it("isSubmissionTimedOut returns false for fresh drafts", () => {
    const draft: SubmissionDraft = {
      taskId: "t1",
      taskTitle: "Test",
      executorId: "e1",
      pieces: [],
      currentPieceIndex: 0,
      startedAt: Date.now() - 5 * 60 * 1000, // 5 min ago
    };
    expect(isSubmissionTimedOut(draft)).toBe(false);
  });

  it("isSubmissionTimedOut boundary — exactly 30 min is not timed out", () => {
    const draft: SubmissionDraft = {
      taskId: "t1",
      taskTitle: "Test",
      executorId: "e1",
      pieces: [],
      currentPieceIndex: 0,
      startedAt: Date.now() - 30 * 60 * 1000, // exactly 30 min
    };
    // At exactly 30 min, Date.now() - startedAt == TIMEOUT, and > is false
    expect(isSubmissionTimedOut(draft)).toBe(false);
  });

  it("isSubmissionTimedOut boundary — 30 min + 1ms is timed out", () => {
    const draft: SubmissionDraft = {
      taskId: "t1",
      taskTitle: "Test",
      executorId: "e1",
      pieces: [],
      currentPieceIndex: 0,
      startedAt: Date.now() - (30 * 60 * 1000 + 1),
    };
    expect(isSubmissionTimedOut(draft)).toBe(true);
  });
});

describe("Submission Flow - collectAttachment", () => {
  it("returns false when no draft exists", () => {
    const result = collectAttachment(
      "0x001",
      "https://cdn.example.com/photo.jpg",
      "image/jpeg",
    );
    expect(result).toBe(false);
  });
});
