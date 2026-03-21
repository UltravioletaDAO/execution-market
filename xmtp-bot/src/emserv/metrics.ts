/**
 * EMServ Metrics — IRC command usage, errors, and bridge latency tracking.
 *
 * Counters:
 * - commands_processed_total (by command name)
 * - command_errors_total (by command name)
 * - active_channels (gauge)
 * - connected_users (gauge)
 * - bridge_latency_ms (IRC ↔ XMTP)
 */

import { logger } from "../utils/logger.js";

// ─── Counters ────────────────────────────────────────────────────

const commandCounts = new Map<string, number>();
const commandErrors = new Map<string, number>();
let activeChannels = 0;
let connectedUsers = 0;
const bridgeLatencySamples: number[] = [];
const MAX_LATENCY_SAMPLES = 100;

// ─── Recording ───────────────────────────────────────────────────

export function recordCommand(command: string): void {
  commandCounts.set(command, (commandCounts.get(command) ?? 0) + 1);
}

export function recordCommandError(command: string): void {
  commandErrors.set(command, (commandErrors.get(command) ?? 0) + 1);
}

export function setActiveChannels(count: number): void {
  activeChannels = count;
}

export function setConnectedUsers(count: number): void {
  connectedUsers = count;
}

export function recordBridgeLatency(latencyMs: number): void {
  bridgeLatencySamples.push(latencyMs);
  if (bridgeLatencySamples.length > MAX_LATENCY_SAMPLES) {
    bridgeLatencySamples.shift();
  }
}

// ─── Reporting ───────────────────────────────────────────────────

export interface EMServMetrics {
  commands_processed_total: Record<string, number>;
  command_errors_total: Record<string, number>;
  active_channels: number;
  connected_users: number;
  avg_bridge_latency_ms: number;
  total_commands: number;
  total_errors: number;
}

export function getMetrics(): EMServMetrics {
  let totalCommands = 0;
  let totalErrors = 0;
  const cmdCounts: Record<string, number> = {};
  const cmdErrors: Record<string, number> = {};

  for (const [cmd, count] of commandCounts) {
    cmdCounts[cmd] = count;
    totalCommands += count;
  }
  for (const [cmd, count] of commandErrors) {
    cmdErrors[cmd] = count;
    totalErrors += count;
  }

  const avgLatency =
    bridgeLatencySamples.length > 0
      ? bridgeLatencySamples.reduce((a, b) => a + b, 0) / bridgeLatencySamples.length
      : 0;

  return {
    commands_processed_total: cmdCounts,
    command_errors_total: cmdErrors,
    active_channels: activeChannels,
    connected_users: connectedUsers,
    avg_bridge_latency_ms: Math.round(avgLatency * 100) / 100,
    total_commands: totalCommands,
    total_errors: totalErrors,
  };
}

/**
 * Reset all metrics (testing only).
 */
export function resetMetrics(): void {
  commandCounts.clear();
  commandErrors.clear();
  activeChannels = 0;
  connectedUsers = 0;
  bridgeLatencySamples.length = 0;
}
