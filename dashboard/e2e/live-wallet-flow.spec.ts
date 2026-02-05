/**
 * Live smoke test for the "Start Earning" wallet connection flow.
 * Tests against the deployed site at https://execution.market
 *
 * NOTE: MetaMask/WalletConnect can't be fully tested in headless mode
 * (no browser extension), but we can verify the UI flow up to the
 * wallet selection step and check for JS errors.
 */

import { test, expect } from '@playwright/test'

const BASE_URL = 'https://execution.market'

test.describe('Start Earning Flow - Live', () => {
  test('homepage loads and renders correctly', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })

    // The page should have rendered (React hydrated)
    await expect(page.locator('#root')).not.toBeEmpty()

    // Should see the hero section with "Start Earning" or similar CTA
    const heroText = page.locator('main')
    await expect(heroText).toBeVisible()

    // Log any console errors for debugging
    if (consoleErrors.length > 0) {
      console.log('Console errors on homepage:', consoleErrors)
    }
  })

  test('"Start Earning" button opens auth modal', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })

    // Find and click the "Start Earning" button (or equivalent CTA)
    const startEarningBtn = page.getByRole('button', { name: /start earning|connect wallet|get started/i }).first()

    if (await startEarningBtn.isVisible()) {
      await startEarningBtn.click()

      // Auth modal should appear with wallet options
      const modal = page.locator('.fixed.inset-0.z-50')
      await expect(modal).toBeVisible({ timeout: 5000 })

      // Should show MetaMask option (use role to avoid matching the "email not available" notice)
      const metamaskOption = page.getByRole('button', { name: /MetaMask/i })
      await expect(metamaskOption).toBeVisible()

      // Should show WalletConnect option
      const walletConnectOption = page.getByRole('button', { name: /WalletConnect/i })
      await expect(walletConnectOption).toBeVisible()

      console.log('Auth modal opened successfully with wallet options')
    } else {
      // User might already be authenticated (session exists)
      console.log('Start Earning button not visible — user may already be authenticated')
    }

    if (consoleErrors.length > 0) {
      console.log('Console errors:', consoleErrors)
    }
  })

  test('MetaMask click does NOT close modal prematurely', async ({ page }) => {
    const consoleErrors: string[] = []
    const consoleLogs: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
      if (msg.text().includes('[AuthContext]') || msg.text().includes('Auth')) {
        consoleLogs.push(`[${msg.type()}] ${msg.text()}`)
      }
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })

    // Open auth modal
    const startEarningBtn = page.getByRole('button', { name: /start earning|connect wallet|get started/i }).first()
    if (!(await startEarningBtn.isVisible())) {
      console.log('Skipping — Start Earning not visible')
      return
    }

    await startEarningBtn.click()
    const modal = page.locator('.fixed.inset-0.z-50')
    await expect(modal).toBeVisible({ timeout: 5000 })

    // Click MetaMask
    const metamaskBtn = page.locator('button').filter({ hasText: 'MetaMask' })
    await metamaskBtn.click()

    // The key fix: modal should STAY OPEN after clicking MetaMask
    // (Previously it would close immediately because onSuccess fired prematurely)
    // Wait a moment to see if it closes
    await page.waitForTimeout(2000)

    // Modal should still be visible (MetaMask extension not available in headless,
    // so the flow can't complete, but the modal should NOT have closed)
    const isModalStillVisible = await modal.isVisible()

    // Check if there's an error about MetaMask not being available
    const errorText = page.locator('.bg-red-50')
    const hasError = await errorText.isVisible().catch(() => false)

    if (hasError) {
      const errorMessage = await errorText.textContent()
      console.log('Expected error (no MetaMask extension):', errorMessage)
      // This is fine — the point is the modal didn't close
    }

    console.log('Modal still visible after MetaMask click:', isModalStillVisible)
    console.log('Auth-related logs:', consoleLogs)

    // The critical assertion: modal should not have closed
    // It should either show an error (MetaMask not available) or show a connecting state
    expect(isModalStillVisible).toBe(true)
  })

  test('manual wallet entry flow works', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })

    const startEarningBtn = page.getByRole('button', { name: /start earning|connect wallet|get started/i }).first()
    if (!(await startEarningBtn.isVisible())) {
      console.log('Skipping — Start Earning not visible')
      return
    }

    await startEarningBtn.click()
    const modal = page.locator('.fixed.inset-0.z-50')
    await expect(modal).toBeVisible({ timeout: 5000 })

    // Click "enter your wallet manually"
    const manualEntry = page.getByText(/enter.*wallet.*manually/i)
    if (await manualEntry.isVisible()) {
      await manualEntry.click()

      // Should show wallet address input
      const walletInput = page.locator('input[placeholder="0x..."]')
      await expect(walletInput).toBeVisible()

      // Enter a test wallet address (our agent wallet)
      await walletInput.fill('YOUR_DEV_WALLET')

      // Click connect
      const connectBtn = page.getByRole('button', { name: /connect/i })
      await connectBtn.click()

      // Wait for response
      await page.waitForTimeout(3000)

      // Check what happened
      const pageUrl = page.url()
      console.log('After manual wallet connect, URL:', pageUrl)

      // If this is a returning user, should navigate to /tasks
      // If new user or error, might show profile form or error
      if (pageUrl.includes('/tasks')) {
        console.log('SUCCESS: Returning user navigated to /tasks')
      } else {
        // Check if profile modal appeared
        const profileModal = page.getByText(/complete.*profile|profile.*setup/i)
        const hasProfileModal = await profileModal.isVisible().catch(() => false)
        console.log('Profile modal visible:', hasProfileModal)
      }
    }

    if (consoleErrors.length > 0) {
      console.log('Console errors:', consoleErrors)
    }
  })

  test('page has no critical JS errors on load', async ({ page }) => {
    const criticalErrors: string[] = []
    page.on('pageerror', error => {
      criticalErrors.push(error.message)
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.waitForTimeout(2000)

    if (criticalErrors.length > 0) {
      console.log('Critical JS errors:', criticalErrors)
    }

    // No critical uncaught errors
    expect(criticalErrors.length).toBe(0)
  })
})
