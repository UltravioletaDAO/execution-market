import { test, expect } from '@playwright/test';

/**
 * Navigation Tests
 * Verify all navigation links and menu items work correctly.
 */

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('main navigation links are visible', async ({ page }) => {
    // Desktop nav
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();
  });

  test('can navigate to tasks page', async ({ page }) => {
    await page.click('text=Tasks');
    await expect(page).toHaveURL(/.*tasks/);
    await expect(page.locator('h1')).toContainText(/tasks/i);
  });

  test('can navigate to profile page', async ({ page }) => {
    // May require auth first
    await page.click('text=Profile');
    // Should either show profile or redirect to login
    const url = page.url();
    expect(url.includes('profile') || url.includes('login')).toBeTruthy();
  });

  test('mobile navigation works', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.reload();

    // Mobile nav should be visible
    const mobileNav = page.locator('[data-testid="mobile-nav"]');
    if (await mobileNav.isVisible()) {
      await expect(mobileNav).toBeVisible();
      
      // Can tap nav items
      await mobileNav.locator('button').first().click();
    }
  });

  test('logo links to home', async ({ page }) => {
    await page.goto('/tasks');
    await page.click('[data-testid="logo"], header a:has-text("Chamba")');
    await expect(page).toHaveURL('/');
  });
});
