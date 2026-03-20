/**
 * EMServ type definitions — command parsing, registry, context.
 */

import { TrustLevel } from "../bridges/identity-store.js";

export interface CommandContext {
  channel: string;
  nick: string;
  taskId?: string; // Auto-detected from #task-{id} channels
  trustLevel: TrustLevel;
  walletAddress?: string;
}

export interface ParsedCommand {
  command: string; // "claim", "publish", "status" (without /)
  args: string[]; // Positional arguments
  flags: Record<string, string>; // --flag=value or --flag value
  jsonPayload?: Record<string, unknown>; // Agent JSON mode
  raw: string; // Original text
  context: CommandContext;
}

export interface CommandDefinition {
  name: string;
  aliases: string[];
  description: string;
  usage: string;
  minTrustLevel: TrustLevel;
  category: CommandCategory;
  channelScoped: boolean; // true = taskId auto-detected in #task-* channels
  handler: (cmd: ParsedCommand, send: SendFn) => Promise<void>;
}

export type SendFn = (channel: string, message: string) => void;

export type CommandCategory =
  | "auction"
  | "discovery"
  | "relay"
  | "task_ops"
  | "publisher"
  | "identity"
  | "reputation"
  | "dispute"
  | "system";

export type OutputFormat = "human" | "json";
