/**
 * Execution Market E2E Tests - Tasks
 *
 * Tests for task browsing and executor flows:
 * - Task list loading
 * - Task filtering
 * - Task detail view
 * - Task application
 * - Application status
 */

import { test, expect } from '@playwright/test'
import { setupMocks, mockTasks } from '../fixtures/mocks'
import { loginWithEmail, TEST_EXECUTOR } from '../fixtures/auth'
import {
  filterByCategory,
  filterByStatus,
  searchTasks,
  applyToTask,
  assertTaskCardVisible,
  assertTaskCount,
} from '../fixtures/tasks'

test.describe('Tasks - Executor View', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
    await loginWithEmail(page, TEST_EXECUTOR)
  })

  test.describe('Task List', () => {
    test('task list loads successfully', async ({ page }) => {
      await page.goto('/tasks')

      // Wait for task list to load
      await page.waitForSelector('[data-testid="task-list"]', { timeout: 10000 })

      // Should show loading skeleton first, then tasks
      const taskCards = page.locator('[data-testid^="task-card-"]')
      await expect(taskCards.first()).toBeVisible({ timeout: 10000 })

      // Should have multiple tasks
      const count = await taskCards.count()
      expect(count).toBeGreaterThan(0)
    })

    test('displays task cards with correct information', async ({ page }) => {
      await page.goto('/tasks')

      // Wait for first task
      const firstTask = mockTasks[0]
      await assertTaskCardVisible(page, firstTask)

      // Check card has required elements
      const card = page.locator(`[data-testid="task-card-${firstTask.id}"]`)

      // Title
      await expect(card.locator('h3')).toContainText(firstTask.title)

      // Category badge
      await expect(card.locator('[data-testid="category-badge"]')).toBeVisible()

      // Bounty
      await expect(card.locator('[data-testid="bounty-amount"]')).toContainText(
        `$${firstTask.bounty_usd}`
      )

      // Deadline
      await expect(card.locator('[data-testid="deadline"]')).toBeVisible()

      // Location hint (if present)
      if (firstTask.location_hint) {
        await expect(
          card.locator('[data-testid="location-hint"]')
        ).toContainText(firstTask.location_hint)
      }
    })

    test('shows empty state when no tasks', async ({ page }) => {
      // Override mock to return empty array
      await page.route('**/rest/v1/tasks*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        })
      })

      await page.goto('/tasks')

      // Should show empty state
      await expect(page.locator('[data-testid="empty-state"]')).toBeVisible()
      await expect(page.locator('text=No hay tareas')).toBeVisible()
    })

    test('shows error state on API failure', async ({ page }) => {
      // Override mock to return error
      await page.route('**/rest/v1/tasks*', async (route) => {
        await route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Internal Server Error' }),
        })
      })

      await page.goto('/tasks')

      // Should show error state
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible()
      await expect(page.locator('text=Error')).toBeVisible()
    })

    test('shows loading skeleton while fetching', async ({ page }) => {
      // Add delay to mock
      await page.route('**/rest/v1/tasks*', async (route) => {
        await new Promise((r) => setTimeout(r, 1000))
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockTasks),
        })
      })

      await page.goto('/tasks')

      // Should show loading skeleton
      await expect(
        page.locator('[data-testid="loading-skeleton"]')
      ).toBeVisible()

      // Eventually shows tasks
      await expect(
        page.locator('[data-testid^="task-card-"]').first()
      ).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Task Filtering', () => {
    test('can filter tasks by category', async ({ page }) => {
      await page.goto('/tasks')
      await page.waitForSelector('[data-testid="task-list"]')

      // Filter by physical_presence
      await filterByCategory(page, 'physical_presence')

      // Should only show physical presence tasks
      const cards = page.locator('[data-testid^="task-card-"]')
      const count = await cards.count()

      for (let i = 0; i < count; i++) {
        const card = cards.nth(i)
        await expect(card.locator('[data-testid="category-badge"]')).toContainText(
          /Presencia|physical/i
        )
      }
    })

    test('can filter tasks by multiple categories', async ({ page }) => {
      await page.goto('/tasks')
      await page.waitForSelector('[data-testid="task-list"]')

      // Select physical_presence
      await page.click('[data-testid="filter-physical_presence"]')

      // Select knowledge_access (multi-select)
      await page.click('[data-testid="filter-knowledge_access"]')

      // Should show tasks from both categories
      const physicalCards = page.locator('[data-testid*="physical_presence"]')
      const knowledgeCards = page.locator('[data-testid*="knowledge_access"]')

      expect(
        (await physicalCards.count()) + (await knowledgeCards.count())
      ).toBeGreaterThan(0)
    })

    test('can clear all filters', async ({ page }) => {
      await page.goto('/tasks')
      await page.waitForSelector('[data-testid="task-list"]')

      // Apply filter
      await filterByCategory(page, 'physical_presence')

      // Clear filters
      await filterByCategory(page, null) // null = all

      // Should show all tasks again
      await assertTaskCount(page, mockTasks.length)
    })

    test('filter persists in URL', async ({ page }) => {
      await page.goto('/tasks')
      await page.waitForSelector('[data-testid="task-list"]')

      // Apply filter
      await filterByCategory(page, 'physical_presence')

      // URL should update
      await expect(page).toHaveURL(/category=physical_presence/)

      // Reload page
      await page.reload()

      // Filter should still be applied
      const categoryFilter = page.locator(
        '[data-testid="filter-physical_presence"]'
      )
      await expect(categoryFilter).toHaveAttribute('aria-selected', 'true')
    })
  })

  test.describe('Task Detail', () => {
    test('can view task detail', async ({ page }) => {
      const task = mockTasks[0]

      await page.goto('/tasks')
      await page.waitForSelector('[data-testid="task-list"]')

      // Click on task card
      await page.click(`[data-testid="task-card-${task.id}"]`)

      // Should navigate to detail page
      await expect(page).toHaveURL(new RegExp(`/tasks/${task.id}`))

      // Should show task details
      await expect(page.locator('[data-testid="task-detail"]')).toBeVisible()
      await expect(page.locator('h1')).toContainText(task.title)
    })

    test('task detail shows full instructions', async ({ page }) => {
      const task = mockTasks[0]

      await page.goto(`/tasks/${task.id}`)

      // Wait for detail to load
      await page.waitForSelector('[data-testid="task-detail"]')

      // Should show full instructions
      await expect(
        page.locator('[data-testid="task-instructions"]')
      ).toContainText(task.instructions)
    })

    test('task detail shows evidence requirements', async ({ page }) => {
      const task = mockTasks[0]

      await page.goto(`/tasks/${task.id}`)
      await page.waitForSelector('[data-testid="task-detail"]')

      // Should show required evidence
      const evidenceSection = page.locator(
        '[data-testid="evidence-requirements"]'
      )
      await expect(evidenceSection).toBeVisible()

      for (const evidenceType of task.evidence_schema.required) {
        await expect(evidenceSection).toContainText(new RegExp(evidenceType, 'i'))
      }
    })

    test('task detail shows location info when available', async ({ page }) => {
      const task = mockTasks.find((t) => t.location !== null)!

      await page.goto(`/tasks/${task.id}`)
      await page.waitForSelector('[data-testid="task-detail"]')

      // Should show location section
      await expect(
        page.locator('[data-testid="task-location"]')
      ).toBeVisible()

      // Should show location hint
      if (task.location_hint) {
        await expect(page.locator('[data-testid="location-hint"]')).toContainText(
          task.location_hint
        )
      }
    })

    test('task detail shows reputation requirement', async ({ page }) => {
      const task = mockTasks.find((t) => t.min_reputation > 0)!

      await page.goto(`/tasks/${task.id}`)
      await page.waitForSelector('[data-testid="task-detail"]')

      // Should show reputation requirement
      await expect(
        page.locator('[data-testid="reputation-requirement"]')
      ).toContainText(`${task.min_reputation}`)
    })

    test('can navigate back to list from detail', async ({ page }) => {
      await page.goto('/tasks/task-001')
      await page.waitForSelector('[data-testid="task-detail"]')

      // Click back button
      await page.click('[data-testid="back-button"]')

      // Should be back on list
      await expect(page).toHaveURL(/\/tasks$/)
    })
  })

  test.describe('Task Application', () => {
    test('can apply to task', async ({ page }) => {
      const task = mockTasks[0]

      await page.goto(`/tasks/${task.id}`)
      await page.waitForSelector('[data-testid="task-detail"]')

      // Click apply button
      await page.click('[data-testid="apply-button"]')

      // Application modal should appear
      await expect(
        page.locator('[data-testid="application-modal"]')
      ).toBeVisible()

      // Fill optional message
      await page.fill(
        '[data-testid="application-message"]',
        'I am interested in this task'
      )

      // Submit
      await page.click('[data-testid="submit-application"]')

      // Should show success
      await expect(
        page.locator('[data-testid="application-submitted"]')
      ).toBeVisible()
    })

    test('apply button shows loading state', async ({ page }) => {
      // Add delay to application endpoint
      await page.route('**/rest/v1/task_applications*', async (route) => {
        await new Promise((r) => setTimeout(r, 1000))
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'app-new',
            task_id: 'task-001',
            executor_id: 'exec-001',
            status: 'pending',
          }),
        })
      })

      const task = mockTasks[0]
      await page.goto(`/tasks/${task.id}`)

      await page.click('[data-testid="apply-button"]')
      await page.click('[data-testid="submit-application"]')

      // Button should show loading
      await expect(
        page.locator('[data-testid="submit-application"]')
      ).toBeDisabled()
      await expect(
        page.locator('[data-testid="submit-application"] .loading')
      ).toBeVisible()
    })

    test('cannot apply to task with insufficient reputation', async ({
      page,
    }) => {
      const highRepTask = mockTasks.find((t) => t.min_reputation > 100)

      if (!highRepTask) {
        test.skip()
        return
      }

      await page.goto(`/tasks/${highRepTask.id}`)
      await page.waitForSelector('[data-testid="task-detail"]')

      // Apply button should be disabled or show warning
      const applyButton = page.locator('[data-testid="apply-button"]')

      const isDisabled = await applyButton.isDisabled()
      if (isDisabled) {
        expect(isDisabled).toBe(true)
      } else {
        // Should show reputation warning when clicked
        await applyButton.click()
        await expect(
          page.locator('[data-testid="reputation-warning"]')
        ).toBeVisible()
      }
    })
  })

  test.describe('Application Status', () => {
    test('shows applied status on task card', async ({ page }) => {
      // Mock that user has applied to task-002
      await page.route('**/rest/v1/task_applications*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'app-001',
              task_id: 'task-002',
              executor_id: 'exec-001',
              status: 'pending',
              created_at: new Date().toISOString(),
            },
          ]),
        })
      })

      await page.goto('/tasks')
      await page.waitForSelector('[data-testid="task-list"]')

      // Task-002 card should show applied badge
      const appliedCard = page.locator('[data-testid="task-card-task-002"]')
      await expect(
        appliedCard.locator('[data-testid="applied-badge"]')
      ).toBeVisible()
    })

    test('shows pending status in task detail', async ({ page }) => {
      // Mock pending application
      await page.route('**/rest/v1/task_applications*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'app-001',
              task_id: 'task-001',
              executor_id: 'exec-001',
              status: 'pending',
              created_at: new Date().toISOString(),
            },
          ]),
        })
      })

      await page.goto('/tasks/task-001')
      await page.waitForSelector('[data-testid="task-detail"]')

      // Should show application status instead of apply button
      await expect(
        page.locator('[data-testid="application-status"]')
      ).toBeVisible()
      await expect(
        page.locator('[data-testid="application-status"]')
      ).toContainText(/Pending|Pendiente/i)
    })

    test('shows accepted status with next steps', async ({ page }) => {
      // Mock accepted application
      await page.route('**/rest/v1/task_applications*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'app-001',
              task_id: 'task-001',
              executor_id: 'exec-001',
              status: 'accepted',
              created_at: new Date().toISOString(),
            },
          ]),
        })
      })

      await page.goto('/tasks/task-001')
      await page.waitForSelector('[data-testid="task-detail"]')

      // Should show accepted status
      await expect(
        page.locator('[data-testid="application-status"]')
      ).toContainText(/Accepted|Aceptada/i)

      // Should show start task button
      await expect(
        page.locator('[data-testid="start-task-button"]')
      ).toBeVisible()
    })

    test('shows rejected status with message', async ({ page }) => {
      // Mock rejected application
      await page.route('**/rest/v1/task_applications*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'app-001',
              task_id: 'task-001',
              executor_id: 'exec-001',
              status: 'rejected',
              rejection_reason: 'Not enough experience',
              created_at: new Date().toISOString(),
            },
          ]),
        })
      })

      await page.goto('/tasks/task-001')
      await page.waitForSelector('[data-testid="task-detail"]')

      // Should show rejected status
      await expect(
        page.locator('[data-testid="application-status"]')
      ).toContainText(/Rejected|Rechazada/i)

      // Should show reason
      await expect(
        page.locator('[data-testid="rejection-reason"]')
      ).toContainText('Not enough experience')
    })
  })
})
