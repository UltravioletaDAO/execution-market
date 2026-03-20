/**
 * EMServ Dual-Parse Command Parser
 *
 * Supports two modes:
 * - Human: /claim abc123 --message "I'm nearby"
 * - Agent: /claim {"task_id":"abc123","message":"I'm nearby"}
 *
 * Auto-detects mode by checking if the first arg is valid JSON.
 */

import type { ParsedCommand, CommandContext } from "./types.js";

/**
 * Parse a command string into a structured ParsedCommand.
 * Returns null if the text is not a valid command (doesn't start with /).
 */
export function parseCommand(text: string, context: CommandContext): ParsedCommand | null {
  const trimmed = text.trim();
  if (!trimmed.startsWith("/")) return null;

  // Split command from rest
  const spaceIdx = trimmed.indexOf(" ");
  const command = (spaceIdx === -1 ? trimmed : trimmed.slice(0, spaceIdx))
    .slice(1) // remove /
    .toLowerCase();
  const rest = spaceIdx === -1 ? "" : trimmed.slice(spaceIdx + 1).trim();

  // Try JSON mode first (agent mode)
  if (rest.startsWith("{")) {
    try {
      const jsonPayload = JSON.parse(rest) as Record<string, unknown>;
      return {
        command,
        args: [],
        flags: {},
        jsonPayload,
        raw: trimmed,
        context,
      };
    } catch {
      // Not valid JSON — fall through to human mode
    }
  }

  // Human mode: parse positional args and --flags
  const args: string[] = [];
  const flags: Record<string, string> = {};

  if (rest) {
    const tokens = tokenize(rest);

    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];

      if (token.startsWith("--")) {
        const flagName = token.slice(2);
        const eqIdx = flagName.indexOf("=");

        if (eqIdx !== -1) {
          // --flag=value
          flags[flagName.slice(0, eqIdx)] = flagName.slice(eqIdx + 1);
        } else if (i + 1 < tokens.length && !tokens[i + 1].startsWith("--")) {
          // --flag value
          flags[flagName] = tokens[++i];
        } else {
          // --flag (boolean)
          flags[flagName] = "true";
        }
      } else {
        args.push(token);
      }
    }
  }

  return {
    command,
    args,
    flags,
    raw: trimmed,
    context,
  };
}

/**
 * Tokenize a string, respecting quoted strings.
 * "hello world" becomes a single token.
 */
function tokenize(input: string): string[] {
  const tokens: string[] = [];
  let current = "";
  let inQuote = false;
  let quoteChar = "";

  for (const char of input) {
    if (inQuote) {
      if (char === quoteChar) {
        inQuote = false;
      } else {
        current += char;
      }
    } else if (char === '"' || char === "'") {
      inQuote = true;
      quoteChar = char;
    } else if (char === " " || char === "\t") {
      if (current) {
        tokens.push(current);
        current = "";
      }
    } else {
      current += char;
    }
  }

  if (current) tokens.push(current);
  return tokens;
}

/**
 * Detect task ID from channel name for channel-scoped commands.
 */
export function getTaskIdFromChannel(channel: string): string | null {
  const match = channel.match(/^#task-([a-f0-9]{8})$/i);
  return match ? match[1] : null;
}
