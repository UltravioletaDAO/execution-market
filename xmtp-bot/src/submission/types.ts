export interface EvidencePiece {
  type: "photo" | "video" | "document" | "text" | "gps" | "json_response";
  description: string;
  required: boolean;
  collected: boolean;
  value?: unknown;
  fileUrl?: string;
}

export interface SubmissionDraft {
  taskId: string;
  taskTitle: string;
  executorId: string;
  pieces: EvidencePiece[];
  currentPieceIndex: number;
  startedAt: number;
}

export const SUBMISSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 min
