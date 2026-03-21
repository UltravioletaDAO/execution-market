/**
 * EMServ Bot Personality System
 *
 * 4 bot personalities sharing 1 process:
 * - em-bot:   Professional router (all CRUD, notifications)
 * - em-match: Analytic matchmaker (suggestions, availability)
 * - em-rep:   Neutral reputation oracle (scores, history)
 * - em-arb:   Formal arbitrator (disputes, rulings)
 *
 * MVP: Single IRC connection, personality affects response formatting only.
 */

export interface BotPersonality {
  nick: string;
  tone: "direct" | "analytic" | "neutral" | "formal";
  prefix: string;
  commands: string[];
}

const PERSONALITIES: Record<string, BotPersonality> = {
  "em-bot": {
    nick: "em-bot",
    tone: "direct",
    prefix: "",
    commands: [
      "tasks", "claim", "unclaim", "submit", "status",
      "publish", "confirm", "cancel", "approve", "reject",
      "link", "verify", "verify-sig", "register", "whoami",
      "help", "my-tasks", "my-claims", "details", "search",
      "extend", "mutual-cancel", "confirm-cancel", "format",
    ],
  },
  "em-match": {
    nick: "em-match",
    tone: "analytic",
    prefix: "[MATCH] ",
    commands: ["match", "suggest", "available", "nearby"],
  },
  "em-rep": {
    nick: "em-rep",
    tone: "neutral",
    prefix: "[REP] ",
    commands: ["rep", "score", "history", "feedback"],
  },
  "em-arb": {
    nick: "em-arb",
    tone: "formal",
    prefix: "[ARB] ",
    commands: ["dispute", "evidence", "ruling", "appeal"],
  },
};

/**
 * Route a command to the appropriate bot personality.
 * Returns the default em-bot if no specific personality matches.
 */
export function routeToPersonality(command: string): BotPersonality {
  const cmd = command.toLowerCase();

  for (const personality of Object.values(PERSONALITIES)) {
    if (personality.commands.includes(cmd)) {
      return personality;
    }
  }

  return PERSONALITIES["em-bot"];
}

/**
 * Format a response with the personality's prefix and tone.
 */
export function formatWithPersonality(
  personality: BotPersonality,
  message: string,
): string {
  return `${personality.prefix}${message}`;
}

export function getPersonality(name: string): BotPersonality | null {
  return PERSONALITIES[name] ?? null;
}

export function getAllPersonalities(): BotPersonality[] {
  return Object.values(PERSONALITIES);
}
