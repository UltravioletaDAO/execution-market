/**
 * Chamba E2E Tests - Agent Dashboard
 *
 * Tests for AI agent flows:
 * - Agent dashboard
 * - Task creation
 * - Submission review
 * - Approval/rejection
 */

import { test, expect } from '@playwright/test'
import { setupMocks, mockTasks, mockSubmissions, mockApplications } from '../fixtures/mocks'
import { loginWithEmail, TEST_AGENT } from '../fixtures/auth'
import {
  createTaskViaUI,
  approveSubmission,
  rejectSubmission,
} from '../fixtures/tasks'

test.describe('Agent Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
    await loginWithEmail(page, TEST_AGENT)
  })

  test.describe('Dashboard Overview', () => {
    test('agent dashboard loads successfully', async ({ page }) => {
      await page.goto('/agent')

      // Wait for dashboard
      await page.waitForSelector('[data-testid="agent-dashboard"]', {
        timeout: 10000,
      })

      // Should show welcome message or overview
      await expect(page.locator('h1')).toBeVisible()
    })

    test('dashboard shows task statistics', async ({ page }) => {
      await page.goto('/agent')
      await page.waitForSelector('[data-testid="agent-dashboard"]')

      // Should show stats cards
      await expect(page.locator('[data-testid="stat-total-tasks"]')).toBeVisible()
      await expect(page.locator('[data-testid="stat-active-tasks"]')).toBeVisible()
      await expect(page.locator('[data-testid="stat-pending-submissions"]')).toBeVisible()
      await expect(page.locator('[data-testid="stat-completed-tasks"]')).toBeVisible()
    })

    test('dashboard shows recent activity', async ({ page }) => {
      await page.goto('/agent')
      await page.waitForSelector('[data-testid="agent-dashboard"]')

      // Should show recent activity section
      await expect(page.locator('[data-testid="recent-activity"]')).toBeVisible()
    })

    test('dashboard shows pending items requiring attention', async ({ page }) => {
      await page.goto('/agent')
      await page.waitForSelector('[data-testid="agent-dashboard"]')

      // Should show pending items
      await expect(
        page.locator('[data-testid="pending-attention"]')
      ).toBeVisible()
    })
  })

  test.describe('Task Creation', () => {
    test('can create a new task', async ({ page }) => {
      await page.goto('/agent/tasks/new')

      // Wait for form
      await page.waitForSelector('[data-testid="create-task-form"]', {
        timeout: 10000,
      })

      // Fill form
      await page.click('[data-testid="category-physical_presence"]')
      await page.fill(
        '[data-testid="task-title"]',
        'Verificar tienda en centro comercial'
      )
      await page.fill(
        '[data-testid="task-instructions"]',
        'Ir a la direccion indicada y tomar fotos del frente y interior de la tienda.'
      )
      await page.fill('[data-testid="task-bounty"]', '10')

      // Set deadline (tomorrow)
      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0]
      await page.fill('[data-testid="task-deadline"]', tomorrow)

      // Set location hint
      await page.fill(
        '[data-testid="task-location-hint"]',
        'Centro Comercial Lima'
      )

      // Select evidence types
      await page.click('[data-testid="evidence-photo_geo"]')
      await page.click('[data-testid="evidence-photo"]')

      // Submit
      await page.click('[data-testid="create-task-submit"]')

      // Should redirect to task list or detail
      await expect(page).toHaveURL(/\/agent\/tasks/)

      // Should show success message
      await expect(
        page.locator('[data-testid="task-created-success"]')
      ).toBeVisible()
    })

    test('validates required fields', async ({ page }) => {
      await page.goto('/agent/tasks/new')
      await page.waitForSelector('[data-testid="create-task-form"]')

      // Try to submit empty form
      await page.click('[data-testid="create-task-submit"]')

      // Should show validation errors
      await expect(
        page.locator('[data-testid="error-title"]')
      ).toBeVisible()
      await expect(
        page.locator('[data-testid="error-instructions"]')
      ).toBeVisible()
      await expect(
        page.locator('[data-testid="error-bounty"]')
      ).toBeVisible()
    })

    test('validates bounty is positive number', async ({ page }) => {
      await page.goto('/agent/tasks/new')
      await page.waitForSelector('[data-testid="create-task-form"]')

      // Enter negative bounty
      await page.fill('[data-testid="task-bounty"]', '-5')
      await page.click('[data-testid="create-task-submit"]')

      // Should show error
      await expect(
        page.locator('[data-testid="error-bounty"]')
      ).toContainText(/positive|mayor que 0/i)
    })

    test('validates deadline is in future', async ({ page }) => {
      await page.goto('/agent/tasks/new')
      await page.waitForSelector('[data-testid="create-task-form"]')

      // Enter past date
      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0]
      await page.fill('[data-testid="task-deadline"]', yesterday)
      await page.click('[data-testid="create-task-submit"]')

      // Should show error
      await expect(
        page.locator('[data-testid="error-deadline"]')
      ).toContainText(/future|futuro/i)
    })

    test('shows preview before publishing', async ({ page }) => {
      await page.goto('/agent/tasks/new')
      await page.waitForSelector('[data-testid="create-task-form"]')

      // Fill minimal form
      await page.click('[data-testid="category-simple_action"]')
      await page.fill('[data-testid="task-title"]', 'Test Task')
      await page.fill('[data-testid="task-instructions"]', 'Test instructions')
      await page.fill('[data-testid="task-bounty"]', '5')

      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0]
      await page.fill('[data-testid="task-deadline"]', tomorrow)

      // Click preview
      await page.click('[data-testid="preview-task"]')

      // Should show preview
      await expect(
        page.locator('[data-testid="task-preview"]')
      ).toBeVisible()
      await expect(
        page.locator('[data-testid="task-preview"]')
      ).toContainText('Test Task')
    })

    test('can save task as draft', async ({ page }) => {
      await page.goto('/agent/tasks/new')
      await page.waitForSelector('[data-testid="create-task-form"]')

      // Fill partial form
      await page.click('[data-testid="category-physical_presence"]')
      await page.fill('[data-testid="task-title"]', 'Draft Task')

      // Save as draft
      await page.click('[data-testid="save-draft"]')

      // Should show success
      await expect(
        page.locator('[data-testid="draft-saved"]')
      ).toBeVisible()

      // Navigate away and back
      await page.goto('/agent')
      await page.goto('/agent/tasks/new')

      // Draft should be restored (optional - depends on implementation)
      // await expect(page.locator('[data-testid="task-title"]')).toHaveValue('Draft Task')
    })
  })

  test.describe('Submission Review', () => {
    test('can view submissions list', async ({ page }) => {
      await page.goto('/agent/submissions')

      // Wait for list
      await page.waitForSelector('[data-testid="submissions-list"]', {
        timeout: 10000,
      })

      // Should show submissions
      const submissions = page.locator('[data-testid^="submission-"]')
      await expect(submissions.first()).toBeVisible()
    })

    test('can view submission detail', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)

      // Wait for detail
      await page.waitForSelector('[data-testid="submission-detail"]', {
        timeout: 10000,
      })

      // Should show submission info
      await expect(
        page.locator('[data-testid="submission-evidence"]')
      ).toBeVisible()
      await expect(
        page.locator('[data-testid="submission-timestamp"]')
      ).toBeVisible()
    })

    test('can view evidence files in submission', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      // Should show evidence files
      const evidenceFiles = page.locator('[data-testid="evidence-file"]')
      const count = await evidenceFiles.count()

      expect(count).toBeGreaterThan(0)

      // Can click to view image
      await evidenceFiles.first().click()
      await expect(page.locator('[data-testid="image-viewer"]')).toBeVisible()
    })

    test('shows submission location on map', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      // Should show map with location
      await expect(
        page.locator('[data-testid="submission-map"]')
      ).toBeVisible()
    })
  })

  test.describe('Approve Submission', () => {
    test('can approve submission', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      // Click approve
      await page.click('[data-testid="approve-submission"]')

      // Confirmation dialog
      await expect(
        page.locator('[data-testid="confirm-dialog"]')
      ).toBeVisible()

      // Add notes (optional)
      await page.fill(
        '[data-testid="approval-notes"]',
        'Evidence verified, looks good'
      )

      // Confirm
      await page.click('[data-testid="confirm-approval"]')

      // Should show success
      await expect(
        page.locator('[data-testid="submission-approved"]')
      ).toBeVisible()
    })

    test('approval triggers payment', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      await page.click('[data-testid="approve-submission"]')
      await page.click('[data-testid="confirm-approval"]')

      // Should show payment processing
      await expect(
        page.locator('[data-testid="payment-processing"]')
      ).toBeVisible()

      // Should show payment complete
      await expect(
        page.locator('[data-testid="payment-complete"]')
      ).toBeVisible({ timeout: 10000 })
    })

    test('shows error if approval fails', async ({ page }) => {
      // Override mock to fail
      await page.route('**/rest/v1/submissions*', async (route) => {
        if (route.request().method() === 'PATCH') {
          await route.fulfill({
            status: 500,
            body: JSON.stringify({ error: 'Payment failed' }),
          })
        } else {
          await route.continue()
        }
      })

      const submission = mockSubmissions[0]
      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      await page.click('[data-testid="approve-submission"]')
      await page.click('[data-testid="confirm-approval"]')

      // Should show error
      await expect(
        page.locator('[data-testid="approval-error"]')
      ).toBeVisible()
    })
  })

  test.describe('Reject Submission', () => {
    test('can reject submission', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      // Click reject
      await page.click('[data-testid="reject-submission"]')

      // Rejection dialog
      await expect(
        page.locator('[data-testid="rejection-dialog"]')
      ).toBeVisible()

      // Must provide reason
      await page.fill(
        '[data-testid="rejection-reason"]',
        'Evidence does not match task requirements - location is incorrect'
      )

      // Confirm
      await page.click('[data-testid="confirm-rejection"]')

      // Should show success
      await expect(
        page.locator('[data-testid="submission-rejected"]')
      ).toBeVisible()
    })

    test('requires reason for rejection', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      await page.click('[data-testid="reject-submission"]')

      // Try to confirm without reason
      await page.click('[data-testid="confirm-rejection"]')

      // Should show error
      await expect(
        page.locator('[data-testid="error-reason-required"]')
      ).toBeVisible()

      // Confirm button should be disabled when reason is empty
      await expect(
        page.locator('[data-testid="confirm-rejection"]')
      ).toBeDisabled()
    })

    test('rejection notifies executor', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      await page.click('[data-testid="reject-submission"]')
      await page.fill(
        '[data-testid="rejection-reason"]',
        'Evidence quality is insufficient'
      )
      await page.click('[data-testid="confirm-rejection"]')

      // Should show notification sent confirmation
      await expect(
        page.locator('[data-testid="notification-sent"]')
      ).toBeVisible()
    })

    test('allows executor to dispute rejection', async ({ page }) => {
      const submission = mockSubmissions[0]

      await page.goto(`/agent/submissions/${submission.id}`)
      await page.waitForSelector('[data-testid="submission-detail"]')

      await page.click('[data-testid="reject-submission"]')
      await page.fill('[data-testid="rejection-reason"]', 'Incorrect location')
      await page.click('[data-testid="confirm-rejection"]')

      // After rejection, dispute option should be mentioned
      await expect(page.locator('text=dispute')).toBeVisible()
    })
  })

  test.describe('Task Management', () => {
    test('can view list of created tasks', async ({ page }) => {
      await page.goto('/agent/tasks')

      // Wait for list
      await page.waitForSelector('[data-testid="agent-tasks-list"]', {
        timeout: 10000,
      })

      // Should show tasks
      const tasks = page.locator('[data-testid^="agent-task-"]')
      await expect(tasks.first()).toBeVisible()
    })

    test('can cancel a task', async ({ page }) => {
      const task = mockTasks[0]

      await page.goto(`/agent/tasks/${task.id}`)
      await page.waitForSelector('[data-testid="agent-task-detail"]')

      // Click more options
      await page.click('[data-testid="task-options"]')

      // Click cancel
      await page.click('[data-testid="cancel-task"]')

      // Confirm
      await page.click('[data-testid="confirm-cancel"]')

      // Should show cancelled
      await expect(
        page.locator('[data-testid="task-cancelled"]')
      ).toBeVisible()
    })

    test('can extend task deadline', async ({ page }) => {
      const task = mockTasks[0]

      await page.goto(`/agent/tasks/${task.id}`)
      await page.waitForSelector('[data-testid="agent-task-detail"]')

      await page.click('[data-testid="task-options"]')
      await page.click('[data-testid="extend-deadline"]')

      // New deadline picker
      const newDeadline = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0]
      await page.fill('[data-testid="new-deadline"]', newDeadline)
      await page.click('[data-testid="confirm-extend"]')

      // Should show success
      await expect(
        page.locator('[data-testid="deadline-extended"]')
      ).toBeVisible()
    })
  })
})
