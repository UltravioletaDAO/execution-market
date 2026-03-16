import { formatUsdc } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";
import { txLink } from "./payment-monitor.js";

type SendMessageFn = (peerAddress: string, text: string) => Promise<void>;

let sendMessage: SendMessageFn | null = null;

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
