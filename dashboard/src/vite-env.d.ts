/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Supabase
  readonly VITE_SUPABASE_URL: string
  readonly VITE_SUPABASE_ANON_KEY: string

  // API
  readonly VITE_API_URL: string

  // Blockchain (Avalanche C-Chain)
  readonly VITE_CHAIN_ID: string
  readonly VITE_ESCROW_ADDRESS: string
  readonly VITE_USDC_ADDRESS: string

  // Wallet Providers (optional)
  readonly VITE_WALLET_CONNECT_PROJECT_ID?: string
  readonly VITE_CROSSMINT_PROJECT_ID?: string

  // Feature Flags
  readonly VITE_ENABLE_TESTNET?: string
  readonly VITE_ENABLE_EMAIL_WALLETS?: string
  readonly VITE_ENABLE_STREAMING_PAYMENTS?: string

  // Analytics (optional)
  readonly VITE_GA_MEASUREMENT_ID?: string
  readonly VITE_MIXPANEL_TOKEN?: string

  // Development
  readonly VITE_MOCK_MODE?: string
  readonly VITE_DEBUG?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
