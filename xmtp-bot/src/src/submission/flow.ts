import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { getWorkerStore } from "../services/worker-store.js";
import { logger } from "../utils/logger.js";
import type { EvidencePiece, SubmissionDraft } from "./types.js";
import { SUBMISSION_TIMEOUT_MS } from "./types.js";

// ─── In-memory draft store ───────────────────────────────────────
const drafts = new Map<string, SubmissionDraft>();

// ─── Public API ──────────────────────────────────────────────────

export function getActiveDraft(address: string): SubmissionDraft | undefined {
  return drafts.get(address.toLowerCase());
}

export function clearDraft(address: string): void {
  drafts.delete(address.toLowerCase());
}

export function isSubmissionTimedOut(draft: SubmissionDraft): boolean {
  return Date.now() - draft.startedAt > SUBMISSION_TIMEOUT_MS;
}

export async function startSubmission(
  ctx: MessageContext<string>,
  taskId: string
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
      "Debes registrarte primero. Usa /register para comenzar."
    );
    return;
  }

  // Check for existing draft
  const existing = getActiveDraft(senderAddress);
  if (existing) {
    await ctx.sendTextReply(
      `Ya tienes una submission activa para tarea ${existing.taskId.slice(0, 8)}...\n` +
        `Usa /cancel para cancelarla o /done para enviar lo que tienes.`
    );
    return;
  }

  // Fetch task details
  const task = await apiClient.resolveTask(taskId);
  if (!task) {
    await ctx.sendTextReply(
      `No se encontro la tarea "${taskId}". Verifica el ID con /tasks`
    );
    return;
  }

  // Build evidence pieces from task requirements
  const pieces = buildEvidencePieces(task);
  if (pieces.length === 0) {
    await ctx.sendTextReply(
      "Esta tarea no tiene requisitos de evidencia definidos. Contacta al publicador."
    );
    return;
  }

  // Create draft
  const draft: SubmissionDraft = {
    taskId: task.id,
    taskTitle: task.title ?? task.id,
    executorId: worker.executorId,
    pieces,
    currentPieceIndex: 0,
    startedAt: Date.now(),
  };

  drafts.set(senderAddress.toLowerCase(), draft);
  store.setConversationState(senderAddress, "submission");

  // Show intro
  const requiredCount = pieces.filter((p) => p.required).length;
  const optionalCount = pieces.length - requiredCount;

  await ctx.sendMarkdownReply(
    `**Enviar evidencia**\n\n` +
      `Tarea: **${draft.taskTitle}**\n` +
      `ID: \`${draft.taskId.slice(0, 8)}...\`\n\n` +
      `Evidencia requerida: **${requiredCount}** pieza(s)` +
      (optionalCount > 0 ? ` + ${optionalCount} opcional(es)` : "") +
      `\n\n` +
      `Comandos durante la submission:\n` +
      `- \`/skip\` — Omitir pieza opcional\n` +
      `- \`/cancel\` — Cancelar submission\n` +
      `- \`/done\` — Enviar con lo que tengas\n\n` +
      `Tiempo limite: 30 minutos`
  );

  // Prompt first piece
  const prompt = promptForPiece(pieces[0], 0, pieces.length);
  await ctx.sendMarkdownReply(progressBar(draft) + "\n\n" + prompt);
}

