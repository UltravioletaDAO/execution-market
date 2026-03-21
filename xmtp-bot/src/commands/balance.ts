import type { MessageContext } from "@xmtp/agent-sdk";
import { apiClient } from "../services/api-client.js";
import { formatUsdc } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";

const CHAINS = [
  "base",
  "ethereum",
  "polygon",
  "arbitrum",
  "avalanche",
  "optimism",
  "celo",
  "monad",
];

export async function handleBalance(
  ctx: MessageContext<string>,
  _args: string[]
): Promise<void> {
  const senderAddress = await ctx.getSenderAddress();
  if (!senderAddress) {
    await ctx.sendTextReply("No se pudo resolver tu direccion.");
    return;
  }

  await ctx.sendTextReply("Consultando balances...");

  try {
    const results = await Promise.allSettled(
      CHAINS.map(async (chain) => {
        const data = await apiClient.get<any>(
          `/api/v1/payments/balance/${senderAddress}`,
          { params: { network: chain } }
        );
        return {
          chain,
          balance: parseFloat(data.balance ?? data.amount ?? "0"),
        };
      })
    );

    const balances = results
      .map((r, i) => {
        if (r.status === "fulfilled" && r.value.balance > 0) {
          return r.value;
        }
        return { chain: CHAINS[i], balance: 0 };
      })
      .filter((b) => b.balance > 0);

    if (balances.length === 0) {
      await ctx.sendTextReply(
        "No tienes balance USDC en ninguna chain soportada."
      );
      return;
    }

    const total = balances.reduce((sum, b) => sum + b.balance, 0);
    const rows = balances.map(
      (b) => `| ${b.chain} | $${formatUsdc(b.balance)} |`
    );

    await ctx.sendMarkdownReply(
      `**Balance USDC**\n\n` +
        `| Chain | Balance |\n` +
        `|-------|---------|\n` +
        rows.join("\n") +
        "\n" +
        `| **Total** | **$${formatUsdc(total)}** |`
    );
  } catch (err) {
    logger.error({ err }, "Failed to fetch balances");
    await ctx.sendTextReply("Error consultando balances. Intenta de nuevo.");
  }
}
