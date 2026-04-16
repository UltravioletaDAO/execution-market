/**
 * Neutral module: AuthContext React context object + AuthContextValue type.
 *
 * Extracted here to break the circular dependency:
 *   AuthContext.tsx  <--re-exports-- hooks.ts  <--imports-- AuthContext.tsx
 *
 * Both AuthContext.tsx and hooks.ts import from this file.
 * Neither depends on the other via this path.
 */

import { createContext } from 'react'
import type { Executor } from '../types/database'

export type UserType = 'worker' | 'agent' | null

export interface AuthContextValue {
  // State
  walletAddress: string | null
  executor: Executor | null
  userType: UserType
  isAuthenticated: boolean
  isProfileComplete: boolean
  loading: boolean
  error: Error | null

  // Actions
  logout: () => Promise<void>
  setUserType: (type: UserType) => void
  refreshExecutor: () => Promise<void>
  openAuthModal: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
