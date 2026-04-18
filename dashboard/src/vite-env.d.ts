/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Supabase
  readonly VITE_SUPABASE_URL: string
  readonly VITE_SUPABASE_ANON_KEY: string

  // API
  readonly VITE_API_URL: string

  // Evidence Storage (S3 presigned URL pipeline)
  readonly VITE_EVIDENCE_API_URL?: string

  // Auth (Dynamic.xyz — email login configured in Dynamic Dashboard, not here)
  readonly VITE_DYNAMIC_ENVIRONMENT_ID?: string

  // Observability (Task 1.6 — Sentry React)
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_GIT_SHA?: string
  readonly VITE_BUILD_TIMESTAMP?: string

  // Feature Flags
  readonly VITE_ENABLE_TESTNET?: string
  readonly VITE_REQUIRE_AGENT_API_KEY?: string
  readonly VITE_ENABLE_EVIDENCE_CAROUSEL?: string
  readonly VITE_WORLD_ID_ENABLED?: string
  readonly VITE_E2E_MODE?: string

  // (VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS removed — DB-008 security lockdown)
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
