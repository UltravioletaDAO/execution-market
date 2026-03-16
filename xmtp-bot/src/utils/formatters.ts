export function formatUsdc(amount: number | string): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return num.toFixed(2);
}

export function formatDeadline(deadline: string): string {
  const d = new Date(deadline);
  const now = new Date();
  const diff = d.getTime() - now.getTime();
  if (diff <= 0) return "Expirado";
  const hours = Math.floor(diff / 3_600_000);
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  if (hours > 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

export function truncate(text: string, maxLen: number = 100): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 3) + "...";
}

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

export function txLink(chain: string, hash: string): string {
  const base = EXPLORER_URLS[chain] ?? "https://blockscan.com/tx/";
  return `${base}${hash}`;
}

export function chainName(chain: string): string {
  const names: Record<string, string> = {
    base: "Base",
    ethereum: "Ethereum",
    polygon: "Polygon",
    arbitrum: "Arbitrum",
    avalanche: "Avalanche",
    optimism: "Optimism",
    celo: "Celo",
    monad: "Monad",
  };
  return names[chain] ?? chain;
}

export function chainToCaip2(chain: string): string | undefined {
  return CHAIN_TO_CAIP2[chain];
}

export function formatPaymentReceipt(opts: {
  amount: number | string;
  chain: string;
  txHash: string;
  taskTitle?: string;
  workerShare?: number | string;
}): string {
  const amount = formatUsdc(opts.amount);
  const net = opts.workerShare ? formatUsdc(opts.workerShare) : null;
  const explorer = txLink(opts.chain, opts.txHash);
  const shortHash = `${opts.txHash.slice(0, 10)}...${opts.txHash.slice(-6)}`;

  const lines = [
    `**Pago Recibido**\n`,
    `| Campo | Valor |`,
    `|-------|-------|`,
    `| Bounty | $${amount} USDC |`,
  ];

  if (net) {
    lines.push(`| Recibido (87%) | $${net} USDC |`);
  }

  lines.push(
    `| Chain | ${chainName(opts.chain)} |`,
    `| TX | [${shortHash}](${explorer}) |`,
  );

  if (opts.taskTitle) {
    lines.push(`| Tarea | ${truncate(opts.taskTitle, 40)} |`);
  }

  return lines.join("\n");
}
