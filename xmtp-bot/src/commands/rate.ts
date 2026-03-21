import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { getWorkerStore } from "../services/worker-store.js";
import { shortId } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

export async function handleRate(
  ctx: MessageContext<string>,
  args: string[]
): Promise<void> {
  if (args.length < 2) {
    await ctx.sendTextReply(
      "Uso: /rate <task_id> <1-5> [comentario]\nEjemplo: /rate abc12345 5 Excelente trabajo"
    );
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
    await ctx.sendTextReply("No estas registrado. Usa /register primero.");
    return;
  }

  const [taskIdInput, scoreStr, ...commentParts] = args;
  const score = parseInt(scoreStr, 10);

  if (isNaN(score) || score < 1 || score > 5) {
    await ctx.sendTextReply("Score debe ser un numero entre 1 y 5.");
    return;
  }

  const comment = commentParts.join(" ") || undefined;

  try {
    const task = await apiClient.resolveTask(taskIdInput);
    if (!task) {
      await ctx.sendTextReply(`Tarea no encontrada: ${taskIdInput}`);
      return;
    }

    // Validate task is completed
    if (task.status !== "completed") {
      await ctx.sendTextReply(
        `La tarea debe estar completada para calificar (estado actual: ${task.status}).`
      );
      return;
    }

    // Submit rating
    // Convert 1-5 star rating to 0-100 score for ERC-8004
    const score100 = score * 20;
    await apiClient.post("/api/v1/reputation/agents/rate", {
      task_id: task.id,
      agent_id: task.agent_id ? parseInt(task.agent_id, 10) : 2106,
      score: score100,
      comment,
      proof_tx: task.payment_tx ?? "",
    });

    const stars = "\u2605".repeat(score) + "\u2606".repeat(5 - score);
    await ctx.sendMarkdownReply(
      `**Rating enviado** ${stars}\n\n` +
        `| Campo | Valor |\n` +
        `|-------|-------|\n` +
        `| Tarea | ${shortId(task.id)} — ${task.title} |\n` +
        `| Score | ${score100}/100 |\n` +
        (comment ? `| Comentario | ${comment} |\n` : "") +
        `\n_Rating registrado on-chain via ERC-8004._`
    );
  } catch (err: any) {
    const detail = err?.response?.data?.detail ?? "Error al enviar rating.";
    logger.error({ err, taskId: taskIdInput }, "Rating failed");
    await ctx.sendTextReply(`Error: ${detail}`);
  }
}
