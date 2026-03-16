import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { logger } from "../utils/logger.js";

export async function handleReputation(
  ctx: MessageContext<string>,
  args: string[]
): Promise<void> {
  const senderAddress = await ctx.getSenderAddress();
  if (!senderAddress) {
    await ctx.sendTextReply("No se pudo resolver tu direccion.");
    return;
  }

  const targetAddress = args[0] ?? senderAddress;

  try {
    const data = await apiClient.get<any>(
      `/api/v1/reputation/${targetAddress}`
    );

    const score = data.average_score ?? data.score ?? 0;
    const count = data.total_ratings ?? data.count ?? 0;
    const isSelf =
      targetAddress.toLowerCase() === senderAddress.toLowerCase();
    const label = isSelf
      ? "Tu reputacion"
      : `Reputacion de ${targetAddress.slice(0, 6)}...${targetAddress.slice(-4)}`;

    if (count === 0) {
      await ctx.sendTextReply(
        isSelf
          ? "Aun no tienes ratings. Completa tareas para construir reputacion!"
          : `${targetAddress.slice(0, 10)}... no tiene ratings aun.`
      );
      return;
    }

    const stars =
      "\u2605".repeat(Math.round(score)) +
      "\u2606".repeat(5 - Math.round(score));
    const lines = [
      `**${label}** ${stars}\n`,
      `| Metrica | Valor |`,
      `|---------|-------|`,
      `| Score promedio | ${score.toFixed(1)}/5.0 |`,
      `| Total ratings | ${count} |`,
    ];

    if (data.agent_id) {
      lines.push(`| Agent ID | #${data.agent_id} |`);
    }

    // Recent reviews
    const reviews = data.recent_reviews ?? data.reviews ?? [];
    if (reviews.length > 0) {
      lines.push("\n**Ultimos reviews:**");
      for (const r of reviews.slice(0, 3)) {
        const rStars =
          "\u2605".repeat(r.score) + "\u2606".repeat(5 - r.score);
        const from = r.from_address
          ? `${r.from_address.slice(0, 6)}...`
          : "Anonimo";
        lines.push(
          `- ${rStars} — ${r.comment ?? "Sin comentario"} — _${from}_`
        );
      }
    }

    await ctx.sendMarkdownReply(lines.join("\n"));
  } catch (err: any) {
    if (err?.response?.status === 404) {
      await ctx.sendTextReply(
        "No se encontro informacion de reputacion para esa direccion."
      );
    } else {
      logger.error({ err, target: targetAddress }, "Reputation query failed");
      await ctx.sendTextReply("Error consultando reputacion. Intenta de nuevo.");
    }
  }
}
