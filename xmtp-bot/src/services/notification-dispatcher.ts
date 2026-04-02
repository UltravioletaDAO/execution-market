import { formatUsdc } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";
import { txLink } from "./payment-monitor.js";
import { apiClient } from "./api-client.js";

type SendMessageFn = (peerAddress: string, text: string) => Promise<void>;

let sendMessage: SendMessageFn | null = null;

// Track tasks already prompted for rating
const ratingPrompted = new Set<string>();

export function setSendMessageFn(fn: SendMessageFn): void {
  sendMessage = fn;
}

async function notify(address: string, text: string): Promise<void> {
  if (!sendMessage) {
    logger.warn("SendMessage function not set, skipping notification");
    return;
  }
  try {
    await sendMessage(address, text);
  } catch (err) {
    logger.error({ err, address }, "Failed to send notification");
  }
}

export async function notifyTaskCreated(task: any): Promise<void> {
  // In Phase 1, just log — no category-based subscription yet
  logger.info({ taskId: task.id, category: task.category }, "New task published");
}

export async function notifyTaskAssigned(
  workerAddress: string,
  task: any
): Promise<void> {
  const text =
    `**Tarea Asignada!**\n\n` +
    `**${task.title}**\n` +
    `Bounty: ${formatUsdc(task.bounty_usdc)} USDC (${task.payment_network ?? "base"})\n` +
    `Categoria: ${task.category}\n\n` +
    `Envia evidencia cuando estes listo.\n` +
    `Dashboard: https://execution.market/tasks/${task.id}`;

  await notify(workerAddress, text);
}

export async function notifySubmissionApproved(
  workerAddress: string,
  task: any,
  txHash?: string
): Promise<void> {
  const bounty = parseFloat(String(task.bounty_usdc ?? 0));
  const net = bounty * 0.87;
  const fee = bounty - net;
  const chain = task.payment_network ?? "base";

  let text =
    `**Evidencia Aprobada!**\n\n` +
    `**${task.title}**\n\n` +
    `| Detalle | Valor |\n` +
    `|---------|-------|\n` +
    `| Bounty | $${formatUsdc(bounty)} USDC |\n` +
    `| Fee (13%) | -$${formatUsdc(fee)} |\n` +
    `| **Neto** | **$${formatUsdc(net)} USDC** |\n` +
    `| Chain | ${chain} |\n`;

  if (txHash) {
    const explorerLink = txLink(chain, txHash);
    text += `| TX | ${explorerLink} |\n`;
  }

  await notify(workerAddress, text);

  // Auto-rate the worker from the agent after successful payment
  const taskId = task.id ?? task.task_id;
  if (taskId) {
    try {
      await apiClient.post("/api/v1/reputation/workers/rate", {
        task_id: taskId,
        score: 80,
        comment: "Task completed successfully",
      });
      logger.info({ taskId }, "Auto-rated worker after approval");

      // Notify the agent's conversation that the worker was rated
      const agentAddress = task.agent_wallet ?? task.publisher_wallet;
      if (agentAddress) {
        await notify(
          agentAddress,
          `**Auto-rating enviado** al worker de **${task.title}**\n` +
            `Score: 80/100 — Task completed successfully`
        );
      }
    } catch (err) {
      logger.error({ err, taskId }, "Failed to auto-rate worker after approval");
    }
  }

  // Prompt worker to rate the agent after payment
  scheduleRatingPrompt(workerAddress, task);
}

export async function notifySubmissionRejected(
  workerAddress: string,
  task: any,
  reason?: string
): Promise<void> {
  const text =
    `**Evidencia Rechazada**\n\n` +
    `**${task.title}**\n` +
    (reason ? `Razon: ${reason}\n\n` : "\n") +
    `Puedes reenviar evidencia desde el dashboard.`;

  await notify(workerAddress, text);
}

export function scheduleRatingPrompt(
  workerAddress: string,
  task: any
): void {
  const key = `${workerAddress}:${task.id}`;
  if (ratingPrompted.has(key)) return;
  ratingPrompted.add(key);

  // Wait 30 seconds then prompt
  setTimeout(async () => {
    const shortTaskId = task.id?.slice(0, 8) ?? "?";
    await notify(
      workerAddress,
      `Como fue tu experiencia con **${task.title}**?\n\n` +
        `Califica al publicador:\n` +
        `\`/rate ${shortTaskId} <1-5> [comentario]\`\n\n` +
        `_Tu feedback ayuda a construir confianza en la plataforma._`
    );
  }, 30_000);
}

export async function notifyNewRating(
  targetAddress: string,
  rating: {
    score: number;
    comment?: string;
    from_address?: string;
    task_title?: string;
  }
): Promise<void> {
  const stars = "\u2605".repeat(rating.score) + "\u2606".repeat(5 - rating.score);
  const from = rating.from_address
    ? `${rating.from_address.slice(0, 6)}...${rating.from_address.slice(-4)}`
    : "Anonimo";

  await notify(
    targetAddress,
    `**Nuevo rating recibido** ${stars}\n\n` +
      `| Campo | Valor |\n` +
      `|-------|-------|\n` +
      `| Score | ${rating.score}/5 |\n` +
      `| De | ${from} |\n` +
      (rating.comment ? `| Comentario | ${rating.comment} |\n` : "") +
      (rating.task_title ? `| Tarea | ${rating.task_title} |\n` : "") +
      `\nUsa \`/reputation\` para ver tu score completo.`
  );
}
