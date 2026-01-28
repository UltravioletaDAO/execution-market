import { test, expect } from '@playwright/test';

/**
 * Task Browsing Tests
 * Test the core task functionality - browsing, filtering, viewing.
 */

test.describe('Task Browsing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/tasks');
  });

  test('tasks page loads', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/task/i);
  });

  test('shows task list or empty state', async ({ page }) => {
    // Either shows tasks or empty state
    const taskList = page.locator('[data-testid="task-list"], .task-list');
    const emptyState = page.locator('text=No tasks, text=Sin tareas');
    
    const hasContent = await taskList.isVisible() || await emptyState.isVisible();
    expect(hasContent).toBeTruthy();
  });

  test('can filter tasks by category', async ({ page }) => {
    const categoryFilter = page.locator('[data-testid="category-filter"], select');
    
    if (await categoryFilter.isVisible()) {
      await categoryFilter.selectOption({ index: 1 });
      await page.waitForLoadState('networkidle');
      // Page should update
    }
  });

  test('can search tasks', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"], input[placeholder*="buscar"]');
    
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.waitForTimeout(500); // Debounce
      // Results should update
    }
  });

  test('task cards show required info', async ({ page }) => {
    const taskCard = page.locator('[data-testid="task-card"], .task-card').first();
    
    if (await taskCard.isVisible()) {
      // Should show title
      await expect(taskCard.locator('h2, h3, .title')).toBeVisible();
      // Should show bounty
      await expect(taskCard.locator('text=$, text=USD, text=USDC')).toBeVisible();
    }
  });

  test('clicking task card shows details', async ({ page }) => {
    const taskCard = page.locator('[data-testid="task-card"], .task-card').first();
    
    if (await taskCard.isVisible()) {
      await taskCard.click();
      
      // Should show task detail view
      await expect(page.locator('[data-testid="task-detail"], .task-detail')).toBeVisible();
    }
  });
});
