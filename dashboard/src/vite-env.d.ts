/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Supabase
  readonly VITE_SUPABASE_URL: string
  readonly VITE_SUPABASE_ANON_KEY: string

  // API
  readonly VITE_API_URL: string
  readonly VITE_API_KEY?: string

  // Evidence Storage (S3 presigned URL pipeline)
  readonly VITE_EVIDENCE_API_URL?: string

  // Auth (Dynamic.xyz — email login configured in Dynamic Dashboard, not here)
  readonly VITE_DYNAMIC_ENVIRONMENT_ID?: string

  // Feature Flags
  readonly VITE_ENABLE_TESTNET?: string
  readonly VITE_REQUIRE_AGENT_API_KEY?: string

  // (VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS removed — DB-008 security lockdown)
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
