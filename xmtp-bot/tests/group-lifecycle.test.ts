import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock group-manager ───────────────────────────────────────

const mockSendGroupMessage = vi.fn().mockResolvedValue(undefined);
const mockUpdateGroupStatus = vi.fn().mockResolvedValue(undefined);
const mockArchiveGroup = vi.fn().mockResolvedValue(undefined);
const mockScheduleAutoArchive = vi.fn();

const mockTaskGroup = {
  taskId: "task-lc-001",
  groupId: "group-lc-001",
  taskTitle: "Lifecycle Test Task",
  bounty: "5.00",
  chain: "base",
  members: [{ walletAddress: "0xWorker", role: "worker", joinedAt: "2026-03-19T00:00:00Z" }],
  status: "active" as const,
  createdAt: "2026-03-19T00:00:00Z",
};

vi.mock("../src/services/group-manager.js", () => ({
  getTaskGroup: vi.fn((taskId: string) =>
    taskId === "task-lc-001" ? mockTaskGroup : undefined,
  ),
  updateGroupStatus: (...args: any[]) => mockUpdateGroupStatus(...args),
  sendGroupMessage: (...args: any[]) => mockSendGroupMessage(...args),
  archiveGroup: (...args: any[]) => mockArchiveGroup(...args),
  scheduleAutoArchive: (...args: any[]) => mockScheduleAutoArchive(...args),
}));

vi.mock("../src/utils/formatters.js", () => ({
  formatUsdc: (v: number | string) => {
    const n = typeof v === "string" ? parseFloat(v) : v;
    return n.toFixed(2);
  },
  txLink: (chain: string, hash: string) => `https://${chain}scan.org/tx/${hash}`,
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
}));

import {
  onTaskStatusChanged,
  onEvidenceSubmitted,
  onSubmissionApproved,
  onSubmissionRejected,
  onRatingReceived,
} from "../src/services/group-lifecycle.js";

describe("group-lifecycle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("onTaskStatusChanged", () => {
    it("handles in_progress → sends message + updates status", async () => {
      await onTaskStatusChanged("task-lc-001", "in_progress");

      expect(mockUpdateGroupStatus).toHaveBeenCalledWith(
        "task-lc-001",
        "active",
        "EN PROGRESO",
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("en progreso"),
      );
    });

    it("handles submitted → shows evidence sent message", async () => {
      await onTaskStatusChanged("task-lc-001", "submitted");

      expect(mockUpdateGroupStatus).toHaveBeenCalledWith(
        "task-lc-001",
        "submitted",
        "EVIDENCIA ENVIADA",
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Evidencia enviada"),
      );
    });

    it("handles completed → sends payment info + schedules archive", async () => {
      await onTaskStatusChanged("task-lc-001", "completed", {
        tx_hash: "0xabc123",
        payment_network: "base",
      });

      expect(mockUpdateGroupStatus).toHaveBeenCalledWith(
        "task-lc-001",
        "completed",
        "COMPLETADA",
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Tarea Completada"),
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("0xabc123"),
      );
      expect(mockScheduleAutoArchive).toHaveBeenCalledWith("task-lc-001");
    });

    it("handles completed without tx_hash", async () => {
      await onTaskStatusChanged("task-lc-001", "completed");

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("5.00 USDC"),
      );
      expect(mockScheduleAutoArchive).toHaveBeenCalled();
    });

    it("handles disputed → shows dispute message", async () => {
      await onTaskStatusChanged("task-lc-001", "disputed");

      expect(mockUpdateGroupStatus).toHaveBeenCalledWith(
        "task-lc-001",
        "active",
        "EN DISPUTA",
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Disputa abierta"),
      );
    });

    it("handles cancelled → sends message + archives", async () => {
      await onTaskStatusChanged("task-lc-001", "cancelled");

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Tarea cancelada"),
      );
      expect(mockArchiveGroup).toHaveBeenCalledWith(
        "task-lc-001",
        "Tarea cancelada.",
      );
    });

    it("handles expired → sends message + archives", async () => {
      await onTaskStatusChanged("task-lc-001", "expired");

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Tarea expirada"),
      );
      expect(mockArchiveGroup).toHaveBeenCalledWith(
        "task-lc-001",
        "Tarea expirada.",
      );
    });

    it("does nothing for unknown taskId", async () => {
      await onTaskStatusChanged("unknown-task", "in_progress");

      expect(mockUpdateGroupStatus).not.toHaveBeenCalled();
      expect(mockSendGroupMessage).not.toHaveBeenCalled();
    });

    it("handles unknown status (no-op switch fallthrough)", async () => {
      await onTaskStatusChanged("task-lc-001", "some_new_status");

      // Should not throw, no messages sent
      expect(mockUpdateGroupStatus).not.toHaveBeenCalled();
      expect(mockSendGroupMessage).not.toHaveBeenCalled();
    });
  });

  describe("onEvidenceSubmitted", () => {
    it("sends evidence count message", async () => {
      await onEvidenceSubmitted("task-lc-001", { piece_count: 3 });

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("3 piezas"),
      );
    });

    it("uses evidence_count fallback", async () => {
      await onEvidenceSubmitted("task-lc-001", { evidence_count: 5 });

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("5 piezas"),
      );
    });

    it("shows ? when no count provided", async () => {
      await onEvidenceSubmitted("task-lc-001");

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("? piezas"),
      );
    });

    it("does nothing for unknown taskId", async () => {
      await onEvidenceSubmitted("ghost-task", { piece_count: 1 });

      expect(mockSendGroupMessage).not.toHaveBeenCalled();
    });
  });

  describe("onSubmissionApproved", () => {
    it("sends approval with amount from data", async () => {
      await onSubmissionApproved("task-lc-001", { amount: 4.35 });

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Evidencia aprobada"),
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("4.35"),
      );
    });

    it("falls back to group bounty when no amount", async () => {
      await onSubmissionApproved("task-lc-001");

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("5.00"),
      );
    });

    it("does nothing for unknown taskId", async () => {
      await onSubmissionApproved("unknown-task");
      expect(mockSendGroupMessage).not.toHaveBeenCalled();
    });
  });

  describe("onSubmissionRejected", () => {
    it("sends rejection with reason", async () => {
      await onSubmissionRejected("task-lc-001", "Photo is blurry");

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Evidencia rechazada"),
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Photo is blurry"),
      );
    });

    it("sends rejection without reason", async () => {
      await onSubmissionRejected("task-lc-001");

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Evidencia rechazada"),
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("puede reenviar"),
      );
    });

    it("does nothing for unknown taskId", async () => {
      await onSubmissionRejected("unknown");
      expect(mockSendGroupMessage).not.toHaveBeenCalled();
    });
  });

  describe("onRatingReceived", () => {
    it("shows stars for worker rating", async () => {
      await onRatingReceived("task-lc-001", {
        score: 4,
        from_role: "worker",
        comment: "Good agent!",
      });

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("★★★★☆"),
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Worker"),
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Good agent!"),
      );
    });

    it("shows stars for agent rating", async () => {
      await onRatingReceived("task-lc-001", {
        score: 5,
        from_role: "agent",
      });

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("★★★★★"),
      );
      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("Agente"),
      );
    });

    it("handles 0 score", async () => {
      await onRatingReceived("task-lc-001", { from_role: "worker" });

      expect(mockSendGroupMessage).toHaveBeenCalledWith(
        "task-lc-001",
        expect.stringContaining("☆☆☆☆☆"),
      );
    });

    it("does nothing for unknown taskId", async () => {
      await onRatingReceived("unknown");
      expect(mockSendGroupMessage).not.toHaveBeenCalled();
    });
  });
});
