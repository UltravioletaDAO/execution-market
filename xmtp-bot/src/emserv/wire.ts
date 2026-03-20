/**
 * EMServ Wire Format — dual output for humans and machines.
 *
 * Human-readable (default):
 *   [NEW TASK] Take photo | $0.10 USDC (base) | physical_presence | 15min | /claim a1b2c3d4
 *
 * JSON mode (for agents, triggered by /format json):
 *   {"event":"task.created","task_id":"a1b2c3d4","title":"Take photo","bounty_usdc":0.10}
 *
 * Both are regex-parseable for machine consumption.
 */

import type { OutputFormat } from "./types.js";

// Per-nick format preference (default: human)
const formatPrefs = new Map<string, OutputFormat>();

export function setOutputFormat(nick: string, format: OutputFormat): void {
  formatPrefs.set(nick.toLowerCase(), format);
}

export function getOutputFormat(nick: string): OutputFormat {
  return formatPrefs.get(nick.toLowerCase()) ?? "human";
}

/**
 * Format a task event for output.
 */
export function formatTaskEvent(
  nick: string,
  event: string,
  data: Record<string, unknown>,
): string {
  const format = getOutputFormat(nick);

  if (format === "json") {
    return JSON.stringify({ event, ...data });
  }

  // Human-readable format
  switch (event) {
    case "task.created": {
      const title = (data.title as string)?.slice(0, 80) ?? "Untitled";
      const bounty = parseFloat(String(data.bounty_usdc ?? 0)).toFixed(2);
      const chain = (data.payment_network as string) ?? "base";
      const cat = (data.category as string) ?? "general";
      const id = (data.task_id as string)?.slice(0, 8) ?? "?";
      const deadline = data.deadline_minutes ? `${data.deadline_minutes}min` : "";
      return `[NEW TASK] ${title} | $${bounty} USDC (${chain}) | ${cat}${deadline ? ` | ${deadline}` : ""} | /claim ${id}`;
    }

    case "task.assigned": {
      const id = (data.task_id as string)?.slice(0, 8) ?? "?";
      let worker = (data.worker_wallet as string) ?? "?";
      if (worker.length > 10) worker = `${worker.slice(0, 6)}...${worker.slice(-4)}`;
      return `[ASSIGNED] Task ${id} | Worker: ${worker}`;
    }

    case "task.completed": {
      const id = (data.task_id as string)?.slice(0, 8) ?? "?";
      return `[COMPLETED] Task ${id}`;
    }

    case "task.cancelled": {
      const id = (data.task_id as string)?.slice(0, 8) ?? "?";
      const reason = data.reason ? ` | ${data.reason}` : "";
      return `[CANCELLED] Task ${id}${reason}`;
    }

    case "submission.approved": {
      const id = (data.task_id as string)?.slice(0, 8) ?? "?";
      const bounty = parseFloat(String(data.bounty_usdc ?? data.amount_usd ?? 0)).toFixed(2);
      return `[APPROVED] Task ${id} | Payment: $${bounty} USDC`;
    }

    case "submission.rejected": {
      const id = (data.task_id as string)?.slice(0, 8) ?? "?";
      const reason = (data.reason as string) ?? "No reason given";
      return `[REJECTED] Task ${id} | ${reason}`;
    }

    case "payment.released": {
      const id = (data.task_id as string)?.slice(0, 8) ?? "?";
      const amount = parseFloat(String(data.amount_usd ?? 0)).toFixed(2);
      const tx = data.tx_hash ? ` | TX: ${(data.tx_hash as string).slice(0, 14)}...` : "";
      return `[PAID] Task ${id} | $${amount} USDC${tx}`;
    }

    default:
      return `[${event.toUpperCase()}] ${JSON.stringify(data)}`;
  }
}

/**
 * Regex patterns for machine-parsing human-readable output.
 * Agents can use these to extract structured data from IRC lines.
 */
export const WIRE_PATTERNS = {
  NEW_TASK: /\[NEW TASK\] (.+?) \| \$([0-9.]+) USDC \((\w+)\) \| (\w+)(?: \| (\d+)min)? \| \/claim ([a-f0-9]+)/,
  ASSIGNED: /\[ASSIGNED\] Task ([a-f0-9]+) \| Worker: (.+)/,
  APPROVED: /\[APPROVED\] Task ([a-f0-9]+) \| Payment: \$([0-9.]+) USDC/,
  REJECTED: /\[REJECTED\] Task ([a-f0-9]+) \| (.+)/,
  PAID: /\[PAID\] Task ([a-f0-9]+) \| \$([0-9.]+) USDC(?: \| TX: (.+))?/,
  CANCELLED: /\[CANCELLED\] Task ([a-f0-9]+)(?: \| (.+))?/,
} as const;
