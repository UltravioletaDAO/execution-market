/**
 * Execution Market E2E Authentication Fixtures
 *
 * Uses the E2E escape hatch: injects window.__E2E_AUTH__ via page.addInitScript()
 * so AuthContext picks up mock auth state instead of Dynamic.xyz.
 *
 * Requires the dashboard to be started with VITE_E2E_MODE=true.
 */

import { test as base, type Page, expect } from '@playwright/test'

// Declare the E2E auth state type (mirrors dashboard's AuthContext declaration)
declare global {
  interface Window {
    __E2E_AUTH__?: {
      isAuthenticated: boolean
      walletAddress: string
      userId: string
      role: 'worker' | 'agent' | null
      displayName?: string
    }
  }
}

// ============================================================================
// Mock Users
// ============================================================================

export interface MockUser {
  userId: string
  walletAddress: string
  role: 'worker' | 'agent'
  displayName: string
}

export const MOCK_WORKER: MockUser = {
  userId: 'e2e-worker-001',
  walletAddress: '0xe2e0000000000000000000000000000000000001',
  role: 'worker',
  displayName: 'E2E Worker',
}

export const MOCK_AGENT: MockUser = {
  userId: 'e2e-agent-001',
  walletAddress: '0xe2e0000000000000000000000000000000000002',
  role: 'agent',
  displayName: 'E2E Agent',
}

// ============================================================================
// Auth Injection
// ============================================================================

/**
 * Inject E2E auth state into the page via window.__E2E_AUTH__.
 * Must be called BEFORE page.goto() so the script runs before React hydrates.
 */
export async function injectAuth(page: Page, user: MockUser): Promise<void> {
  await page.addInitScript((authState) => {
    window.__E2E_AUTH__ = {
      isAuthenticated: true,
      walletAddress: authState.walletAddress,
      userId: authState.userId,
      role: authState.role,
      displayName: authState.displayName,
    }
  }, user)
}

// ============================================================================
// Extended Test Fixtures
// ============================================================================

export type AuthFixtures = {
  workerPage: Page
  agentPage: Page
}

/**
 * Extended test with pre-authenticated page fixtures.
 * workerPage: Page with worker auth injected
 * agentPage: Page with agent auth injected
 */
export const test = base.extend<AuthFixtures>({
  workerPage: async ({ page }, use) => {
    await injectAuth(page, MOCK_WORKER)
    await use(page)
  },

  agentPage: async ({ page }, use) => {
    await injectAuth(page, MOCK_AGENT)
    await use(page)
  },
})

export { expect }
