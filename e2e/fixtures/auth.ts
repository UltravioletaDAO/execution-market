/**
 * Execution Market E2E Authentication Fixtures
 *
 * Helpers for authentication in E2E tests.
 */

import { test as base, type Page, expect } from '@playwright/test'
import { mockWalletConnection, mockExecutor, mockAgent } from './mocks'

// ============================================================================
// Test User Types
// ============================================================================

export interface TestUser {
  id: string
  email: string
  password: string
  displayName: string
  walletAddress: string
  role: 'executor' | 'agent'
}

export const TEST_EXECUTOR: TestUser = {
  id: 'user-001',
  email: 'executor@execution.market',
  password: 'test-password-123',
  displayName: 'Test Executor',
  walletAddress: mockExecutor.wallet_address,
  role: 'executor',
}

export const TEST_AGENT: TestUser = {
  id: 'user-agent-001',
  email: 'agent@execution.market',
  password: 'agent-password-123',
  displayName: 'Test Agent',
  walletAddress: mockAgent.wallet_address,
  role: 'agent',
}

// ============================================================================
// Authentication Helpers
// ============================================================================

/**
 * Login via email/password
 */
export async function loginWithEmail(
  page: Page,
  user: TestUser = TEST_EXECUTOR
): Promise<void> {
  await page.goto('/login')

  // Wait for login form
  await page.waitForSelector('[data-testid="login-form"]', { timeout: 10000 })

  // Fill email
  await page.fill('[data-testid="email-input"]', user.email)

  // Fill password
  await page.fill('[data-testid="password-input"]', user.password)

  // Click login button
  await page.click('[data-testid="login-button"]')

  // Wait for redirect to dashboard
  await page.waitForURL(/\/(dashboard|tasks)/, { timeout: 15000 })
}

/**
 * Login via wallet (MetaMask mock)
 */
export async function loginWithWallet(page: Page): Promise<void> {
  // Setup wallet mock
  await mockWalletConnection(page)

  await page.goto('/login')

  // Wait for login options
  await page.waitForSelector('[data-testid="wallet-login-button"]', {
    timeout: 10000,
  })

  // Click wallet login
  await page.click('[data-testid="wallet-login-button"]')

  // Wait for wallet connection modal
  await page.waitForSelector('[data-testid="wallet-connect-modal"]', {
    timeout: 5000,
  })

  // Select MetaMask (or first wallet option)
  await page.click('[data-testid="metamask-option"]')

  // Wait for signature request handling (mocked)
  await page.waitForTimeout(500)

  // Wait for redirect to dashboard
  await page.waitForURL(/\/(dashboard|tasks)/, { timeout: 15000 })
}

/**
 * Logout the current user
 */
export async function logout(page: Page): Promise<void> {
  // Click user menu
  await page.click('[data-testid="user-menu"]')

  // Click logout
  await page.click('[data-testid="logout-button"]')

  // Wait for redirect to landing/login
  await page.waitForURL(/\/(login)?$/, { timeout: 10000 })
}

/**
 * Check if user is logged in
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    await page.waitForSelector('[data-testid="user-menu"]', { timeout: 3000 })
    return true
  } catch {
    return false
  }
}

/**
 * Get current user info from page
 */
export async function getCurrentUser(
  page: Page
): Promise<{ email: string; displayName: string } | null> {
  const loggedIn = await isLoggedIn(page)
  if (!loggedIn) return null

  // Click user menu to show info
  await page.click('[data-testid="user-menu"]')

  const email = await page
    .locator('[data-testid="user-email"]')
    .textContent()
  const displayName = await page
    .locator('[data-testid="user-display-name"]')
    .textContent()

  // Close menu
  await page.keyboard.press('Escape')

  return {
    email: email || '',
    displayName: displayName || '',
  }
}

// ============================================================================
// Extended Test Fixtures
// ============================================================================

/**
 * Test fixture type with authentication helpers
 */
export type AuthFixtures = {
  authenticatedPage: Page
  executorPage: Page
  agentPage: Page
}

/**
 * Extended test with authentication
 */
export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    await loginWithEmail(page, TEST_EXECUTOR)
    await use(page)
    await logout(page)
  },

  executorPage: async ({ page }, use) => {
    await loginWithEmail(page, TEST_EXECUTOR)
    await use(page)
    await logout(page)
  },

  agentPage: async ({ page }, use) => {
    await loginWithEmail(page, TEST_AGENT)
    await use(page)
    await logout(page)
  },
})

export { expect }

// ============================================================================
// Auth Setup for Playwright Projects
// ============================================================================

/**
 * Save authentication state for reuse
 * Use in auth.setup.ts
 */
export async function saveAuthState(
  page: Page,
  path: string
): Promise<void> {
  await loginWithEmail(page, TEST_EXECUTOR)

  // Save signed-in state
  await page.context().storageState({ path })
}
