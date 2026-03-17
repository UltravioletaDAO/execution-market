import {
  getTaskGroup,
  updateGroupStatus,
  sendGroupMessage,
  archiveGroup,
  scheduleAutoArchive,
} from "./group-manager.js";
import { formatUsdc, txLink } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

/**
 * XMTP-5.3: Post task lifecycle events into the group chat.
 */

export async function onTaskStatusChanged(
  taskId: string,
  newStatus: string,
  data?: any,
): Promise<void> {
  const group = getTaskGroup(taskId);
  if (!group) return;

  switch (newStatus) {
    case "in_progress":
      await updateGroupStatus(taskId, "active", "EN PROGRESO");
      await sendGroupMessage(taskId, "La tarea esta ahora en progreso.");
      break;

    case "submitted":
      await updateGroupStatus(taskId, "submitted", "EVIDENCIA ENVIADA");
      await sendGroupMessage(
        taskId,
        `**Evidencia enviada**\n\n` +
          `El worker ha enviado la evidencia para revision.\n` +
          `Esperando aprobacion del agente...`,
      );
      break;

    case "completed": {
      await updateGroupStatus(taskId, "completed", "COMPLETADA");
      const txHash = data?.tx_hash;
      const chain = data?.payment_network ?? data?.chain ?? group.chain;
      let msg = `**Tarea Completada!**\n\nBounty: ${group.bounty} USDC pagado.`;
      if (txHash) {
        msg += `\nTX: ${txLink(chain, txHash)}`;
      }
      msg += `\n\nCalifiquen su experiencia con /rate`;
      await sendGroupMessage(taskId, msg);
      scheduleAutoArchive(taskId);
      break;
    }

    case "disputed":
      await updateGroupStatus(taskId, "active", "EN DISPUTA");
      await sendGroupMessage(
        taskId,
        `**Disputa abierta**\n\n` +
          `La evidencia fue disputada. Se requiere arbitraje.`,
      );
      break;

    case "cancelled":
      await sendGroupMessage(
        taskId,
        `**Tarea cancelada**\n\n` +
          `Esta tarea ha sido cancelada. El grupo sera archivado.`,
      );
      await archiveGroup(taskId, "Tarea cancelada.");
      break;

    case "expired":
      await sendGroupMessage(
        taskId,
        `**Tarea expirada**\n\n` +
          `El deadline ha pasado. El grupo sera archivado.`,
      );
      await archiveGroup(taskId, "Tarea expirada.");
      break;
  }
}

export async function onEvidenceSubmitted(
  taskId: string,
  data?: any,
): Promise<void> {
  const group = getTaskGroup(taskId);
  if (!group) return;

  const pieceCount = data?.piece_count ?? data?.evidence_count ?? "?";
  await sendGroupMessage(
    taskId,
    `**Evidencia recibida** (${pieceCount} piezas)\n` +
      `Pendiente de revision.`,
  );
}

export async function onSubmissionApproved(
  taskId: string,
  data?: any,
): Promise<void> {
  const group = getTaskGroup(taskId);
  if (!group) return;

  const amount = data?.amount ? formatUsdc(data.amount) : group.bounty;
  await sendGroupMessage(
    taskId,
    `**Evidencia aprobada!**\n\n` +
      `Pago: $${amount} USDC\n` +
      `Procesando transferencia...`,
  );
}

export async function onSubmissionRejected(
  taskId: string,
  reason?: string,
): Promise<void> {
  const group = getTaskGroup(taskId);
  if (!group) return;

  await sendGroupMessage(
    taskId,
    `**Evidencia rechazada**\n\n` +
      (reason ? `Razon: ${reason}\n\n` : "") +
      `El worker puede reenviar evidencia.`,
  );
}

export async function onRatingReceived(
  taskId: string,
  data?: any,
): Promise<void> {
  const group = getTaskGroup(taskId);
  if (!group) return;

  const score = data?.score ?? 0;
  const stars = "\u2605".repeat(score) + "\u2606".repeat(5 - score);
  const from = data?.from_role === "worker" ? "Worker" : "Agente";

  await sendGroupMessage(
    taskId,
    `**Rating** ${stars} -- de ${from}\n` +
      (data?.comment ? `"${data.comment}"` : ""),
  );
}
