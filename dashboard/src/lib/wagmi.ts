import { http, createConfig } from 'wagmi'
import { base, baseSepolia, mainnet, sepolia, optimism } from 'wagmi/chains'
import { injected, walletConnect } from 'wagmi/connectors'

// WalletConnect project ID - get one at https://cloud.walletconnect.com
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'demo'

export const wagmiConfig = createConfig({
  chains: [base, baseSepolia, mainnet, sepolia, optimism],
  connectors: [
    injected(),
    walletConnect({
      projectId,
      metadata: {
        name: 'Execution Market',
        description: 'Human Execution Layer for AI Agents',
        url: 'https://execution.market',
        icons: ['https://execution.market/icon.png'],
      },
    }),
  ],
  transports: {
    [base.id]: http(),
    [baseSepolia.id]: http(),
    [mainnet.id]: http(),
    [sepolia.id]: http(),
    [optimism.id]: http(),
  },
})

declare module 'wagmi' {
  interface Register {
    config: typeof wagmiConfig
  }
}
