import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { formatUsdc, formatDeadline, shortId, truncate } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

// Cache agent reputation scores for 5 minutes
const reputationCache = new Map<string, { score: number; ts: number }>();
const REPUTATION_TTL = 5 * 60 * 1000;

async function getAgentScore(agentId: string): Promise<string> {
  try {
    const cached = reputationCache.get(agentId);
    if (cached && Date.now() - cached.ts < REPUTATION_TTL) {
      return `(\u2605 ${cached.score.toFixed(1)})`;
    }

    const rep = await apiClient.get<any>(`/api/v1/reputation/${agentId}`);
    const score = rep?.average_score ?? rep?.score;
    if (score != null && typeof score === "number") {
      reputationCache.set(agentId, { score, ts: Date.now() });
      return `(\u2605 ${score.toFixed(1)})`;
    }
  } catch {
    // Silently skip if reputation API fails
  }
  return "";
}

export async function handleTasks(
  ctx: MessageContext<string>,
  args: string[]
): Promise<void> {
  try {
    const category = args[0];
    const params: Record<string, string> = { status: "published", limit: "10" };
    if (category) params.category = category;

    const data = await apiClient.get<any>("/api/v1/tasks", { params });
    const tasks = Array.isArray(data) ? data : data.tasks ?? [];

    if (tasks.length === 0) {
      await ctx.sendTextReply("No hay tareas disponibles en este momento.");
      return;
    }

    // Fetch agent scores in parallel
    const agentIds: string[] = [...new Set(tasks.map((t: any) => t.agent_id).filter(Boolean))] as string[];
    await Promise.all(agentIds.map((id) => getAgentScore(id)));

    const lines = ["**Tareas disponibles:**\n"];
    for (const t of tasks) {
      const score = t.agent_id ? await getAgentScore(t.agent_id) : "";
      const scoreStr = score ? ` ${score}` : "";
      lines.push(
        `- \`${shortId(t.id)}\` **${truncate(t.title, 40)}**${scoreStr} — $${formatUsdc(t.bounty_usdc ?? t.bounty)} USDC — ${formatDeadline(t.deadline)}`
      );
    }
    lines.push("\nUsa `/apply <id>` para aplicar.");
    await ctx.sendMarkdownReply(lines.join("\n"));
  } catch (err) {
    logger.error({ err }, "Failed to fetch tasks");
    await ctx.sendTextReply("Error al obtener tareas. Intenta de nuevo.");
  }
}