export async function handleSubmissionText(
  ctx: MessageContext<string>,
  senderAddress: string,
  text: string
): Promise<void> {
  const draft = getActiveDraft(senderAddress);
  if (!draft) {
    getWorkerStore().resetConversation(senderAddress);
    return;
  }

  if (isSubmissionTimedOut(draft)) {
    clearDraft(senderAddress);
    getWorkerStore().resetConversation(senderAddress);
    await ctx.sendTextReply(
      "Submission expirada (30 min). Usa /submit para reiniciar."
    );
    return;
  }

  const piece = draft.pieces[draft.currentPieceIndex];
  if (!piece) {
    await compileAndSubmit(ctx, senderAddress, draft);
    return;
  }

  switch (piece.type) {
    case "text": {
      if (text.length < 5) {
        await ctx.sendTextReply(
          "Texto muy corto (minimo 5 caracteres). Intenta de nuevo:"
        );
        return;
      }
      if (text.length > 5000) {
        await ctx.sendTextReply(
          "Texto muy largo (maximo 5000 caracteres). Intenta de nuevo:"
        );
        return;
      }
      piece.value = text;
      piece.collected = true;
      break;
    }

    case "gps": {
      const coords = parseGpsInput(text);
      if (!coords) {
        await ctx.sendTextReply(
          "No se pudo leer la ubicacion.\n\n" +
            "Formatos aceptados:\n" +
            "- Coordenadas: 4.711,-74.072\n" +
            "- Google Maps link\n" +
            "- Waze link\n" +
            "- Apple Maps link"
        );
        return;
      }
      piece.value = { lat: coords.lat, lng: coords.lng };
      piece.collected = true;
      break;
    }

    case "json_response": {
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        // Accept as text but warn
        await ctx.sendTextReply(
          "No es JSON valido, pero se guardara como texto."
        );
        parsed = text;
      }
      piece.value = parsed;
      piece.collected = true;
      break;
    }

    case "photo":
    case "video":
    case "document": {
      // Text input for file types = treat as description/note
      await ctx.sendTextReply(
        `Este campo requiere un archivo (${piece.type}).\n` +
          `Envia el archivo directamente o usa /skip si es opcional.`
      );
      return;
    }

    default: {
      piece.value = text;
      piece.collected = true;
    }
  }

  const done = await advanceToNextPiece(ctx, draft);
  if (done) {
    await compileAndSubmit(ctx, senderAddress, draft);
  }
}

export async function handleSubmissionSkip(
  ctx: MessageContext<string>,
  senderAddress: string
): Promise<void> {
  const draft = getActiveDraft(senderAddress);
  if (!draft) return;

  const piece = draft.pieces[draft.currentPieceIndex];
  if (!piece) return;

  if (piece.required) {
    await ctx.sendTextReply(
      "Esta pieza es obligatoria y no se puede omitir."
    );
    return;
  }

  // Skip it
  const done = await advanceToNextPiece(ctx, draft);
  if (done) {
    await compileAndSubmit(ctx, senderAddress, draft);
  }
}

export async function handleSubmissionCancel(
  ctx: MessageContext<string>,
  senderAddress: string
): Promise<void> {
  const draft = getActiveDraft(senderAddress);
  if (!draft) {
    await ctx.sendTextReply("No hay submission activa.");
    return;
  }

  clearDraft(senderAddress);
  getWorkerStore().resetConversation(senderAddress);
  await ctx.sendTextReply("Submission cancelada.");
}

export async function handleSubmissionDone(
  ctx: MessageContext<string>,
  senderAddress: string
): Promise<void> {
  const draft = getActiveDraft(senderAddress);
  if (!draft) {
    await ctx.sendTextReply("No hay submission activa.");
    return;
  }

  await compileAndSubmit(ctx, senderAddress, draft);
}

export async function advanceToNextPiece(
  ctx: MessageContext<string>,
  draft: SubmissionDraft
): Promise<boolean> {
  draft.currentPieceIndex++;

  // Skip already-collected pieces (e.g. filled by attachment handler)
  while (
    draft.currentPieceIndex < draft.pieces.length &&
    draft.pieces[draft.currentPieceIndex].collected
  ) {
    draft.currentPieceIndex++;
  }

  if (draft.currentPieceIndex >= draft.pieces.length) {
    return true; // All pieces done
  }

  const piece = draft.pieces[draft.currentPieceIndex];
  const prompt = promptForPiece(
    piece,
    draft.currentPieceIndex,
    draft.pieces.length
  );
  await ctx.sendMarkdownReply(progressBar(draft) + "\n\n" + prompt);
  return false;
}

export function collectAttachment(
  address: string,
  fileUrl: string,
  mimeType: string
): boolean {
  const draft = getActiveDraft(address);
  if (!draft) return false;

  const piece = draft.pieces[draft.currentPieceIndex];
  if (!piece) return false;

  const isFileType =
    piece.type === "photo" ||
    piece.type === "video" ||
    piece.type === "document";

  if (!isFileType) return false;

  // Validate mime type loosely
  if (piece.type === "photo" && !mimeType.startsWith("image/")) return false;
  if (piece.type === "video" && !mimeType.startsWith("video/")) return false;

  piece.fileUrl = fileUrl;
  piece.value = fileUrl;
  piece.collected = true;
  return true;
}

