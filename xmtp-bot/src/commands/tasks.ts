import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { formatUsdc, formatDeadline, shortId, truncate } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

export async function handleTasks(
  ctx: MessageContext<string>,
  args: string[]
): Promise<void> {
  try {
    const category = args[0];
    const params: Record<string, string> = { status: "published", limit: "10" };
    if (category) params.category = category;

    const data = await apiClient.get<any>("/api/v1/tasks", { params });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      await ctx.sendTextReply("No hay tareas disponibles en este momento.");
      return;
    }

    const lines = ["**Tareas disponibles:**\n"];
    for (const t of tasks) {
      lines.push(
        `- \`${shortId(t.id)}\` **${truncate(t.title, 40)}** — $${formatUsdc(t.bounty_usdc ?? t.bounty)} USDC — ${formatDeadline(t.deadline)}`
      );
    }
    lines.push("\nUsa `/apply <id>` para aplicar.");
    await ctx.sendMarkdownReply(lines.join("\n"));
  } catch (err) {
    logger.error({ err }, "Failed to fetch tasks");
    await ctx.sendTextReply("Error al obtener tareas. Intenta de nuevo.");
  }
}
