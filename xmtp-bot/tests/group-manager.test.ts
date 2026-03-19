import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ── Mock agent before imports ─────────────────────────────────

const mockGroup = {
  id: "group-abc",
  sendText: vi.fn().mockResolvedValue(undefined),
  updateName: vi.fn().mockResolvedValue(undefined),
};

const mockConversationCtx = {
  isGroup: () => true,
  conversation: mockGroup,
};

const mockAgent = {
  address: "0xBotAddress",
  createGroupWithAddresses: vi.fn().mockResolvedValue(mockGroup),
  getConversationContext: vi.fn().mockResolvedValue(mockConversationCtx),
  addMembersWithAddresses: vi.fn().mockResolvedValue(undefined),
};

vi.mock("../src/agent.js", () => ({
  getAgent: () => mockAgent,
}));

vi.mock("../src/utils/logger.js", () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import {
  getTaskGroup,
  getAllActiveGroups,
  createTaskGroup,
  updateGroupStatus,
  sendGroupMessage,
  archiveGroup,
  scheduleAutoArchive,
  addWorkerToGroup,
} from "../src/services/group-manager.js";

describe("group-manager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear internal activeGroups map by archiving any leftover
    // (we test fresh state by creating new groups)
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("createTaskGroup", () => {
    it("creates a new group and stores it", async () => {
      const result = await createTaskGroup({
        taskId: "task-001",
        taskTitle: "Buy coffee from shop",
        bounty: 5.0,
        chain: "base",
        workerAddress: "0xWorker123",
        agentAddress: "0xAgent456",
      });

      expect(result).not.toBeNull();
      expect(result!.taskId).toBe("task-001");
      expect(result!.bounty).toBe("5.00");
      expect(result!.chain).toBe("base");
      expect(result!.status).toBe("active");
      expect(result!.members).toHaveLength(2);
      expect(result!.members[0].role).toBe("worker");
      expect(result!.members[1].role).toBe("agent");

      expect(mockAgent.createGroupWithAddresses).toHaveBeenCalledWith(
        ["0xWorker123", "0xAgent456"],
        expect.objectContaining({
          groupName: expect.stringContaining("Buy coffee"),
        }),
      );
      expect(mockGroup.sendText).toHaveBeenCalledWith(
        expect.stringContaining("Grupo de Tarea"),
      );
    });

    it("accepts string bounty", async () => {
      const result = await createTaskGroup({
        taskId: "task-002",
        taskTitle: "Another task",
        bounty: "3.50",
        chain: "polygon",
        workerAddress: "0xWorkerABC",
      });

      expect(result!.bounty).toBe("3.50");
      expect(result!.members).toHaveLength(1); // no agent
    });

    it("returns existing group on duplicate taskId", async () => {
      await createTaskGroup({
        taskId: "task-dup",
        taskTitle: "First",
        bounty: 1,
        chain: "base",
        workerAddress: "0xW1",
      });

      mockAgent.createGroupWithAddresses.mockClear();

      const dup = await createTaskGroup({
        taskId: "task-dup",
        taskTitle: "Second try",
        bounty: 2,
        chain: "ethereum",
        workerAddress: "0xW2",
      });

      // Should return original, not create new
      expect(dup!.taskTitle).toBe("First");
      expect(mockAgent.createGroupWithAddresses).not.toHaveBeenCalled();
    });

    it("returns null on agent error", async () => {
      mockAgent.createGroupWithAddresses.mockRejectedValueOnce(
        new Error("XMTP down"),
      );

      const result = await createTaskGroup({
        taskId: "task-fail",
        taskTitle: "Will fail",
        bounty: 1,
        chain: "base",
        workerAddress: "0xWF",
      });

      expect(result).toBeNull();
    });

    it("truncates long task titles in group name", async () => {
      const longTitle = "A".repeat(100);
      await createTaskGroup({
        taskId: "task-long",
        taskTitle: longTitle,
        bounty: 1,
        chain: "base",
        workerAddress: "0xWL",
      });

      expect(mockAgent.createGroupWithAddresses).toHaveBeenCalledWith(
        expect.any(Array),
        expect.objectContaining({
          groupName: expect.stringMatching(/^EM: A{40}$/),
        }),
      );
    });
  });

  describe("getTaskGroup", () => {
    it("returns undefined for non-existent taskId", () => {
      expect(getTaskGroup("nonexistent")).toBeUndefined();
    });

    it("returns the group after creation", async () => {
      await createTaskGroup({
        taskId: "task-get-1",
        taskTitle: "Get me",
        bounty: 2,
        chain: "base",
        workerAddress: "0xGet",
      });

      const group = getTaskGroup("task-get-1");
      expect(group).toBeDefined();
      expect(group!.taskTitle).toBe("Get me");
    });
  });

  describe("getAllActiveGroups", () => {
    it("returns only active/submitted groups", async () => {
      await createTaskGroup({
        taskId: "task-active-1",
        taskTitle: "Active",
        bounty: 1,
        chain: "base",
        workerAddress: "0xA1",
      });

      await createTaskGroup({
        taskId: "task-active-2",
        taskTitle: "Active2",
        bounty: 1,
        chain: "base",
        workerAddress: "0xA2",
      });

      const active = getAllActiveGroups();
      const found = active.filter(
        (g) =>
          g.taskId === "task-active-1" || g.taskId === "task-active-2",
      );
      expect(found.length).toBe(2);
    });
  });

  describe("updateGroupStatus", () => {
    it("updates internal status and renames group", async () => {
      await createTaskGroup({
        taskId: "task-upd",
        taskTitle: "Update me",
        bounty: 5,
        chain: "base",
        workerAddress: "0xUpd",
      });

      await updateGroupStatus("task-upd", "submitted", "EVIDENCIA ENVIADA");

      const group = getTaskGroup("task-upd");
      expect(group!.status).toBe("submitted");

      expect(mockGroup.updateName).toHaveBeenCalledWith(
        expect.stringContaining("EVIDENCIA ENVIADA"),
      );
    });

    it("does nothing for unknown taskId", async () => {
      await updateGroupStatus("unknown-task", "completed");
      expect(mockGroup.updateName).not.toHaveBeenCalled();
    });

    it("uses default label from status when no label provided", async () => {
      await createTaskGroup({
        taskId: "task-upd2",
        taskTitle: "Default label",
        bounty: 1,
        chain: "base",
        workerAddress: "0xU2",
      });

      await updateGroupStatus("task-upd2", "completed");

      expect(mockGroup.updateName).toHaveBeenCalledWith(
        expect.stringContaining("COMPLETED"),
      );
    });
  });

  describe("sendGroupMessage", () => {
    it("sends text to the group conversation", async () => {
      await createTaskGroup({
        taskId: "task-msg",
        taskTitle: "Message test",
        bounty: 1,
        chain: "base",
        workerAddress: "0xMsg",
      });

      const ctx = { conversation: { sendText: vi.fn() } };
      mockAgent.getConversationContext.mockResolvedValueOnce(ctx);

      await sendGroupMessage("task-msg", "Hello workers!");

      expect(ctx.conversation.sendText).toHaveBeenCalledWith("Hello workers!");
    });

    it("does nothing for unknown taskId", async () => {
      await sendGroupMessage("ghost-task", "Nobody hears this");
      // Should not throw
    });
  });

  describe("archiveGroup", () => {
    it("archives the group with summary", async () => {
      vi.useFakeTimers();

      await createTaskGroup({
        taskId: "task-archive",
        taskTitle: "Archive me",
        bounty: 1,
        chain: "base",
        workerAddress: "0xArc",
      });

      await archiveGroup("task-archive", "Done and done.");

      const group = getTaskGroup("task-archive");
      expect(group!.status).toBe("archived");

      expect(mockGroup.updateName).toHaveBeenCalledWith(
        expect.stringContaining("ARCHIVADO"),
      );

      vi.useRealTimers();
    });

    it("does nothing if already archived", async () => {
      await createTaskGroup({
        taskId: "task-arc2",
        taskTitle: "Double archive",
        bounty: 1,
        chain: "base",
        workerAddress: "0xArc2",
      });

      await archiveGroup("task-arc2", "First");
      mockGroup.updateName.mockClear();

      await archiveGroup("task-arc2", "Second");
      // Should not call updateName again
      expect(mockGroup.updateName).not.toHaveBeenCalled();
    });
  });

  describe("scheduleAutoArchive", () => {
    it("schedules archive after 72 hours", async () => {
      vi.useFakeTimers();

      await createTaskGroup({
        taskId: "task-auto-arc",
        taskTitle: "Auto archive",
        bounty: 1,
        chain: "base",
        workerAddress: "0xAutoArc",
      });

      scheduleAutoArchive("task-auto-arc");

      // Status still active before timer
      expect(getTaskGroup("task-auto-arc")!.status).toBe("active");

      // Advance 72 hours
      await vi.advanceTimersByTimeAsync(72 * 60 * 60 * 1000 + 1);

      // Should be archived
      expect(getTaskGroup("task-auto-arc")!.status).toBe("archived");

      vi.useRealTimers();
    });
  });

  describe("addWorkerToGroup", () => {
    it("adds a new worker to an existing group", async () => {
      await createTaskGroup({
        taskId: "task-add",
        taskTitle: "Add worker",
        bounty: 1,
        chain: "base",
        workerAddress: "0xW1",
      });

      const ctx = {
        isGroup: () => true,
        conversation: mockGroup,
      };
      mockAgent.getConversationContext.mockResolvedValueOnce(ctx);

      const success = await addWorkerToGroup("task-add", "0xW2");
      expect(success).toBe(true);

      const group = getTaskGroup("task-add");
      expect(group!.members).toHaveLength(2);
      expect(group!.members[1].walletAddress).toBe("0xW2");
    });

    it("returns true for already-existing member (case insensitive)", async () => {
      await createTaskGroup({
        taskId: "task-add-dup",
        taskTitle: "Dup add",
        bounty: 1,
        chain: "base",
        workerAddress: "0xw1abc",
      });

      const success = await addWorkerToGroup("task-add-dup", "0xW1ABC");
      expect(success).toBe(true);
    });

    it("returns false for unknown taskId", async () => {
      const success = await addWorkerToGroup("unknown", "0xW2");
      expect(success).toBe(false);
    });

    it("returns false on XMTP error", async () => {
      await createTaskGroup({
        taskId: "task-add-fail",
        taskTitle: "Fail add",
        bounty: 1,
        chain: "base",
        workerAddress: "0xWFail1",
      });

      const ctx = {
        isGroup: () => false,
        conversation: mockGroup,
      };
      mockAgent.getConversationContext.mockResolvedValueOnce(ctx);

      const success = await addWorkerToGroup("task-add-fail", "0xWFail2");
      expect(success).toBe(false);
    });
  });
});
