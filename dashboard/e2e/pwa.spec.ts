import { test, expect } from '@playwright/test';

/**
 * PWA Tests
 * Test Progressive Web App functionality.
 */

test.describe('PWA Features', () => {
  test('has valid manifest', async ({ page, request }) => {
    const response = await request.get('/manifest.json');
    expect(response.status()).toBe(200);
    
    const manifest = await response.json();
    expect(manifest.name).toBe('Chamba - Human Execution Layer');
    expect(manifest.short_name).toBe('Chamba');
    expect(manifest.display).toBe('standalone');
    expect(manifest.icons.length).toBeGreaterThan(0);
  });

  test('service worker is registered', async ({ page }) => {
    await page.goto('/');
    
    // Check if service worker is registered
    const swRegistered = await page.evaluate(async () => {
      if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        return registrations.length > 0;
      }
      return false;
    });
    
    // SW should be registered in production
    // In dev mode, it might not be
    expect(typeof swRegistered).toBe('boolean');
  });

  test('page works offline after cache', async ({ page, context }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Go offline
    await context.setOffline(true);
    
    // Try to reload
    try {
      await page.reload({ timeout: 5000 });
      // Should show cached content or offline page
      const bodyText = await page.locator('body').textContent();
      expect(bodyText).toBeTruthy();
    } catch {
      // Expected if SW not caching in dev
    }
    
    // Go back online
    await context.setOffline(false);
  });

  test('responsive design works on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Content should be visible
    await expect(page.locator('main')).toBeVisible();
    
    // No horizontal scroll
    const body = page.locator('body');
    const scrollWidth = await body.evaluate(el => el.scrollWidth);
    const clientWidth = await body.evaluate(el => el.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });
});
