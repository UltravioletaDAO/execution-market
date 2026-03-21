/**
 * Wizard State Machine — multi-step interactive flows (e.g., /publish).
 * In-memory per-nick with auto-timeout (10 min).
 */

export interface WizardData {
  title?: string;
  description?: string;
  category?: string;
  bounty_usdc?: number;
  deadline_minutes?: number;
  payment_network?: string;
  evidence_requirements?: string[];
}

export interface WizardSession {
  nick: string;
  channel: string;
  step: WizardStep;
  data: WizardData;
  startedAt: number;
  expiresAt: number;
}

export type WizardStep =
  | "title"
  | "category"
  | "bounty"
  | "deadline"
  | "confirm";

const WIZARD_TTL_MS = 10 * 60 * 1000; // 10 minutes
const CATEGORIES = [
  "physical_presence",
  "knowledge_access",
  "human_authority",
  "simple_action",
  "digital_physical",
];

// Active wizard sessions per nick
const sessions = new Map<string, WizardSession>();

export function startWizard(nick: string, channel: string): WizardSession {
  const session: WizardSession = {
    nick: nick.toLowerCase(),
    channel,
    step: "title",
    data: {},
    startedAt: Date.now(),
    expiresAt: Date.now() + WIZARD_TTL_MS,
  };
  sessions.set(nick.toLowerCase(), session);
  return session;
}

export function getWizardSession(nick: string): WizardSession | null {
  const session = sessions.get(nick.toLowerCase());
  if (!session) return null;
  if (Date.now() > session.expiresAt) {
    sessions.delete(nick.toLowerCase());
    return null;
  }
  return session;
}

export function cancelWizard(nick: string): boolean {
  return sessions.delete(nick.toLowerCase());
}

export function advanceWizard(nick: string, input: string): { prompt: string; done: boolean } {
  const session = getWizardSession(nick);
  if (!session) return { prompt: "No active wizard. Run /publish to start.", done: false };

  switch (session.step) {
    case "title":
      session.data.title = input.trim();
      session.step = "category";
      return {
        prompt: `Category? (${CATEGORIES.join(", ")})`,
        done: false,
      };

    case "category": {
      const cat = input.trim().toLowerCase();
      if (!CATEGORIES.includes(cat)) {
        return {
          prompt: `Invalid category. Choose: ${CATEGORIES.join(", ")}`,
          done: false,
        };
      }
      session.data.category = cat;
      session.step = "bounty";
      return { prompt: "Bounty in USDC? (e.g., 0.10)", done: false };
    }

    case "bounty": {
      const amount = parseFloat(input.trim());
      if (isNaN(amount) || amount <= 0 || amount > 100) {
        return { prompt: "Invalid amount. Enter USDC value (0.01-100).", done: false };
      }
      session.data.bounty_usdc = amount;
      session.step = "deadline";
      return { prompt: "Deadline in minutes? (e.g., 15)", done: false };
    }

    case "deadline": {
      const mins = parseInt(input.trim(), 10);
      if (isNaN(mins) || mins < 1 || mins > 1440) {
        return { prompt: "Invalid deadline. Enter minutes (1-1440).", done: false };
      }
      session.data.deadline_minutes = mins;
      session.step = "confirm";

      const summary = [
        `Title: ${session.data.title}`,
        `Category: ${session.data.category}`,
        `Bounty: $${session.data.bounty_usdc?.toFixed(2)} USDC`,
        `Deadline: ${mins} minutes`,
        `/confirm to publish or /cancel to abort.`,
      ].join("\n  ");

      return { prompt: `Confirm task:\n  ${summary}`, done: false };
    }

    case "confirm":
      if (input.trim().toLowerCase() === "/confirm" || input.trim().toLowerCase() === "confirm") {
        sessions.delete(nick.toLowerCase());
        return { prompt: "", done: true };
      }
      return { prompt: "/confirm to publish or /cancel to abort.", done: false };

    default:
      return { prompt: "Unknown wizard step.", done: false };
  }
}

export function getWizardData(nick: string): WizardData | null {
  const session = getWizardSession(nick);
  return session?.data ?? null;
}

export { CATEGORIES };
