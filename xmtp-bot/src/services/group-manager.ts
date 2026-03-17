import { getAgent } from "../agent.js";
import { formatUsdc, shortId } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";
import type { Group } from "@xmtp/agent-sdk";

// ─── Types ───────────────────────────────────────────────────

interface GroupMember {
  walletAddress: string;
  role: "worker" | "agent" | "observer";
  joinedAt: string;
}

interface TaskGroup {
  taskId: string;
  groupId: string;
  taskTitle: string;
  bounty: string;
  chain: string;
  members: GroupMember[];
  agentAddress?: string;
  status: "active" | "submitted" | "completed" | "archived";
  createdAt: string;
}

// ─── Group Manager ──────────────────────────────────────────

const activeGroups = new Map<string, TaskGroup>();
const ARCHIVE_DELAY_MS = 72 * 60 * 60 * 1000; // 72 hours

export function getTaskGroup(taskId: string): TaskGroup | undefined {
  return activeGroups.get(taskId);
}

export function getAllActiveGroups(): TaskGroup[] {
  return Array.from(activeGroups.values()).filter(
    (g) => g.status === "active" || g.status === "submitted",
  );
}

/**
 * XMTP-5.1: Create a group chat when a task is assigned.
 */
export async function createTaskGroup(opts: {
  taskId: string;
  taskTitle: string;
  bounty: string | number;
  chain: string;
  workerAddress: string;
  agentAddress?: string;
}): Promise<TaskGroup | null> {
  try {
    // Don't create duplicate groups
    if (activeGroups.has(opts.taskId)) {
      logger.warn({ taskId: opts.taskId }, "Task group already exists");
      return activeGroups.get(opts.taskId)!;
    }

    const agent = getAgent();
    const members: `0x${string}`[] = [opts.workerAddress as `0x${string}`];
    if (opts.agentAddress) {
      members.push(opts.agentAddress as `0x${string}`);
    }

    const bountyStr =
      typeof opts.bounty === "number" ? formatUsdc(opts.bounty) : opts.bounty;

    const group = await agent.createGroupWithAddresses(members, {
      groupName: `EM: ${opts.taskTitle.slice(0, 40)}`,
      groupDescription: `Bounty: ${bountyStr} USDC (${opts.chain}) | Task: ${shortId(opts.taskId)}`,
    });

    const taskGroup: TaskGroup = {
      taskId: opts.taskId,
      groupId: group.id,
      taskTitle: opts.taskTitle,
      bounty: bountyStr,
      chain: opts.chain,
      members: [
        {
          walletAddress: opts.workerAddress,
          role: "worker",
          joinedAt: new Date().toISOString(),
        },
        ...(opts.agentAddress
          ? [
              {
                walletAddress: opts.agentAddress,
                role: "agent" as const,
                joinedAt: new Date().toISOString(),
              },
            ]
          : []),
      ],
      agentAddress: opts.agentAddress,
      status: "active",
      createdAt: new Date().toISOString(),
    };

    activeGroups.set(opts.taskId, taskGroup);

    // Welcome message
    await group.sendText(
      `Grupo de Tarea — ${opts.taskTitle}\n\n` +
        `Bounty: ${bountyStr} USDC (${opts.chain})\n` +
        `Worker: ${opts.workerAddress.slice(0, 10)}...\n\n` +
        `Comandos en grupo: /status, /help`,
    );

    logger.info(
      { taskId: opts.taskId, groupId: group.id, members: members.length },
      "Task group created",
    );
    return taskGroup;
  } catch (err) {
    logger.error({ err, taskId: opts.taskId }, "Failed to create task group");
    return null;
  }
}

/**
 * XMTP-5.2: Update group metadata when task status changes.
 */
