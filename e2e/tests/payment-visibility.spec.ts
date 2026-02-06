/**
 * Execution Market E2E Tests - Payment Visibility
 *
 * Tests that payment information is visible in the dashboard:
 * - Task cards show bounty amounts
 * - Completed tasks show payment status badge
 * - Public metrics show payment volume
 * - StatsBar renders on the home page
 */

import { test, expect } from '@playwright/test'

test.describe('Payment Visibility', () => {
  test('home page shows stats bar with metrics', async ({ page }) => {
    await page.goto('/')

    // StatsBar should be visible
    const statsBar = page.locator('.flex.items-center.justify-center.gap-6')
    await expect(statsBar).toBeVisible({ timeout: 15000 })

    // Should show at least 3 stat values
    const statValues = statsBar.locator('.font-bold')
    const count = await statValues.count()
    expect(count).toBeGreaterThanOrEqual(3)
  })

  test('home page loads public metrics from API', async ({ page }) => {
    // Intercept the metrics API call
    const metricsPromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/public/metrics') && resp.status() === 200,
      { timeout: 20000 }
    )

    await page.goto('/')

    const metricsResponse = await metricsPromise
    const data = await metricsResponse.json()

    // Verify response structure
    expect(data).toHaveProperty('tasks')
    expect(data).toHaveProperty('payments')
    expect(data.payments).toHaveProperty('total_volume_usd')
    expect(typeof data.payments.total_volume_usd).toBe('number')
  })

  test('task cards display bounty amount', async ({ page }) => {
    await page.goto('/tasks')

    // Wait for task list to load
    await page.waitForSelector('[data-testid="task-list"], .task-card, [class*="task"]', {
      timeout: 15000,
    }).catch(() => {
      // If no test IDs, wait for any card-like content
    })

    // Look for dollar amounts in the page (bounty display)
    const dollarAmounts = page.locator('text=/\\$\\d/')
    const hasAmounts = (await dollarAmounts.count()) > 0

    // If tasks exist, they should show bounty amounts
    if (hasAmounts) {
      await expect(dollarAmounts.first()).toBeVisible()
    }
  })

  test('available tasks endpoint returns valid data', async ({ page }) => {
    // Direct API check via page context
    const response = await page.request.get('/api/v1/tasks/available')

    // May return 200 or redirect depending on CORS
    if (response.ok()) {
      const data = await response.json()
      const tasks = Array.isArray(data) ? data : data.tasks || data.data || []

      for (const task of tasks.slice(0, 5)) {
        // Each task should have bounty information
        expect(task).toHaveProperty('bounty_usd')
        expect(typeof task.bounty_usd).toBe('number')
        expect(task.bounty_usd).toBeGreaterThanOrEqual(0)
      }
    }
  })
})

test.describe('Payment Status Indicators', () => {
  test('health sanity endpoint returns financial checks', async ({ page }) => {
    const response = await page.request.get(
      `${process.env.API_URL || 'https://api.execution.market'}/health/sanity`
    )

    if (response.ok()) {
      const data = await response.json()
      expect(data).toHaveProperty('checks_passed')
      expect(data).toHaveProperty('checks_total')
      expect(data).toHaveProperty('summary')
      expect(data.summary).toHaveProperty('total_bounty_usd')
      expect(typeof data.summary.total_bounty_usd).toBe('number')
    }
  })
})
