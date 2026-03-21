import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { getWorkerStore } from "../services/worker-store.js";
import { formatUsdc } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

export async function handleEarnings(
  ctx: MessageContext<string>,
  _args: string[]
): Promise<void> {
  const senderAddress = await ctx.getSenderAddress();
  if (!senderAddress) {
    await ctx.sendTextReply("No se pudo resolver tu direccion.");
    return;
  }

  const store = getWorkerStore();
  const worker = store.getByAddress(senderAddress);
  if (!worker?.executorId) {
    await ctx.sendTextReply("No estas registrado. Usa /register primero.");
    return;
  }

  try {
    // Fetch payment events for this worker
    const data = await apiClient.get<any>("/api/v1/payments/events", {
      params: {
        address: senderAddress,
        event_type: "disburse_worker",
        limit: "50",
      },
    });

    const events = Array.isArray(data) ? data : (data.events ?? []);

    if (events.length === 0) {
      await ctx.sendTextReply(
        "No tienes pagos registrados aun.\nCompleta tareas para empezar a ganar!"
      );
      return;
    }

    // Calculate totals by chain
    const byChain: Record<string, number> = {};
    let total = 0;
    for (const evt of events) {
      const chain = evt.chain ?? evt.payment_network ?? "base";
      const amount = parseFloat(evt.amount ?? "0");
      byChain[chain] = (byChain[chain] ?? 0) + amount;
      total += amount;
    }

    const chainRows = Object.entries(byChain)
      .sort((a, b) => b[1] - a[1])
      .map(([chain, amt]) => `| ${chain} | $${formatUsdc(amt)} |`);

    // Last 5 payments
    const recent = events.slice(0, 5);
    const recentRows = recent.map((evt: any) => {
      const amt = formatUsdc(evt.amount ?? 0);
      const chain = evt.chain ?? evt.payment_network ?? "base";
      const date = evt.created_at
        ? new Date(evt.created_at).toLocaleDateString()
        : "---";
      return `| $${amt} | ${chain} | ${date} |`;
    });

    await ctx.sendMarkdownReply(
      `**Ganancias en Execution Market**\n\n` +
        `Total: **$${formatUsdc(total)} USDC**\n` +
        `Tareas pagadas: **${events.length}**\n\n` +
        `**Por chain:**\n` +
        `| Chain | Total |\n|-------|-------|\n` +
        chainRows.join("\n") +
        "\n\n" +
        `**Ultimos pagos:**\n` +
        `| Monto | Chain | Fecha |\n|-------|-------|-------|\n` +
        recentRows.join("\n")
    );
  } catch (err) {
    logger.error({ err }, "Failed to fetch earnings");
    await ctx.sendTextReply("Error consultando ganancias. Intenta de nuevo.");
  }
}
