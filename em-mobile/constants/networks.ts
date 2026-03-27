export const NETWORKS = [
  { key: "base", name: "Base", chainId: 8453, explorer: "https://basescan.org", color: "#0052FF" },
  { key: "ethereum", name: "Ethereum", chainId: 1, explorer: "https://etherscan.io", color: "#627EEA" },
  { key: "polygon", name: "Polygon", chainId: 137, explorer: "https://polygonscan.com", color: "#8247E5" },
  { key: "arbitrum", name: "Arbitrum", chainId: 42161, explorer: "https://arbiscan.io", color: "#28A0F0" },
  { key: "avalanche", name: "Avalanche", chainId: 43114, explorer: "https://snowtrace.io", color: "#E84142" },
  { key: "optimism", name: "Optimism", chainId: 10, explorer: "https://optimistic.etherscan.io", color: "#FF0420" },
  { key: "celo", name: "Celo", chainId: 42220, explorer: "https://celoscan.io", color: "#FCFF52" },
  { key: "monad", name: "Monad", chainId: 143, explorer: "https://explorer.monad.xyz", color: "#836EF9" },
  { key: "skale", name: "SKALE", chainId: 1187947933, explorer: "https://skale-base-explorer.skalenodes.com", color: "#000000" },
] as const;

export function getExplorerTxUrl(network: string, txHash: string): string {
  const net = NETWORKS.find((n) => n.key === network);
  return net ? `${net.explorer}/tx/${txHash}` : `https://basescan.org/tx/${txHash}`;
}
