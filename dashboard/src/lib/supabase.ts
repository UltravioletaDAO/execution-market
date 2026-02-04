// Execution Market Supabase Client Configuration
import { createClient } from '@supabase/supabase-js'
import type { Database } from '../types/database'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

console.log('[Supabase] Initializing with URL:', supabaseUrl, 'Key length:', supabaseAnonKey?.length)

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false,
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
