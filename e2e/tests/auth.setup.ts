/**
 * Chamba E2E Auth Setup
 *
 * This file runs before other tests to set up authentication state.
 */

import { test as setup } from '@playwright/test'
import { setupMocks, mockWalletConnection } from '../fixtures/mocks'
import { TEST_EXECUTOR, loginWithEmail } from '../fixtures/auth'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  // Setup API mocks
  await setupMocks(page)

  // Setup wallet mock
  await mockWalletConnection(page)

  // Login with test executor
  await loginWithEmail(page, TEST_EXECUTOR)

  // Verify we're logged in
  await page.waitForURL(/\/(dashboard|tasks)/, { timeout: 15000 })

  // Save authentication state
  await page.context().storageState({ path: authFile })
})
