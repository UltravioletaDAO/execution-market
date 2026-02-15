// Execution Market Supabase Client Configuration
import { createClient } from '@supabase/supabase-js'
import type { Database } from '../types/database'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

console.log('[Supabase] Initializing with URL:', supabaseUrl, 'Key length:', supabaseAnonKey?.length)

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

const noOpLock = async <R>(_name: string, _timeout: number, fn: () => Promise<R>): Promise<R> => {
  return await fn()
}

// Temporary escape hatch for shipping:
// schema/type drift between runtime DB and static TS types currently breaks
// query builder inference across the app. Re-enable strict DB generics once
// types are regenerated from the canonical production schema.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const supabase: any = createClient<any>(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Dynamic.xyz handles wallet auth; Supabase session persists the
    // anonymous user + wallet link so users stay logged in across reloads.
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false,
    // Avoid Web Locks API deadlocks in some browsers
    lock: noOpLock,
    storage: typeof window !== 'undefined' ? window.localStorage : undefined,
  },
  global: {
    headers: {
      'x-client-info': 'execution-market-dashboard',
    },
  },
})

// Warm-up: Make a simple fetch to "unblock" the Supabase client
// This works around an issue where the JS client hangs until a direct fetch is made
if (typeof window !== 'undefined') {
  fetch(`${supabaseUrl}/rest/v1/tasks?select=id&limit=1`, {
    headers: { 'apikey': supabaseAnonKey },
  }).then(() => {
    console.log('[Supabase] Warm-up completed successfully')
  }).catch((err) => {
    console.error('[Supabase] Warm-up failed:', err)
  })
  console.log('[Supabase] Warm-up request sent')
}

// Helper for typed queries
export type Tables<T extends keyof Database['public']['Tables']> =
  Database['public']['Tables'][T]['Row']

export type InsertTables<T extends keyof Database['public']['Tables']> =
  Database['public']['Tables'][T]['Insert']

export type UpdateTables<T extends keyof Database['public']['Tables']> =
  Database['public']['Tables'][T]['Update']