export async function updateGroupStatus(
  taskId: string,
  newStatus: TaskGroup["status"],
  statusLabel?: string,
): Promise<void> {
  const taskGroup = activeGroups.get(taskId);
  if (!taskGroup) return;

  taskGroup.status = newStatus;

  try {
    const agent = getAgent();
    const ctx = await agent.getConversationContext(taskGroup.groupId);
    if (!ctx || !ctx.isGroup()) return;

    const group = ctx.conversation;
    const label = statusLabel ?? newStatus.toUpperCase();
    await group.updateName(`[${label}] ${taskGroup.taskTitle.slice(0, 35)}`);

    logger.info({ taskId, status: newStatus }, "Group status updated");
  } catch (err) {
    logger.error({ err, taskId }, "Failed to update group status");
  }
}

/**
 * Send a message to a task's group chat.
 */
export async function sendGroupMessage(
  taskId: string,
  text: string,
): Promise<void> {
  const taskGroup = activeGroups.get(taskId);
  if (!taskGroup) return;

  try {
    const agent = getAgent();
    const ctx = await agent.getConversationContext(taskGroup.groupId);
    if (!ctx) return;

    await ctx.conversation.sendText(text);
  } catch (err) {
    logger.error({ err, taskId }, "Failed to send group message");
  }
}

/**
 * XMTP-5.5: Archive a group after task completion + ratings or 72h timeout.
 */
export async function archiveGroup(
  taskId: string,
  summary?: string,
): Promise<void> {
  const taskGroup = activeGroups.get(taskId);
  if (!taskGroup || taskGroup.status === "archived") return;

  taskGroup.status = "archived";

  try {
    const agent = getAgent();
    const ctx = await agent.getConversationContext(taskGroup.groupId);
    if (!ctx || !ctx.isGroup()) return;

    const group = ctx.conversation;

    // Send summary
    const summaryText =
      summary ??
      `Tarea completada.\n\n` +
        `Bounty: ${taskGroup.bounty} USDC (${taskGroup.chain})\n` +
        `Workers: ${taskGroup.members.filter((m) => m.role === "worker").length}\n\n` +
        `Este grupo sera archivado.`;

    await group.sendText(summaryText);
    await group.updateName(
      `[ARCHIVADO] ${taskGroup.taskTitle.slice(0, 30)}`,
    );

    logger.info({ taskId, groupId: taskGroup.groupId }, "Group archived");
  } catch (err) {
    logger.error({ err, taskId }, "Failed to archive group");
  }

  // Remove from active tracking after a delay
  setTimeout(() => {
    activeGroups.delete(taskId);
  }, 60_000);
}

/**
 * Schedule auto-archive after 72 hours.
 */
export function scheduleAutoArchive(taskId: string): void {
  const timer = setTimeout(() => {
    const group = activeGroups.get(taskId);
    if (group && group.status !== "archived") {
      archiveGroup(taskId, "Grupo archivado automaticamente (72h timeout).");
    }
  }, ARCHIVE_DELAY_MS);

  // Allow the process to exit without waiting for this timer
  if (timer.unref) {
    timer.unref();
  }
}

/**
 * XMTP-5.6: Add additional workers to an existing task group.
 */
export async function addWorkerToGroup(
  taskId: string,
  workerAddress: string,
): Promise<boolean> {
  const taskGroup = activeGroups.get(taskId);
  if (!taskGroup) return false;

  // Check if already a member
  if (
    taskGroup.members.some(
      (m) => m.walletAddress.toLowerCase() === workerAddress.toLowerCase(),
    )
  ) {
    return true; // Already in group
  }

  try {
    const agent = getAgent();
    const ctx = await agent.getConversationContext(taskGroup.groupId);
    if (!ctx || !ctx.isGroup()) return false;

    const group = ctx.conversation;
    await agent.addMembersWithAddresses(group, [
      workerAddress as `0x${string}`,
    ]);

    taskGroup.members.push({
      walletAddress: workerAddress,
      role: "worker",
      joinedAt: new Date().toISOString(),
    });

    await group.sendText(
      `Nuevo worker agregado: ${workerAddress.slice(0, 10)}...`,
    );

    logger.info({ taskId, worker: workerAddress }, "Worker added to group");
    return true;
  } catch (err) {
    logger.error(
      { err, taskId, worker: workerAddress },
      "Failed to add worker to group",
    );
    return false;
  }
}

export type { TaskGroup, GroupMember };
