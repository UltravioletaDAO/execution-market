import { base, mainnet, polygon, arbitrum, avalanche, optimism, celo } from "viem/chains";

// Monad chain definition (not in viem yet)
export const monad = {
  id: 10143,
  name: "Monad",
  nativeCurrency: { name: "MON", symbol: "MON", decimals: 18 },
  rpcUrls: {
    default: { http: ["https://rpc.monad.xyz"] },
  },
  blockExplorers: {
    default: { name: "Monad Explorer", url: "https://explorer.monad.xyz" },
  },
} as const;

export const supportedChains = [base, mainnet, polygon, arbitrum, avalanche, optimism, celo, monad] as const;
