import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { getWorkerStore } from "../services/worker-store.js";
import { formatUsdc, shortId, truncate } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

export async function handleMyTasks(
  ctx: MessageContext<string>,
  _args: string[]
): Promise<void> {
  const senderAddress = await ctx.getSenderAddress();
  if (!senderAddress) {
    await ctx.sendTextReply("No se pudo resolver tu direccion.");
    return;
  }

  const store = getWorkerStore();
  const worker = store.getByAddress(senderAddress);
  if (!worker?.executorId) {
    await ctx.sendTextReply(
      "No estas registrado. Usa /register primero."
    );
    return;
  }

  try {
    const data = await apiClient.get<any>("/api/v1/tasks", {
      params: { executor_id: worker.executorId, limit: "20" },
    });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      await ctx.sendTextReply(
        "No tienes tareas activas. Usa /tasks para ver disponibles."
      );
      return;
    }

    const lines = ["**Mis tareas:**\n"];
    for (const t of tasks) {
      lines.push(
        `- \`${shortId(t.id)}\` [${t.status}] **${truncate(t.title, 35)}** — $${formatUsdc(t.bounty_usdc ?? t.bounty)}`
      );
    }
    await ctx.sendMarkdownReply(lines.join("\n"));
  } catch (err) {
    logger.error({ err }, "Failed to fetch my tasks");
    await ctx.sendTextReply("Error al obtener tus tareas. Intenta de nuevo.");
  }
}
