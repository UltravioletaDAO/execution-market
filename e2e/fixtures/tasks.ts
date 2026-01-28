/**
 * Chamba E2E Task Fixtures
 *
 * Helpers for task creation and manipulation in E2E tests.
 */

import type { Page } from '@playwright/test'
import {
  mockTasks,
  type Task,
  type TaskCategory,
  type TaskStatus,
} from './mocks'

// ============================================================================
// Task Creation Helpers
// ============================================================================

export interface CreateTaskInput {
  category: TaskCategory
  title: string
  instructions: string
  bountyUsd: number
  deadline?: Date
  locationHint?: string
  location?: { lat: number; lng: number }
  locationRadiusKm?: number
  minReputation?: number
  requiredEvidence?: string[]
  maxExecutors?: number
}

/**
 * Create a new task via the UI
 */
export async function createTaskViaUI(
  page: Page,
  input: CreateTaskInput
): Promise<void> {
  // Navigate to task creation
  await page.goto('/agent/tasks/new')

  // Wait for form
  await page.waitForSelector('[data-testid="create-task-form"]', {
    timeout: 10000,
  })

  // Select category
  await page.click(`[data-testid="category-${input.category}"]`)

  // Fill title
  await page.fill('[data-testid="task-title"]', input.title)

  // Fill instructions
  await page.fill('[data-testid="task-instructions"]', input.instructions)

  // Fill bounty
  await page.fill('[data-testid="task-bounty"]', input.bountyUsd.toString())

  // Set deadline if provided
  if (input.deadline) {
    const dateStr = input.deadline.toISOString().split('T')[0]
    await page.fill('[data-testid="task-deadline"]', dateStr)
  }

  // Set location hint if provided
  if (input.locationHint) {
    await page.fill('[data-testid="task-location-hint"]', input.locationHint)
  }

  // Set min reputation if provided
  if (input.minReputation) {
    await page.fill(
      '[data-testid="task-min-reputation"]',
      input.minReputation.toString()
    )
  }

  // Select required evidence types
  if (input.requiredEvidence) {
    for (const evidenceType of input.requiredEvidence) {
      await page.click(`[data-testid="evidence-${evidenceType}"]`)
    }
  }

  // Set max executors if provided
  if (input.maxExecutors) {
    await page.fill(
      '[data-testid="task-max-executors"]',
      input.maxExecutors.toString()
    )
  }

  // Submit form
  await page.click('[data-testid="create-task-submit"]')

  // Wait for redirect to task detail or list
  await page.waitForURL(/\/agent\/tasks/, { timeout: 15000 })
}

/**
 * Get a task by ID from mock data
 */
export function getTaskById(id: string): Task | undefined {
  return mockTasks.find((t) => t.id === id)
}

/**
 * Get tasks by status from mock data
 */
export function getTasksByStatus(status: TaskStatus): Task[] {
  return mockTasks.filter((t) => t.status === status)
}

/**
 * Get tasks by category from mock data
 */
export function getTasksByCategory(category: TaskCategory): Task[] {
  return mockTasks.filter((t) => t.category === category)
}

// ============================================================================
// Task Interaction Helpers
// ============================================================================

/**
 * Apply to a task via the UI
 */
export async function applyToTask(
  page: Page,
  taskId: string,
  message?: string
): Promise<void> {
  // Navigate to task detail
  await page.goto(`/tasks/${taskId}`)

  // Wait for task detail to load
  await page.waitForSelector('[data-testid="task-detail"]', { timeout: 10000 })

  // Click apply button
  await page.click('[data-testid="apply-button"]')

  // Wait for application modal
  await page.waitForSelector('[data-testid="application-modal"]', {
    timeout: 5000,
  })

  // Fill message if provided
  if (message) {
    await page.fill('[data-testid="application-message"]', message)
  }

  // Submit application
  await page.click('[data-testid="submit-application"]')

  // Wait for confirmation
  await page.waitForSelector('[data-testid="application-submitted"]', {
    timeout: 10000,
  })
}

/**
 * Accept a task (for agents approving applications)
 */
export async function acceptTaskApplication(
  page: Page,
  taskId: string,
  applicationId: string
): Promise<void> {
  // Navigate to task management
  await page.goto(`/agent/tasks/${taskId}`)

  // Wait for applications list
  await page.waitForSelector('[data-testid="applications-list"]', {
    timeout: 10000,
  })

  // Find the application
  const application = page.locator(
    `[data-testid="application-${applicationId}"]`
  )
  await application.waitFor({ timeout: 5000 })

  // Click accept
  await application.locator('[data-testid="accept-application"]').click()

  // Wait for confirmation
  await page.waitForSelector('[data-testid="application-accepted"]', {
    timeout: 10000,
  })
}

/**
 * Reject a task application (for agents)
 */