// ─── Private helpers ─────────────────────────────────────────────

function progressBar(draft: SubmissionDraft): string {
  return draft.pieces
    .map((p, i) => {
      if (p.collected) return "[x]";
      if (i === draft.currentPieceIndex) return "[>]";
      return "[ ]";
    })
    .join(" ");
}

function promptForPiece(
  piece: EvidencePiece,
  index: number,
  total: number
): string {
  const reqLabel = piece.required ? "obligatorio" : "opcional";
  const header = `**Pieza ${index + 1}/${total}** (${reqLabel})`;
  const desc = piece.description || piece.type;

  switch (piece.type) {
    case "photo":
      return (
        `${header}\n` +
        `Tipo: Foto\n` +
        `${desc}\n\n` +
        `Envia una imagen directamente en el chat.`
      );
    case "video":
      return (
        `${header}\n` +
        `Tipo: Video\n` +
        `${desc}\n\n` +
        `Envia un video directamente en el chat.`
      );
    case "document":
      return (
        `${header}\n` +
        `Tipo: Documento\n` +
        `${desc}\n\n` +
        `Envia el archivo directamente en el chat.`
      );
    case "text":
      return (
        `${header}\n` +
        `Tipo: Texto\n` +
        `${desc}\n\n` +
        `Escribe tu respuesta (5-5000 caracteres):`
      );
    case "gps":
      return (
        `${header}\n` +
        `Tipo: Ubicacion GPS\n` +
        `${desc}\n\n` +
        `Envia coordenadas o un link de Google Maps/Waze/Apple Maps:`
      );
    case "json_response":
      return (
        `${header}\n` +
        `Tipo: Respuesta JSON\n` +
        `${desc}\n\n` +
        `Envia el JSON o texto de respuesta:`
      );
    default:
      return `${header}\n${desc}\n\nEnvia tu respuesta:`;
  }
}

async function compileAndSubmit(
  ctx: MessageContext<string>,
  address: string,
  draft: SubmissionDraft
): Promise<void> {
  // Validate required pieces
  const missing = draft.pieces.filter((p) => p.required && !p.collected);
  if (missing.length > 0) {
    const names = missing.map((p) => `- ${p.description || p.type}`).join("\n");
    await ctx.sendTextReply(
      `Faltan ${missing.length} pieza(s) obligatoria(s):\n${names}\n\n` +
        `Completa las piezas o usa /cancel para cancelar.`
    );
    return;
  }

  // Build evidence dict: { evidence_type: value }
  const evidence: Record<string, unknown> = {};
  for (const piece of draft.pieces) {
    if (!piece.collected) continue;

    // Use type as key; if duplicate types, append index
    let key: string = piece.type;
    if (key in evidence) {
      let suffix = 2;
      while (`${key}_${suffix}` in evidence) suffix++;
      key = `${key}_${suffix}`;
    }
    evidence[key] = piece.value;
  }

  const collectedCount = draft.pieces.filter((p) => p.collected).length;

  await ctx.sendTextReply(
    `Enviando ${collectedCount}/${draft.pieces.length} pieza(s)...`
  );

  try {
    await apiClient.submitEvidence(draft.taskId, draft.executorId, evidence);

    clearDraft(address);
    getWorkerStore().resetConversation(address);

    await ctx.sendMarkdownReply(
      `**Evidencia enviada!**\n\n` +
        `Tarea: ${draft.taskTitle}\n` +
        `Piezas: ${collectedCount}/${draft.pieces.length}\n\n` +
        `El agente revisara tu entrega. Usa \`/status ${draft.taskId.slice(0, 8)}\` para verificar.`
    );
  } catch (err: any) {
    const detail =
      err?.response?.data?.detail ?? err?.message ?? "Error desconocido";
    logger.error(
      { err, taskId: draft.taskId, executor: draft.executorId },
      "Evidence submission failed"
    );
    await ctx.sendTextReply(
      `Error al enviar evidencia: ${detail}\n\n` +
        `Tu draft sigue activo. Intenta /done de nuevo o /cancel para abandonar.`
    );
  }
}

