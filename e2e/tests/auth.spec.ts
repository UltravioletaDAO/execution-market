/**
 * Chamba E2E Tests - Authentication
 *
 * Tests for user authentication flows:
 * - Landing page
 * - Login modal
 * - Wallet connection
 * - Email login
 * - Logout
 */

import { test, expect } from '@playwright/test'
import { setupMocks, mockWalletConnection } from '../fixtures/mocks'
import {
  TEST_EXECUTOR,
  TEST_AGENT,
  loginWithEmail,
  loginWithWallet,
  logout,
  isLoggedIn,
} from '../fixtures/auth'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Setup mocks before each test
    await setupMocks(page)
    await mockWalletConnection(page)
  })

  test.describe('Landing Page', () => {
    test('landing page loads successfully', async ({ page }) => {
      await page.goto('/')

      // Check page title
      await expect(page).toHaveTitle(/Chamba/)

      // Check main heading is visible
      const heading = page.locator('h1')
      await expect(heading).toBeVisible()

      // Check CTA button exists
      const ctaButton = page.locator('[data-testid="cta-button"]')
      await expect(ctaButton).toBeVisible()
    })

    test('landing page shows key features', async ({ page }) => {
      await page.goto('/')

      // Check for key feature sections
      await expect(page.locator('text=Human Tasks')).toBeVisible()
      await expect(page.locator('text=AI Agents')).toBeVisible()

      // Check for payment info
      await expect(page.locator('text=USDC')).toBeVisible()
    })

    test('CTA button navigates to login', async ({ page }) => {
      await page.goto('/')

      // Click CTA
      await page.click('[data-testid="cta-button"]')

      // Should navigate to login or show modal
      await expect(
        page.locator('[data-testid="login-form"], [data-testid="login-modal"]')
      ).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Login Modal', () => {
    test('can open login modal from header', async ({ page }) => {
      await page.goto('/')

      // Click login button in header
      await page.click('[data-testid="header-login-button"]')

      // Modal should appear
      const modal = page.locator('[data-testid="login-modal"]')
      await expect(modal).toBeVisible()

      // Modal should have both login options
      await expect(
        page.locator('[data-testid="email-login-option"]')
      ).toBeVisible()
      await expect(
        page.locator('[data-testid="wallet-login-option"]')
      ).toBeVisible()
    })

    test('can close login modal', async ({ page }) => {
      await page.goto('/')

      // Open modal
      await page.click('[data-testid="header-login-button"]')
      await expect(page.locator('[data-testid="login-modal"]')).toBeVisible()

      // Close via X button
      await page.click('[data-testid="modal-close-button"]')

      // Modal should be hidden
      await expect(
        page.locator('[data-testid="login-modal"]')
      ).not.toBeVisible()
    })

    test('can close login modal with Escape key', async ({ page }) => {
      await page.goto('/')

      // Open modal
      await page.click('[data-testid="header-login-button"]')
      await expect(page.locator('[data-testid="login-modal"]')).toBeVisible()

      // Press Escape
      await page.keyboard.press('Escape')

      // Modal should be hidden
      await expect(
        page.locator('[data-testid="login-modal"]')
      ).not.toBeVisible()
    })
  })

  test.describe('Wallet Connection', () => {
    test('can connect wallet (mock MetaMask)', async ({ page }) => {
      await page.goto('/login')

      // Click wallet login button
      await page.click('[data-testid="wallet-login-button"]')

      // Wallet connect modal should appear
      await expect(
        page.locator('[data-testid="wallet-connect-modal"]')
      ).toBeVisible()

      // Select MetaMask option
      await page.click('[data-testid="metamask-option"]')

      // Wait for mock wallet connection
      await page.waitForTimeout(500)

      // Should redirect to dashboard
      await expect(page).toHaveURL(/\/(dashboard|tasks)/)
    })

    test('shows wallet address after connection', async ({ page }) => {
      await page.goto('/login')

      // Connect wallet
      await page.click('[data-testid="wallet-login-button"]')
      await page.click('[data-testid="metamask-option"]')

      // Wait for navigation
      await page.waitForURL(/\/(dashboard|tasks)/)

      // Check wallet address is shown (truncated)
      const walletDisplay = page.locator('[data-testid="wallet-address"]')
      await expect(walletDisplay).toBeVisible()
      await expect(walletDisplay).toContainText('0x1234')
    })

    test('handles wallet connection rejection', async ({ page }) => {
      // Override wallet mock to reject
      await page.addInitScript(() => {
        window.ethereum = {
          ...window.ethereum,
          request: async ({ method }: { method: string }) => {
            if (method === 'eth_requestAccounts') {
              throw new Error('User rejected the request')
            }
            return null
          },
        }
      })

      await page.goto('/login')
      await page.click('[data-testid="wallet-login-button"]')
      await page.click('[data-testid="metamask-option"]')

      // Should show error message
      await expect(page.locator('[data-testid="connection-error"]')).toBeVisible()
      await expect(page.locator('text=rejected')).toBeVisible()
    })
  })

  test.describe('Email Login', () => {
    test('can login with email', async ({ page }) => {
      await page.goto('/login')

      // Wait for login form
      await expect(page.locator('[data-testid="login-form"]')).toBeVisible()

      // Fill credentials
      await page.fill('[data-testid="email-input"]', TEST_EXECUTOR.email)
      await page.fill('[data-testid="password-input"]', TEST_EXECUTOR.password)

      // Submit
      await page.click('[data-testid="login-button"]')

      // Should redirect to dashboard
      await expect(page).toHaveURL(/\/(dashboard|tasks)/)
    })

    test('shows error for invalid credentials', async ({ page }) => {
      // Override auth mock to return error
      await page.route('**/auth/v1/token*', async (route) => {
        await route.fulfill({
          status: 400,
          body: JSON.stringify({
            error: 'invalid_grant',
            error_description: 'Invalid login credentials',
          }),
        })
      })

      await page.goto('/login')

      // Fill wrong credentials
      await page.fill('[data-testid="email-input"]', 'wrong@email.com')
      await page.fill('[data-testid="password-input"]', 'wrongpassword')
      await page.click('[data-testid="login-button"]')

      // Should show error
      await expect(page.locator('[data-testid="login-error"]')).toBeVisible()
      await expect(page.locator('text=Invalid')).toBeVisible()
    })

    test('validates email format', async ({ page }) => {
      await page.goto('/login')

      // Enter invalid email
      await page.fill('[data-testid="email-input"]', 'not-an-email')
      await page.fill('[data-testid="password-input"]', 'somepassword')
      await page.click('[data-testid="login-button"]')

      // Should show validation error
      const emailInput = page.locator('[data-testid="email-input"]')
      await expect(emailInput).toHaveAttribute('aria-invalid', 'true')
    })

    test('requires password', async ({ page }) => {
      await page.goto('/login')

      // Enter only email
      await page.fill('[data-testid="email-input"]', TEST_EXECUTOR.email)
      await page.click('[data-testid="login-button"]')

      // Password field should show error
      const passwordInput = page.locator('[data-testid="password-input"]')
      await expect(passwordInput).toHaveAttribute('aria-invalid', 'true')
    })
  })

  test.describe('Post-Login Redirect', () => {
    test('redirects to dashboard after login', async ({ page }) => {
      await loginWithEmail(page, TEST_EXECUTOR)

      // Should be on dashboard
      await expect(page).toHaveURL(/\/(dashboard|tasks)/)
    })

    test('redirects to original page after login', async ({ page }) => {
      // Try to access protected page
      await page.goto('/tasks/task-001')

      // Should redirect to login with return URL
      await expect(page).toHaveURL(/\/login\?redirect=/)

      // Login
      await page.fill('[data-testid="email-input"]', TEST_EXECUTOR.email)
      await page.fill('[data-testid="password-input"]', TEST_EXECUTOR.password)
      await page.click('[data-testid="login-button"]')

      // Should redirect back to original page
      await expect(page).toHaveURL(/\/tasks\/task-001/)
    })

    test('agent login redirects to agent dashboard', async ({ page }) => {
      await loginWithEmail(page, TEST_AGENT)

      // Should be on agent dashboard
      await expect(page).toHaveURL(/\/agent/)
    })
  })

  test.describe('Logout', () => {
    test('can logout', async ({ page }) => {
      // Login first
      await loginWithEmail(page, TEST_EXECUTOR)

      // Verify logged in
      expect(await isLoggedIn(page)).toBe(true)

      // Logout
      await logout(page)

      // Should be on landing or login page
      await expect(page).toHaveURL(/\/(login)?$/)

      // User menu should not be visible
      await expect(page.locator('[data-testid="user-menu"]')).not.toBeVisible()
    })

    test('clears session on logout', async ({ page }) => {
      // Login
      await loginWithEmail(page, TEST_EXECUTOR)

      // Logout
      await logout(page)

      // Try to access protected page
      await page.goto('/tasks')

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/)
    })

    test('logout from any page works', async ({ page }) => {
      // Login and navigate to a deep page
      await loginWithEmail(page, TEST_EXECUTOR)
      await page.goto('/tasks/task-001')

      // Logout from there
      await logout(page)

      // Should still redirect properly
      await expect(page).toHaveURL(/\/(login)?$/)
    })
  })

  test.describe('Session Persistence', () => {
    test('maintains login across page navigation', async ({ page }) => {
      await loginWithEmail(page, TEST_EXECUTOR)

      // Navigate to different pages
      await page.goto('/tasks')
      expect(await isLoggedIn(page)).toBe(true)

      await page.goto('/profile')
      expect(await isLoggedIn(page)).toBe(true)

      await page.goto('/')
      expect(await isLoggedIn(page)).toBe(true)
    })

    test('maintains login on page refresh', async ({ page }) => {
      await loginWithEmail(page, TEST_EXECUTOR)

      // Refresh page
      await page.reload()

      // Should still be logged in
      expect(await isLoggedIn(page)).toBe(true)
    })
  })
})
