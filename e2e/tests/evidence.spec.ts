/**
 * Chamba E2E Tests - Evidence Submission
 *
 * Tests for evidence capture and submission:
 * - Camera capture (mocked)
 * - Location capture
 * - File upload
 * - Evidence submission
 */

import { test, expect } from '@playwright/test'
import {
  setupMocks,
  mockCamera,
  mockGeolocation,
  mockTasks,
} from '../fixtures/mocks'
import { loginWithEmail, TEST_EXECUTOR } from '../fixtures/auth'

test.describe('Evidence Submission', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
    await loginWithEmail(page, TEST_EXECUTOR)

    // Setup device mocks
    await mockCamera(page)
    await mockGeolocation(page, { latitude: -12.0464, longitude: -77.0428 })
  })

  test.describe('Camera Capture', () => {
    test('can open camera (mocked)', async ({ page }) => {
      const task = mockTasks.find(
        (t) =>
          t.evidence_schema.required.includes('photo') ||
          t.evidence_schema.required.includes('photo_geo')
      )!

      // Navigate to evidence submission
      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Click camera button
      await page.click('[data-testid="open-camera"]')

      // Camera preview should appear
      await expect(
        page.locator('[data-testid="camera-preview"]')
      ).toBeVisible({ timeout: 5000 })

      // Should show capture button
      await expect(
        page.locator('[data-testid="capture-button"]')
      ).toBeVisible()
    })

    test('can capture photo', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Open camera
      await page.click('[data-testid="open-camera"]')
      await page.waitForSelector('[data-testid="camera-preview"]')

      // Capture
      await page.click('[data-testid="capture-button"]')

      // Should show captured image preview
      await expect(
        page.locator('[data-testid="captured-preview"]')
      ).toBeVisible()

      // Should have retake and use buttons
      await expect(page.locator('[data-testid="retake-button"]')).toBeVisible()
      await expect(page.locator('[data-testid="use-photo-button"]')).toBeVisible()
    })

    test('can retake photo', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Capture first photo
      await page.click('[data-testid="open-camera"]')
      await page.waitForSelector('[data-testid="camera-preview"]')
      await page.click('[data-testid="capture-button"]')
      await page.waitForSelector('[data-testid="captured-preview"]')

      // Retake
      await page.click('[data-testid="retake-button"]')

      // Should go back to camera preview
      await expect(
        page.locator('[data-testid="camera-preview"]')
      ).toBeVisible()
    })

    test('can use captured photo', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Capture photo
      await page.click('[data-testid="open-camera"]')
      await page.waitForSelector('[data-testid="camera-preview"]')
      await page.click('[data-testid="capture-button"]')
      await page.waitForSelector('[data-testid="captured-preview"]')

      // Use photo
      await page.click('[data-testid="use-photo-button"]')

      // Should close camera and show in evidence list
      await expect(
        page.locator('[data-testid="camera-preview"]')
      ).not.toBeVisible()
      await expect(
        page.locator('[data-testid="evidence-item-photo"]')
      ).toBeVisible()
    })

    test('handles camera permission denied', async ({ page, context }) => {
      // Revoke camera permission
      await context.clearPermissions()

      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Try to open camera
      await page.click('[data-testid="open-camera"]')

      // Should show permission error
      await expect(
        page.locator('[data-testid="camera-permission-error"]')
      ).toBeVisible()
    })

    test('can switch between front and back camera', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      await page.click('[data-testid="open-camera"]')
      await page.waitForSelector('[data-testid="camera-preview"]')

      // Check switch camera button exists
      const switchButton = page.locator('[data-testid="switch-camera"]')

      if (await switchButton.isVisible()) {
        await switchButton.click()
        // Camera should still work after switch
        await expect(
          page.locator('[data-testid="camera-preview"]')
        ).toBeVisible()
      }
    })
  })

  test.describe('Location Capture', () => {
    test('can capture location', async ({ page }) => {
      const task = mockTasks.find((t) => t.location !== null)!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Click get location button
      await page.click('[data-testid="get-location"]')

      // Should show loading
      await expect(
        page.locator('[data-testid="location-loading"]')
      ).toBeVisible()

      // Should show captured location
      await expect(
        page.locator('[data-testid="location-captured"]')
      ).toBeVisible({ timeout: 5000 })

      // Should show coordinates
      await expect(page.locator('[data-testid="latitude"]')).toContainText(
        '-12.04'
      )
      await expect(page.locator('[data-testid="longitude"]')).toContainText(
        '-77.04'
      )
    })

    test('shows location on map', async ({ page }) => {
      const task = mockTasks.find((t) => t.location !== null)!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      await page.click('[data-testid="get-location"]')
      await page.waitForSelector('[data-testid="location-captured"]')

      // Map should be visible with marker
      await expect(
        page.locator('[data-testid="location-map"]')
      ).toBeVisible()
    })

    test('validates location is within task radius', async ({ page }) => {
      // Set location outside task radius
      await mockGeolocation(page, {
        latitude: -12.1, // Different location
        longitude: -77.1,
      })

      const task = mockTasks.find(
        (t) => t.location !== null && t.location_radius_km !== null
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      await page.click('[data-testid="get-location"]')
      await page.waitForSelector('[data-testid="location-captured"]')

      // Should show warning about distance
      await expect(
        page.locator('[data-testid="location-warning"]')
      ).toBeVisible()
      await expect(
        page.locator('[data-testid="location-warning"]')
      ).toContainText(/fuera|outside|distance/i)
    })

    test('handles geolocation permission denied', async ({ page, context }) => {
      // Clear permissions
      await context.clearPermissions()

      const task = mockTasks.find((t) => t.location !== null)!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      await page.click('[data-testid="get-location"]')

      // Should show permission error
      await expect(
        page.locator('[data-testid="location-permission-error"]')
      ).toBeVisible()
    })

    test('can retry location capture', async ({ page }) => {
      const task = mockTasks.find((t) => t.location !== null)!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      await page.click('[data-testid="get-location"]')
      await page.waitForSelector('[data-testid="location-captured"]')

      // Click retry
      await page.click('[data-testid="retry-location"]')

      // Should show loading again
      await expect(
        page.locator('[data-testid="location-loading"]')
      ).toBeVisible()
    })
  })

  test.describe('File Upload', () => {
    test('can upload image file', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Upload via file input
      const fileInput = page.locator('input[type="file"][accept*="image"]')

      await fileInput.setInputFiles({
        name: 'test-photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake image content'),
      })

      // Should show uploaded file
      await expect(
        page.locator('[data-testid="evidence-item-photo"]')
      ).toBeVisible()
    })

    test('can upload multiple files', async ({ page }) => {
      const task = mockTasks.find(
        (t) => t.evidence_schema.required.length > 1
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Upload multiple files
      const fileInput = page.locator('input[type="file"]').first()

      await fileInput.setInputFiles([
        {
          name: 'photo1.jpg',
          mimeType: 'image/jpeg',
          buffer: Buffer.from('fake image 1'),
        },
        {
          name: 'photo2.jpg',
          mimeType: 'image/jpeg',
          buffer: Buffer.from('fake image 2'),
        },
      ])

      // Should show both files
      const evidenceItems = page.locator('[data-testid^="evidence-item-"]')
      expect(await evidenceItems.count()).toBeGreaterThanOrEqual(2)
    })

    test('validates file type', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Try to upload wrong file type
      const fileInput = page.locator('input[type="file"]').first()

      await fileInput.setInputFiles({
        name: 'document.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('fake pdf content'),
      })

      // Should show error
      await expect(
        page.locator('[data-testid="file-type-error"]')
      ).toBeVisible()
    })

    test('validates file size', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Create a large buffer (simulating large file)
      // Note: In real test, this would be an actual large file
      const largeBuffer = Buffer.alloc(20 * 1024 * 1024) // 20MB

      const fileInput = page.locator('input[type="file"]').first()

      await fileInput.setInputFiles({
        name: 'large-photo.jpg',
        mimeType: 'image/jpeg',
        buffer: largeBuffer,
      })

      // Should show size error
      await expect(
        page.locator('[data-testid="file-size-error"]')
      ).toBeVisible()
    })

    test('can remove uploaded file', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Upload file
      const fileInput = page.locator('input[type="file"]').first()
      await fileInput.setInputFiles({
        name: 'test-photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake image'),
      })

      await expect(
        page.locator('[data-testid="evidence-item-photo"]')
      ).toBeVisible()

      // Remove file
      await page.click('[data-testid="remove-evidence-photo"]')

      // Should be removed
      await expect(
        page.locator('[data-testid="evidence-item-photo"]')
      ).not.toBeVisible()
    })
  })

  test.describe('Evidence Submission', () => {
    test('can submit evidence', async ({ page }) => {
      const task = mockTasks.find(
        (t) =>
          t.evidence_schema.required.includes('photo') && t.location !== null
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Add photo evidence
      const fileInput = page.locator('input[type="file"]').first()
      await fileInput.setInputFiles({
        name: 'evidence-photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake evidence image'),
      })

      // Capture location
      await page.click('[data-testid="get-location"]')
      await page.waitForSelector('[data-testid="location-captured"]')

      // Submit
      await page.click('[data-testid="submit-evidence"]')

      // Should show confirmation
      await expect(
        page.locator('[data-testid="confirm-submission"]')
      ).toBeVisible()

      // Confirm
      await page.click('[data-testid="confirm-submit"]')

      // Should show success
      await expect(
        page.locator('[data-testid="submission-success"]')
      ).toBeVisible({ timeout: 10000 })
    })

    test('validates all required evidence before submission', async ({
      page,
    }) => {
      const task = mockTasks.find(
        (t) => t.evidence_schema.required.length > 1
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Add only one evidence type
      const fileInput = page.locator('input[type="file"]').first()
      await fileInput.setInputFiles({
        name: 'photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake image'),
      })

      // Try to submit
      await page.click('[data-testid="submit-evidence"]')

      // Should show error about missing evidence
      await expect(
        page.locator('[data-testid="missing-evidence-error"]')
      ).toBeVisible()

      // Submit button should be disabled
      await expect(
        page.locator('[data-testid="submit-evidence"]')
      ).toBeDisabled()
    })

    test('shows progress during submission', async ({ page }) => {
      // Add delay to submission endpoint
      await page.route('**/rest/v1/submissions*', async (route) => {
        if (route.request().method() === 'POST') {
          await new Promise((r) => setTimeout(r, 2000))
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'sub-new',
              task_id: 'task-001',
              executor_id: 'exec-001',
              submitted_at: new Date().toISOString(),
            }),
          })
        } else {
          await route.continue()
        }
      })

      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Add evidence
      const fileInput = page.locator('input[type="file"]').first()
      await fileInput.setInputFiles({
        name: 'photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake image'),
      })

      // Submit
      await page.click('[data-testid="submit-evidence"]')
      await page.click('[data-testid="confirm-submit"]')

      // Should show progress
      await expect(
        page.locator('[data-testid="submission-progress"]')
      ).toBeVisible()
    })

    test('shows submission hash after success', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Add evidence
      const fileInput = page.locator('input[type="file"]').first()
      await fileInput.setInputFiles({
        name: 'photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake image'),
      })

      // Submit
      await page.click('[data-testid="submit-evidence"]')
      await page.click('[data-testid="confirm-submit"]')

      // Wait for success
      await page.waitForSelector('[data-testid="submission-success"]')

      // Should show submission ID/hash
      await expect(
        page.locator('[data-testid="submission-id"]')
      ).toBeVisible()
    })

    test('handles submission error', async ({ page }) => {
      // Override mock to fail
      await page.route('**/rest/v1/submissions*', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 500,
            body: JSON.stringify({ error: 'Upload failed' }),
          })
        } else {
          await route.continue()
        }
      })

      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Add evidence
      const fileInput = page.locator('input[type="file"]').first()
      await fileInput.setInputFiles({
        name: 'photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake image'),
      })

      // Submit
      await page.click('[data-testid="submit-evidence"]')
      await page.click('[data-testid="confirm-submit"]')

      // Should show error
      await expect(
        page.locator('[data-testid="submission-error"]')
      ).toBeVisible()

      // Should allow retry
      await expect(
        page.locator('[data-testid="retry-submission"]')
      ).toBeVisible()
    })

    test('saves draft evidence locally', async ({ page }) => {
      const task = mockTasks.find((t) =>
        t.evidence_schema.required.includes('photo')
      )!

      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Add evidence
      const fileInput = page.locator('input[type="file"]').first()
      await fileInput.setInputFiles({
        name: 'photo.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake image'),
      })

      // Navigate away without submitting
      await page.goto('/tasks')

      // Come back
      await page.goto(`/tasks/${task.id}/submit`)
      await page.waitForSelector('[data-testid="evidence-form"]')

      // Should prompt to restore draft
      const restorePrompt = page.locator('[data-testid="restore-draft"]')
      if (await restorePrompt.isVisible()) {
        await restorePrompt.click()
        // Evidence should be restored
        await expect(
          page.locator('[data-testid="evidence-item-photo"]')
        ).toBeVisible()
      }
    })
  })
})
