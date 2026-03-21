import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { formatUsdc, formatDeadline, shortId } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

export async function handleStatus(
  ctx: MessageContext<string>,
  args: string[]
): Promise<void> {
  if (args.length === 0) {
    await ctx.sendTextReply("Uso: /status <task-id>");
    return;
  }

  try {
    const task = await apiClient.resolveTask(args[0]);
    if (!task) {
      await ctx.sendTextReply(`No se encontro la tarea: ${args[0]}`);
      return;
    }

    const lines = [
      `**Tarea: ${task.title}**\n`,
      `| Campo | Valor |`,
      `|-------|-------|`,
      `| ID | \`${shortId(task.id)}\` |`,
      `| Estado | ${task.status} |`,
      `| Bounty | $${formatUsdc(task.bounty_usdc ?? task.bounty)} USDC |`,
      `| Deadline | ${formatDeadline(task.deadline)} |`,
      `| Categoria | ${task.category ?? "—"} |`,
    ];

    if (task.executor_id) {
      lines.push(`| Executor | \`${shortId(task.executor_id)}\` |`);
    }

    await ctx.sendMarkdownReply(lines.join("\n"));
  } catch (err) {
    logger.error({ err, taskId: args[0] }, "Failed to get task status");
    await ctx.sendTextReply("Error al obtener estado. Intenta de nuevo.");
  }
}
