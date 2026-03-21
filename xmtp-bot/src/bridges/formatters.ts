import { TrustLevel } from "./identity-store.js";

// ─── Trust level badges and enforcement ──────────────────────────
export function trustBadge(level: TrustLevel | number): string {
  switch (level) {
    case TrustLevel.REGISTERED:
      return "[R]";
    case TrustLevel.VERIFIED:
      return "[V]";
    case TrustLevel.LINKED:
      return "";
    default:
      return "";
  }
}

/**
 * Minimum trust level required for each IRC command.
 * Commands not listed default to ANONYMOUS (anyone can use them).
 */
export const TRUST_REQUIREMENTS: Record<string, TrustLevel> = {
  "/tasks": TrustLevel.ANONYMOUS,
  "/search": TrustLevel.ANONYMOUS,
  "/status": TrustLevel.ANONYMOUS,
  "/help": TrustLevel.ANONYMOUS,
  "/whoami": TrustLevel.ANONYMOUS,
  "/link": TrustLevel.ANONYMOUS,
  "/verify": TrustLevel.LINKED,
  "/verify-sig": TrustLevel.LINKED,
  "/claim": TrustLevel.LINKED,
  "/bid": TrustLevel.LINKED,
  "/submit": TrustLevel.LINKED,
  "/publish": TrustLevel.VERIFIED,
  "/register": TrustLevel.VERIFIED,
  "/cancel": TrustLevel.VERIFIED,
  "/approve": TrustLevel.VERIFIED,
  "/reject": TrustLevel.VERIFIED,
  "/mutual-cancel": TrustLevel.LINKED,
  "/confirm-cancel": TrustLevel.LINKED,
};

export function checkTrustLevel(command: string, userLevel: TrustLevel): { allowed: boolean; required: TrustLevel } {
  const cmd = command.split(/\s/)[0].toLowerCase();
  const required = TRUST_REQUIREMENTS[cmd] ?? TrustLevel.ANONYMOUS;
  return { allowed: userLevel >= required, required };
}

// Markdown -> Plain text (for IRC)
export function markdownToIrc(md: string): string {
  let text = md;
  // Strip markdown tables
  text = text.replace(/\|[^\n]+\|/g, (match) => {
    // Convert table row to "key: value" format
    const cells = match
      .split("|")
      .filter((c) => c.trim())
      .map((c) => c.trim());
    if (cells.length === 2 && !cells[0].match(/^-+$/)) {
      return `  ${cells[0]}: ${cells[1]}`;
    }
    return "";
  });
  // Strip table separators
  text = text.replace(/\|[-|]+\|/g, "");
  // Bold **text** -> text
  text = text.replace(/\*\*([^*]+)\*\*/g, "$1");
  // Italic _text_ -> text
  text = text.replace(/_([^_]+)_/g, "$1");
  // Code `text` -> text
  text = text.replace(/`([^`]+)`/g, "$1");
  // Links [text](url) -> text (url)
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)");
  // Clean up multiple blank lines
  text = text.replace(/\n{3,}/g, "\n\n");
  return text.trim();
}

// Plain text -> Markdown (for XMTP)
export function ircToMarkdown(text: string, nick: string): string {
  let md = text;
  // Detect URLs and linkify
  md = md.replace(/(https?:\/\/\S+)/g, "[$1]($1)");
  // Highlight IRC commands
  md = md.replace(/\/(claim|link|help|status)\b/g, "`/$1`");
  return `**[${nick}]** ${md}`;
}

// Truncate for IRC (max ~450 chars per message, leaving room for nick/channel overhead)
export function truncateForIrc(text: string, maxLen: number = 450): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 3) + "...";
}

// Format a task notification for IRC (plain text, single line)
export function formatTaskForIrc(task: any): string {
  const bounty = parseFloat(
    String(task.bounty_usdc ?? task.bounty ?? 0),
  ).toFixed(2);
  const chain = task.payment_network ?? "base";
  const cat = task.category ?? "general";
  const id = task.id?.slice(0, 8) ?? "?";
  const title = (task.title ?? "").slice(0, 80);
  return `[NEW TASK] ${title} | $${bounty} USDC (${chain}) | Category: ${cat} | /claim ${id}`;
}

// Format status update for IRC
export function formatStatusForIrc(
  taskId: string,
  status: string,
  extra?: string,
): string {
  const id = taskId.slice(0, 8);
  const statusMap: Record<string, string> = {
    accepted: "ASSIGNED",
    in_progress: "IN PROGRESS",
    submitted: "EVIDENCE SUBMITTED",
    completed: "COMPLETED",
    cancelled: "CANCELLED",
    disputed: "DISPUTED",
  };
  const label = statusMap[status] ?? status.toUpperCase();
  return `[${label}] Task ${id}${extra ? ` | ${extra}` : ""}`;
}
