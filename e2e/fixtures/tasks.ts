/**
 * Execution Market E2E Task Fixtures
 *
 * Helpers for task interaction in E2E tests.
 * Uses role/text-based selectors instead of data-testid.
 */

import type { Page } from '@playwright/test'
import { mockTasks, type Task, type TaskCategory, type TaskStatus } from './mocks'

// ============================================================================
// Data Helpers
// ============================================================================

export function getTaskById(id: string): Task | undefined {
  return mockTasks.find((t) => t.id === id)
}

export function getTasksByStatus(status: TaskStatus): Task[] {
  return mockTasks.filter((t) => t.status === status)
}

export function getTasksByCategory(category: TaskCategory): Task[] {
  return mockTasks.filter((t) => t.category === category)
}

// ============================================================================
// UI Interaction Helpers
// ============================================================================

/**
 * Wait for task cards to appear on the page.
 * Uses text from mock task titles rather than data-testid.
 */
export async function waitForTasks(page: Page): Promise<void> {
  // Wait for at least one task title to appear
  await page.getByText(mockTasks[0].title).waitFor({ timeout: 10000 })
}

/**
 * Count visible task cards by looking for USDC bounty text pattern.
 */
export async function getVisibleTaskCount(page: Page): Promise<number> {
  // Each task card shows a bounty with $ sign - count those
  const bountyElements = page.locator('text=/\\$\\d+\\.\\d{2}/')
  return bountyElements.count()
}
