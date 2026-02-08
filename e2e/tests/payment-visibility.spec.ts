/**
 * Execution Market E2E Tests - Payment Visibility
 */

import { test as base, expect } from '@playwright/test'
import { test } from '../fixtures/auth'
import { setupMocks, mockTasks } from '../fixtures/mocks'

base.describe('Payment Visibility - Public', () => {
  base.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  base('home page includes payment-related trust text', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/USDC|x402|Instant/i).first()).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Payment Visibility - Worker', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/tasks')
  })

  test('task cards display bounty amounts', async ({ workerPage }) => {
    await expect(workerPage.getByText(mockTasks[0].title)).toBeVisible({ timeout: 15000 })

    await expect(
      workerPage.getByText(`$${mockTasks[0].bounty_usd.toFixed(2)}`)
    ).toBeVisible()
  })

  test('multiple tasks show their respective bounties', async ({ workerPage }) => {
    await expect(workerPage.getByText(mockTasks[0].title)).toBeVisible({ timeout: 15000 })

    for (const task of mockTasks) {
      await expect(workerPage.getByText(`$${task.bounty_usd.toFixed(2)}`)).toBeVisible()
    }
  })
})