export async function rejectTaskApplication(
  page: Page,
  taskId: string,
  applicationId: string,
  reason?: string
): Promise<void> {
  // Navigate to task management
  await page.goto(`/agent/tasks/${taskId}`)

  // Wait for applications list
  await page.waitForSelector('[data-testid="applications-list"]', {
    timeout: 10000,
  })

  // Find the application
  const application = page.locator(
    `[data-testid="application-${applicationId}"]`
  )
  await application.waitFor({ timeout: 5000 })

  // Click reject
  await application.locator('[data-testid="reject-application"]').click()

  // Fill reason if modal appears and reason provided
  if (reason) {
    const reasonInput = page.locator('[data-testid="rejection-reason"]')
    if (await reasonInput.isVisible()) {
      await reasonInput.fill(reason)
    }
  }

  // Confirm rejection
  await page.click('[data-testid="confirm-rejection"]')

  // Wait for confirmation
  await page.waitForSelector('[data-testid="application-rejected"]', {
    timeout: 10000,
  })
}

// ============================================================================
// Submission Helpers
// ============================================================================

/**
 * Approve a submission (for agents)
 */
export async function approveSubmission(
  page: Page,
  taskId: string,
  submissionId: string,
  notes?: string
): Promise<void> {
  // Navigate to submissions view
  await page.goto(`/agent/tasks/${taskId}/submissions`)

  // Wait for submissions list
  await page.waitForSelector('[data-testid="submissions-list"]', {
    timeout: 10000,
  })

  // Find the submission
  const submission = page.locator(
    `[data-testid="submission-${submissionId}"]`
  )
  await submission.waitFor({ timeout: 5000 })

  // Click approve
  await submission.locator('[data-testid="approve-submission"]').click()

  // Add notes if provided
  if (notes) {
    const notesInput = page.locator('[data-testid="approval-notes"]')
    if (await notesInput.isVisible()) {
      await notesInput.fill(notes)
    }
  }

  // Confirm approval
  await page.click('[data-testid="confirm-approval"]')

  // Wait for confirmation
  await page.waitForSelector('[data-testid="submission-approved"]', {
    timeout: 10000,
  })
}

/**
 * Reject a submission (for agents)
 */
export async function rejectSubmission(
  page: Page,
  taskId: string,
  submissionId: string,
  reason: string
): Promise<void> {
  // Navigate to submissions view
  await page.goto(`/agent/tasks/${taskId}/submissions`)

  // Wait for submissions list
  await page.waitForSelector('[data-testid="submissions-list"]', {
    timeout: 10000,
  })

  // Find the submission
  const submission = page.locator(
    `[data-testid="submission-${submissionId}"]`
  )
  await submission.waitFor({ timeout: 5000 })

  // Click reject
  await submission.locator('[data-testid="reject-submission"]').click()

  // Fill reason
  await page.fill('[data-testid="rejection-reason"]', reason)

  // Confirm rejection
  await page.click('[data-testid="confirm-rejection"]')

  // Wait for confirmation
  await page.waitForSelector('[data-testid="submission-rejected"]', {
    timeout: 10000,
  })
}

// ============================================================================
// Task Filtering Helpers
// ============================================================================

/**
 * Filter tasks by category
 */
export async function filterByCategory(
  page: Page,
  category: TaskCategory | null
): Promise<void> {
  if (category === null) {
    await page.click('[data-testid="filter-all"]')
  } else {
    await page.click(`[data-testid="filter-${category}"]`)
  }

  // Wait for filter to apply
  await page.waitForTimeout(500)
}

/**
 * Filter tasks by status
 */
export async function filterByStatus(
  page: Page,
  status: TaskStatus
): Promise<void> {
  await page.click('[data-testid="status-filter"]')
  await page.click(`[data-testid="status-${status}"]`)

  // Wait for filter to apply
  await page.waitForTimeout(500)
}

/**
 * Search tasks by keyword
 */
export async function searchTasks(page: Page, query: string): Promise<void> {
  await page.fill('[data-testid="task-search"]', query)

  // Trigger search (debounced, so wait)
  await page.waitForTimeout(500)
}

// ============================================================================
// Task Assertions
// ============================================================================

/**
 * Assert task card is visible with correct data
 */
export async function assertTaskCardVisible(
  page: Page,
  task: Task
): Promise<void> {
  const card = page.locator(`[data-testid="task-card-${task.id}"]`)
  await card.waitFor({ timeout: 5000 })

  // Check title
  await page.locator('h3').filter({ hasText: task.title }).isVisible()

  // Check bounty
  const bountyText = `$${task.bounty_usd.toFixed(2)}`
  await card.locator('text=' + bountyText).isVisible()
}

/**
 * Assert task list shows expected count
 */
export async function assertTaskCount(
  page: Page,
  expectedCount: number
): Promise<void> {
  const cards = page.locator('[data-testid^="task-card-"]')
  await cards.first().waitFor({ timeout: 10000 })

  const count = await cards.count()
  if (count !== expectedCount) {
    throw new Error(`Expected ${expectedCount} tasks, found ${count}`)
  }
}
