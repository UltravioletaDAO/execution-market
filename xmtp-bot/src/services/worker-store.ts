export type ConversationState = "idle" | "registration" | "submission";

interface RegistrationProgress {
  step: "name" | "email" | "confirm";
  name?: string;
  email?: string;
}

export interface WorkerEntry {
  xmtpAddress: string;
  walletAddress?: string;
  executorId?: string;
  name?: string;
  conversationState: ConversationState;
  registrationProgress?: RegistrationProgress;
  lastActivity: number;
}

class WorkerStore {
  private workers: Map<string, WorkerEntry> = new Map();

  getByAddress(xmtpAddress: string): WorkerEntry | undefined {
    return this.workers.get(xmtpAddress.toLowerCase());
  }

  getOrCreate(xmtpAddress: string): WorkerEntry {
    const key = xmtpAddress.toLowerCase();
    if (!this.workers.has(key)) {
      this.workers.set(key, {
        xmtpAddress: key,
        conversationState: "idle",
        lastActivity: Date.now(),
      });
    }
    const entry = this.workers.get(key)!;
    entry.lastActivity = Date.now();
    return entry;
  }

  register(xmtpAddress: string, executorId: string, name: string): void {
    const entry = this.getOrCreate(xmtpAddress);
    entry.executorId = executorId;
    entry.name = name;
    entry.walletAddress = xmtpAddress;
    entry.conversationState = "idle";
    entry.registrationProgress = undefined;
  }

  getConversationState(xmtpAddress: string): ConversationState {
    return this.getByAddress(xmtpAddress)?.conversationState ?? "idle";
  }

  setConversationState(xmtpAddress: string, state: ConversationState): void {
    this.getOrCreate(xmtpAddress).conversationState = state;
  }

  setRegistrationProgress(xmtpAddress: string, progress: RegistrationProgress): void {
    const entry = this.getOrCreate(xmtpAddress);
    entry.conversationState = "registration";
    entry.registrationProgress = progress;
  }

  getRegistrationProgress(xmtpAddress: string): RegistrationProgress | undefined {
    return this.getByAddress(xmtpAddress)?.registrationProgress;
  }

  resetConversation(xmtpAddress: string): void {
    const entry = this.getOrCreate(xmtpAddress);
    entry.conversationState = "idle";
    entry.registrationProgress = undefined;
  }

  getAllRegistered(): WorkerEntry[] {
    return Array.from(this.workers.values()).filter((w) => !!w.executorId);
  }
}

let store: WorkerStore;

export function getWorkerStore(): WorkerStore {
  if (!store) store = new WorkerStore();
  return store;
}
