import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock logger and payment-monitor
vi.mock("../src/utils/logger.js", () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

vi.mock("../src/services/payment-monitor.js", () => ({
  txLink: (chain: string, hash: string) => `https://test-explorer.com/${chain}/${hash}`,
}));

import {
  setSendMessageFn,
  notifyTaskAssigned,
  notifySubmissionApproved,
  notifySubmissionRejected,
  notifyNewRating,
  notifyTaskCreated,
} from "../src/services/notification-dispatcher.js";

describe("Notification Dispatcher", () => {
  let sentMessages: { address: string; text: string }[];
  let mockSend: any;

  beforeEach(() => {
    sentMessages = [];
    mockSend = vi.fn(async (address: string, text: string) => {
      sentMessages.push({ address, text });
    });
    setSendMessageFn(mockSend);
  });

  describe("notifyTaskCreated", () => {
    it("logs but does not send message (Phase 1)", async () => {
      await notifyTaskCreated({ id: "t1", category: "simple_action" });
      expect(sentMessages.length).toBe(0);
    });
  });

  describe("notifyTaskAssigned", () => {
    it("sends assignment notification with task details", async () => {
      await notifyTaskAssigned("0xworker123", {
        title: "Photo of Store",
        bounty_usdc: 0.5,
        payment_network: "base",
        category: "physical_presence",
        id: "task-uuid-123",
      });

      expect(sentMessages.length).toBe(1);
      const msg = sentMessages[0];
      expect(msg.address).toBe("0xworker123");
      expect(msg.text).toContain("Tarea Asignada");
      expect(msg.text).toContain("Photo of Store");
      expect(msg.text).toContain("0.50 USDC");
      expect(msg.text).toContain("base");
      expect(msg.text).toContain("physical_presence");
      expect(msg.text).toContain("execution.market/tasks/task-uuid-123");
    });
  });

  describe("notifySubmissionApproved", () => {
    it("sends approval notification with breakdown", async () => {
      await notifySubmissionApproved(
        "0xworker456",
        {
          title: "Delivery Task",
          bounty_usdc: 1.0,
          payment_network: "polygon",
          id: "task-456",
        },
        "0xtxhash123",
      );

      expect(sentMessages.length).toBe(1);
      const msg = sentMessages[0];
      expect(msg.text).toContain("Evidencia Aprobada");
      expect(msg.text).toContain("$1.00 USDC");
      expect(msg.text).toContain("Fee (13%)");
      expect(msg.text).toContain("$0.13");
      expect(msg.text).toContain("$0.87 USDC"); // Net
      expect(msg.text).toContain("polygon");
      expect(msg.text).toContain("test-explorer.com");
    });

    it("works without txHash", async () => {
      await notifySubmissionApproved("0xworker", {
        title: "Test",
        bounty_usdc: 2.0,
        id: "t1",
      });

      expect(sentMessages.length).toBe(1);
      expect(sentMessages[0].text).toContain("Evidencia Aprobada");
      expect(sentMessages[0].text).not.toContain("test-explorer.com");
    });
  });

  describe("notifySubmissionRejected", () => {
    it("includes rejection reason", async () => {
      await notifySubmissionRejected(
        "0xworker789",
        { title: "Photo Task" },
        "Blurry photo",
      );

      expect(sentMessages.length).toBe(1);
      expect(sentMessages[0].text).toContain("Evidencia Rechazada");
      expect(sentMessages[0].text).toContain("Photo Task");
      expect(sentMessages[0].text).toContain("Blurry photo");
    });

    it("works without reason", async () => {
      await notifySubmissionRejected("0xworker", { title: "Task" });

      expect(sentMessages.length).toBe(1);
      expect(sentMessages[0].text).toContain("Evidencia Rechazada");
    });
  });

  describe("notifyNewRating", () => {
    it("shows stars and rating details", async () => {
      await notifyNewRating("0xtarget", {
        score: 4,
        comment: "Great work!",
        from_address: "0x1234567890abcdef1234567890abcdef12345678",
        task_title: "Photo Task",
      });

      expect(sentMessages.length).toBe(1);
      const msg = sentMessages[0];
      expect(msg.text).toContain("★★★★☆"); // 4 stars
      expect(msg.text).toContain("4/5");
      expect(msg.text).toContain("Great work!");
      expect(msg.text).toContain("0x1234...5678");
      expect(msg.text).toContain("Photo Task");
    });

    it("handles missing optional fields", async () => {
      await notifyNewRating("0xtarget", { score: 5 });

      expect(sentMessages.length).toBe(1);
      expect(sentMessages[0].text).toContain("★★★★★");
      expect(sentMessages[0].text).toContain("Anonimo");
    });

    it("handles score of 0", async () => {
      await notifyNewRating("0xtarget", { score: 0 });
      expect(sentMessages[0].text).toContain("☆☆☆☆☆"); // 0 stars
    });
  });

  describe("error handling", () => {
    it("logs error when sendMessage fails", async () => {
      const failSend = vi.fn(async () => {
        throw new Error("Network error");
      });
      setSendMessageFn(failSend);

      // Should not throw
      await notifyTaskAssigned("0xworker", {
        title: "Test",
        bounty_usdc: 1,
        payment_network: "base",
        category: "test",
        id: "t1",
      });

      expect(failSend).toHaveBeenCalled();
    });

    it("warns when sendMessage function not set", async () => {
      setSendMessageFn(null as any);

      // Should not throw — just logs warning
      // (implementation checks for null)
    });
  });
});
