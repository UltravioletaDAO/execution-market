import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { getWorkerStore } from "../services/worker-store.js";
import { shortId } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

export async function handleApply(
  ctx: MessageContext<string>,
  args: string[]
): Promise<void> {
  if (args.length === 0) {
    await ctx.sendTextReply("Uso: /apply <task-id>\nEjemplo: /apply abc12345");
    return;
  }

  const senderAddress = await ctx.getSenderAddress();
  if (!senderAddress) {
    await ctx.sendTextReply("No se pudo resolver tu direccion.");
    return;
  }

  const store = getWorkerStore();
  const worker = store.getByAddress(senderAddress);
  if (!worker?.executorId) {
    await ctx.sendTextReply(
      "Necesitas registrarte primero. Usa /register"
    );
    return;
  }

  try {
    const task = await apiClient.resolveTask(args[0]);
    if (!task) {
      await ctx.sendTextReply(`No se encontro la tarea: ${args[0]}`);
      return;
    }

    await apiClient.post(`/api/v1/tasks/${task.id}/apply`, {
      executor_id: worker.executorId,
      message: `Applied via XMTP bot`,
    });

    await ctx.sendMarkdownReply(
      `**Solicitud enviada!**\n\n` +
        `Tarea: \`${shortId(task.id)}\` — ${task.title}\n` +
        `Estado: pendiente de asignacion`
    );
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Error al aplicar.";
    logger.error({ err, taskId: args[0] }, "Failed to apply to task");
    await ctx.sendTextReply(`Error: ${detail}`);
  }
}
