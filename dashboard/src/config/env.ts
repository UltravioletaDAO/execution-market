/**
 * Frontend environment validator — Task 4.2 (SaaS Production Hardening).
 *
 * Validates required Vite env vars at module-load time so the app fails
 * loudly during boot instead of producing silent warnings or broken flows
 * later (e.g. `DynamicProvider` quietly refusing to authenticate).
 *
 * Import this module FIRST in `main.tsx`. Any missing required variable
 * raises and prevents the app from mounting.
 */

import { z } from 'zod'

const booleanish = z
  .string()
  .optional()
  .transform((v) => (v ?? '').toLowerCase() === 'true')

const EnvSchema = z
  .object({
    // Required — Supabase
    VITE_SUPABASE_URL: z.string().url(),
    VITE_SUPABASE_ANON_KEY: z.string().min(20, {
      message: 'VITE_SUPABASE_ANON_KEY looks too short to be valid',
    }),

    // Required — REST API backend
    VITE_API_URL: z
      .string()
      .url()
      .or(z.string().startsWith('/'))
      .default('https://api.execution.market'),

    // Optional — evidence API (S3 presigned URL pipeline)
    VITE_EVIDENCE_API_URL: z.string().url().optional(),

    // Optional — auth (Dynamic.xyz)
    VITE_DYNAMIC_ENVIRONMENT_ID: z.string().optional(),

    // Optional — observability
    VITE_SENTRY_DSN: z.string().url().optional().or(z.literal('').optional()),
    VITE_GIT_SHA: z.string().optional(),
    VITE_BUILD_TIMESTAMP: z.string().optional(),

    // Feature flags (all default false)
    VITE_ENABLE_TESTNET: booleanish,
    VITE_REQUIRE_AGENT_API_KEY: booleanish,
    VITE_ENABLE_EVIDENCE_CAROUSEL: booleanish,
    VITE_WORLD_ID_ENABLED: booleanish,
    VITE_E2E_MODE: booleanish,
  })
  .passthrough()

export type Env = z.infer<typeof EnvSchema>

function validate(): Env {
  const parsed = EnvSchema.safeParse(import.meta.env)
  if (!parsed.success) {
    const issues = parsed.error.issues
      .map((i) => `  - ${i.path.join('.')}: ${i.message}`)
      .join('\n')
    const message = `Frontend env validation failed:\n${issues}\n\nCheck dashboard/.env.local or the build environment.`
    console.error('[env]', message)
    throw new Error(message)
  }
  return parsed.data
}

export const env = validate()
