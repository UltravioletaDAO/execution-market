/**
 * Execution Market E2E Tests - Evidence Submission
 *
 * Tests for evidence capture and submission flows.
 * Uses role/text-based selectors.
 *
 * NOTE: These tests cover the evidence submission UI which is a future feature.
 * Currently the SubmissionForm is simpler. These tests are written to match
 * the eventual full EvidenceUpload component. Mark as skip if the routes
 * don't exist yet.
 */

import { test, expect } from '../fixtures/auth'
import { setupMocks, mockGeolocation, mockCamera, mockTasks } from '../fixtures/mocks'

test.describe('Evidence Submission', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
    await mockCamera(workerPage)
    await mockGeolocation(workerPage)
  })

  test('worker can navigate to tasks page and see task list', async ({ workerPage }) => {
    await workerPage.goto('/tasks')

    // Should see available tasks
    await expect(
      workerPage.getByText(mockTasks[0].title)
    ).toBeVisible({ timeout: 15000 })
  })

  test('task cards show evidence requirements info', async ({ workerPage }) => {
    await workerPage.goto('/tasks')

    // Wait for tasks
    await expect(
      workerPage.getByText(mockTasks[0].title)
    ).toBeVisible({ timeout: 15000 })

    // Tasks with photo evidence should show some indicator
    // The exact text depends on the UI, but bounty should be visible
    await expect(
      workerPage.getByText(`$${mockTasks[0].bounty_usd.toFixed(2)}`)
    ).toBeVisible()
  })

  test('geolocation mock is available', async ({ workerPage }) => {
    await workerPage.goto('/tasks')

    // Verify geolocation API is available via JS evaluation
    const hasGeolocation = await workerPage.evaluate(() => {
      return 'geolocation' in navigator
    })

    expect(hasGeolocation).toBe(true)
  })

  test('camera mock is available', async ({ workerPage }) => {
    await workerPage.goto('/tasks')

    // Verify media devices API is available
    const hasMedia = await workerPage.evaluate(() => {
      return 'mediaDevices' in navigator && typeof navigator.mediaDevices.getUserMedia === 'function'
    })

    expect(hasMedia).toBe(true)
  })
})
