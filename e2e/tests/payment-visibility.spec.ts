/**
 * Execution Market E2E Tests - Payment Visibility
 *
 * Tests that payment information is visible in the dashboard:
 * - Task cards show bounty amounts
 * - StatsBar renders on the home page
 * - USDC branding is visible
 */

import { test, expect } from '../fixtures/auth'
import { setupMocks, mockTasks } from '../fixtures/mocks'

test.describe('Payment Visibility', () => {
  test('home page loads with stats section', async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/')

    // Should show USDC or payment-related text
    await expect(
      workerPage.getByText(/USDC/).first()
    ).toBeVisible({ timeout: 15000 })
  })

  test('task cards display bounty amounts', async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/tasks')

    // Wait for tasks to load
    await expect(
      workerPage.getByText(mockTasks[0].title)
    ).toBeVisible({ timeout: 15000 })

    // Should show dollar amounts (bounties)
    await expect(
      workerPage.getByText(`$${mockTasks[0].bounty_usd.toFixed(2)}`)
    ).toBeVisible()
  })

  test('multiple tasks show their respective bounties', async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/tasks')

    // Wait for tasks
    await expect(
      workerPage.getByText(mockTasks[0].title)
    ).toBeVisible({ timeout: 15000 })

    // Verify each task's bounty is displayed
    for (const task of mockTasks) {
      await expect(
        workerPage.getByText(`$${task.bounty_usd.toFixed(2)}`)
      ).toBeVisible()
    }
  })

  test('trust signals mention instant payment', async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/')

    // The landing page should mention instant/fast payment somewhere
    await expect(
      workerPage.getByText(/instant|Paid in USDC|No hidden fees/).first()
    ).toBeVisible({ timeout: 15000 })
  })
})