interface GpsCoords {
  lat: number;
  lng: number;
}

function parseGpsInput(text: string): GpsCoords | null {
  const trimmed = text.trim();

  // Google Maps: https://maps.google.com/?q=4.711,-74.072
  //              https://www.google.com/maps/@4.711,-74.072,15z
  //              https://www.google.com/maps/place/.../@4.711,-74.072,...
  //              https://maps.app.goo.gl/... (short links won't work without redirect)
  const googleQ = trimmed.match(
    /maps\.google\.com\/?\?.*?q=([-\d.]+)[,%20]+([-\d.]+)/i
  );
  if (googleQ) {
    return validateCoords(parseFloat(googleQ[1]), parseFloat(googleQ[2]));
  }

  const googleAt = trimmed.match(
    /google\.com\/maps\/@([-\d.]+),([-\d.]+)/i
  );
  if (googleAt) {
    return validateCoords(parseFloat(googleAt[1]), parseFloat(googleAt[2]));
  }

  const googlePlace = trimmed.match(
    /google\.com\/maps\/place\/[^/]*\/@([-\d.]+),([-\d.]+)/i
  );
  if (googlePlace) {
    return validateCoords(
      parseFloat(googlePlace[1]),
      parseFloat(googlePlace[2])
    );
  }

  // Waze: https://waze.com/ul?ll=4.711,-74.072
  const waze = trimmed.match(/waze\.com\/ul\?.*?ll=([-\d.]+),([-\d.]+)/i);
  if (waze) {
    return validateCoords(parseFloat(waze[1]), parseFloat(waze[2]));
  }

  // Apple Maps: https://maps.apple.com/?ll=4.711,-74.072
  const apple = trimmed.match(
    /maps\.apple\.com\/?\?.*?ll=([-\d.]+),([-\d.]+)/i
  );
  if (apple) {
    return validateCoords(parseFloat(apple[1]), parseFloat(apple[2]));
  }

  // Direct coordinates: "4.711,-74.072" or "4.711 -74.072"
  const direct = trimmed.match(/^([-\d.]+)[,\s]+([-\d.]+)$/);
  if (direct) {
    return validateCoords(parseFloat(direct[1]), parseFloat(direct[2]));
  }

  return null;
}

function validateCoords(lat: number, lng: number): GpsCoords | null {
  if (isNaN(lat) || isNaN(lng)) return null;
  if (lat < -90 || lat > 90) return null;
  if (lng < -180 || lng > 180) return null;
  return { lat, lng };
}

function buildEvidencePieces(task: any): EvidencePiece[] {
  const requirements = task.evidence_requirements;
  if (!requirements) return [];

  // Handle array of requirement objects
  if (Array.isArray(requirements)) {
    return requirements.map((req: any) => ({
      type: mapEvidenceType(req.type ?? req.evidence_type ?? "text"),
      description: req.description ?? req.label ?? req.type ?? "Evidencia",
      required: req.required !== false,
      collected: false,
    }));
  }

  // Handle object with evidence_type keys
  if (typeof requirements === "object") {
    return Object.entries(requirements).map(([key, val]: [string, any]) => {
      const desc =
        typeof val === "string"
          ? val
          : val?.description ?? val?.label ?? key;
      return {
        type: mapEvidenceType(key),
        description: desc,
        required: typeof val === "object" ? val?.required !== false : true,
        collected: false,
      };
    });
  }

  return [];
}

function mapEvidenceType(
  raw: string
): EvidencePiece["type"] {
  const lower = raw.toLowerCase();
  if (lower.includes("photo") || lower.includes("image")) return "photo";
  if (lower.includes("video")) return "video";
  if (lower.includes("document") || lower.includes("file")) return "document";
  if (lower.includes("gps") || lower.includes("location")) return "gps";
  if (lower.includes("json")) return "json_response";
  return "text";
}
