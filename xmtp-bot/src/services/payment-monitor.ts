import { getAgent } from "../agent.js";
import { formatUsdc } from "../utils/formatters.js";
import { logger } from "../utils/logger.js";
import type { TransactionReference } from "@xmtp/node-sdk";

// Block explorer URLs per chain
const EXPLORER_URLS: Record<string, string> = {
  base: "https://basescan.org/tx/",
  ethereum: "https://etherscan.io/tx/",
  polygon: "https://polygonscan.com/tx/",
  arbitrum: "https://arbiscan.io/tx/",
  avalanche: "https://snowtrace.io/tx/",
  optimism: "https://optimistic.etherscan.io/tx/",
  celo: "https://celoscan.io/tx/",
  monad: "https://explorer.monad.xyz/tx/",
};

// CAIP-2 chain IDs for XMTP TransactionReference
const CHAIN_TO_CAIP2: Record<string, string> = {
  base: "eip155:8453",
  ethereum: "eip155:1",
  polygon: "eip155:137",
  arbitrum: "eip155:42161",
  avalanche: "eip155:43114",
  optimism: "eip155:10",
  celo: "eip155:42220",
  monad: "eip155:10143",
};

// Track notified TX hashes to avoid duplicates
const notifiedTxHashes = new Set<string>();

export function txLink(chain: string, hash: string): string {
  const base = EXPLORER_URLS[chain] ?? "https://blockscan.com/tx/";
  return `${base}${hash}`;
}

/**
 * Handle a payment event from the WebSocket listener.
 * Sends both a markdown receipt and a native TransactionReference to the worker.
 */
export async function handlePaymentEvent(event: {
  type: string;
  worker_address?: string;
  executor_wallet?: string;
  tx_hash?: string;
  amount?: string | number;
  chain?: string;
  payment_network?: string;
  task_title?: string;
  task_id?: string;
}): Promise<void> {
  const workerAddress = event.worker_address ?? event.executor_wallet;
  const txHash = event.tx_hash;
  const chain = event.chain ?? event.payment_network ?? "base";

  if (!workerAddress || !txHash) {
    logger.debug({ event: event.type }, "Payment event missing address or tx_hash");
    return;
  }

  // Deduplicate
  if (notifiedTxHashes.has(txHash)) return;
  notifiedTxHashes.add(txHash);

  // Prune old entries (keep last 1000)
  if (notifiedTxHashes.size > 1000) {
    const entries = Array.from(notifiedTxHashes);
    for (let i = 0; i < entries.length - 1000; i++) {
      notifiedTxHashes.delete(entries[i]);
    }
  }

  try {
    const agent = getAgent();
    const dm = await agent.createDmWithAddress(workerAddress as `0x${string}`);

    const amount = event.amount ? formatUsdc(event.amount) : "?";
    const explorerLink = txLink(chain, txHash);

    // 1. Send markdown receipt
    await dm.sendText(
      `**Pago Recibido!**\n\n` +
        `| Campo | Valor |\n` +
        `|-------|-------|\n` +
        `| Monto | $${amount} USDC |\n` +
        `| Chain | ${chain} |\n` +
        `| TX | ${explorerLink} |\n` +
        `| Tarea | ${event.task_title ?? event.task_id ?? "\u2014"} |`,
    );

    // 2. Send native TransactionReference (renders natively in XMTP clients)
    const networkId = CHAIN_TO_CAIP2[chain];
    if (networkId) {
      const amountNum =
        typeof event.amount === "string"
          ? parseFloat(event.amount)
          : (event.amount ?? 0);

      const txRef: TransactionReference = {
        namespace: "eip155",
        networkId,
        reference: txHash,
        metadata: {
          transactionType: "transfer",
          currency: "USDC",
          amount: amountNum,
          decimals: 6,
          fromAddress: "", // agent address not available in event
          toAddress: workerAddress,
        },
      };

      await dm.sendTransactionReference(txRef);
      logger.info({ txHash, chain, worker: workerAddress }, "Payment notification sent with TX reference");
    } else {
      logger.info({ txHash, chain, worker: workerAddress }, "Payment notification sent (no CAIP-2 mapping)");
    }
  } catch (err) {
    logger.error({ err, worker: workerAddress, txHash }, "Failed to send payment notification");
  }
}
