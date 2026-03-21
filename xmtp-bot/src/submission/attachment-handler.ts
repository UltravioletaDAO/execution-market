// src/submission/attachment-handler.ts
// Processes remote attachments received via XMTP during a submission flow.
// Downloads the file, validates it, uploads to S3, and advances the draft.

import type { MessageContext } from "@xmtp/agent-sdk";
import {
  downloadRemoteAttachment,
  type RemoteAttachment,
} from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import {
  getActiveDraft,
  advanceToNextPiece,
  collectAttachment,
  isSubmissionTimedOut,
  clearDraft,
} from "./flow.js";
import { getWorkerStore } from "../services/worker-store.js";
import { logger } from "../utils/logger.js";

const ALLOWED_MIME_TYPES: Record<string, string[]> = {
  photo: [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
  ],
  video: ["video/mp4", "video/quicktime", "video/webm"],
  document: ["application/pdf", "image/jpeg", "image/png"],
};

const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB

export async function handleAttachment(
  ctx: MessageContext<RemoteAttachment>,
): Promise<void> {
  const senderAddress = await ctx.getSenderAddress();
  if (!senderAddress) return;

  const draft = getActiveDraft(senderAddress);
  if (!draft) {
    await ctx.sendTextReply(
      "No tienes un envio de evidencia activo. Usa /submit <task_id> primero.",
    );
    return;
  }

  // Check for timeout
  if (isSubmissionTimedOut(draft)) {
    clearDraft(senderAddress);
    getWorkerStore().resetConversation(senderAddress);
    await ctx.sendTextReply(
      "Submission expirada (30 min). Usa /submit para reiniciar.",
    );
    return;
  }

  const currentPiece = draft.pieces[draft.currentPieceIndex];
  if (!currentPiece) {
    await ctx.sendTextReply("Error: no hay pieza actual.");
    return;
  }

  // Verify the current piece expects a file
  const fileTypes = ["photo", "video", "document"];
  if (!fileTypes.includes(currentPiece.type)) {
    await ctx.sendTextReply(
      `La pieza actual espera **${currentPiece.type}**, no un archivo.\n` +
        `Escribe tu respuesta como texto.`,
    );
    return;
  }

  try {
    // Download the remote attachment
    const remoteAttachment = ctx.message.content;
    const attachment = await downloadRemoteAttachment(remoteAttachment);

    // Validate MIME type
    const mimeType = attachment.mimeType ?? "application/octet-stream";
    const allowed = ALLOWED_MIME_TYPES[currentPiece.type] ?? [];
    if (allowed.length > 0 && !allowed.some((t) => mimeType === t)) {
      // Fallback: check broad category match (image/* for photo, video/* for video)
      const broadCategory =
        currentPiece.type === "photo"
          ? "image/"
          : currentPiece.type === "video"
            ? "video/"
            : null;
      if (!broadCategory || !mimeType.startsWith(broadCategory)) {
        await ctx.sendTextReply(
          `Tipo de archivo no valido: ${mimeType}\n` +
            `Se espera: ${allowed.join(", ")}`,
        );
        return;
      }
    }

    // Check file size (Attachment.content is Uint8Array)
    const content = attachment.content;
    if (content.byteLength > MAX_FILE_SIZE) {
      await ctx.sendTextReply(
        `Archivo muy grande (${(content.byteLength / 1024 / 1024).toFixed(1)}MB). Maximo: 25MB.`,
      );
      return;
    }

    // Build filename
    const extension = mimeType.split("/")[1] ?? "bin";
    const filename =
      attachment.filename ?? `evidence_${Date.now()}.${extension}`;

    // Get presigned upload URL from EM API
    const presigned = await apiClient.getPresignedUploadUrl(
      filename,
      mimeType,
      draft.taskId,
      draft.executorId,
    );

    // Upload to S3
    const cdnUrl = await apiClient.uploadToS3(
      presigned,
      Buffer.from(content),
      mimeType,
    );

    // Update the draft piece
    const success = collectAttachment(senderAddress, cdnUrl, mimeType);
    if (!success) {
      await ctx.sendTextReply("Error actualizando la pieza de evidencia.");
      return;
    }

    await ctx.sendTextReply(`Archivo recibido (${filename}).`);

    // Advance to next piece — advanceToNextPiece expects MessageContext<string>
    // but we only need sendMarkdownReply/sendTextReply which exist on all MessageContext variants
    const done = await advanceToNextPiece(
      ctx as unknown as MessageContext<string>,
      draft,
    );
    if (done) {
      // All pieces collected — notify user
      await ctx.sendTextReply(
        "Toda la evidencia fue recopilada.\n" +
          "Escribe /done para enviar o /cancel para descartar.",
      );
    }
  } catch (err) {
    logger.error({ err, sender: senderAddress }, "Attachment handling failed");
    await ctx.sendTextReply(
      "Error procesando el archivo. Intenta de nuevo o usa /skip si es opcional.",
    );
  }
}
