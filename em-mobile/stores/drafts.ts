import { create } from "zustand";
import AsyncStorage from "@react-native-async-storage/async-storage";

interface EvidenceDraft {
  taskId: string;
  photoUri?: string;
  gpsData?: { lat: number; lng: number; accuracy: number; timestamp: string };
  textEvidence: Record<string, string>;
  notes: string;
  savedAt: string;
}

interface DraftsStore {
  drafts: Record<string, EvidenceDraft>;
  saveDraft: (taskId: string, draft: Omit<EvidenceDraft, "taskId" | "savedAt">) => void;
  getDraft: (taskId: string) => EvidenceDraft | null;
  removeDraft: (taskId: string) => void;
  loadDrafts: () => Promise<void>;
}

const DRAFTS_KEY = "em_evidence_drafts";

export const useDraftsStore = create<DraftsStore>((set, get) => ({
  drafts: {},

  saveDraft: (taskId, draft) => {
    const newDraft: EvidenceDraft = {
      ...draft,
      taskId,
      savedAt: new Date().toISOString(),
    };
    set((state) => {
      const updated = { ...state.drafts, [taskId]: newDraft };
      AsyncStorage.setItem(DRAFTS_KEY, JSON.stringify(updated));
      return { drafts: updated };
    });
  },

  getDraft: (taskId) => {
    return get().drafts[taskId] || null;
  },

  removeDraft: (taskId) => {
    set((state) => {
      const updated = { ...state.drafts };
      delete updated[taskId];
      AsyncStorage.setItem(DRAFTS_KEY, JSON.stringify(updated));
      return { drafts: updated };
    });
  },

  loadDrafts: async () => {
    try {
      const stored = await AsyncStorage.getItem(DRAFTS_KEY);
      if (stored) {
        set({ drafts: JSON.parse(stored) });
      }
    } catch {
      // Silent fail
    }
  },
}));
