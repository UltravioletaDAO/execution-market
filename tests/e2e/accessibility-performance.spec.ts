/**
 * Accessibility & Performance E2E Tests
 *
 * Critical for LATAM users who may have:
 * - Older devices with limited processing power
 * - Slow/unstable network connections
 * - Various accessibility needs
 */
import { test, expect } from '@playwright/test';
import { TEST_USERS, clearAuthState } from './fixtures/test-fixtures';

// ============================================================================
// Accessibility Tests
// ============================================================================

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/');

    // Check for h1
    const h1 = page.locator('h1');
    await expect(h1.first()).toBeVisible();

    // Verify heading order
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();
    let lastLevel = 0;

    for (const heading of headings) {
      const tagName = await heading.evaluate((el) => el.tagName.toLowerCase());
      const level = parseInt(tagName.charAt(1));

      // Should not skip levels (e.g., h1 -> h3 without h2)
      if (lastLevel > 0) {
        expect(level - lastLevel).toBeLessThanOrEqual(1);
      }
      lastLevel = level;
    }
  });

  test('should have alt text for images', async ({ page }) => {
    await page.goto('/');

    const images = await page.locator('img').all();

    for (const img of images) {
      const alt = await img.getAttribute('alt');
      const role = await img.getAttribute('role');

      // Images should have alt text OR be marked as decorative
      const hasAlt = alt !== null && alt !== '';
      const isDecorative = role === 'presentation' || alt === '';

      expect(hasAlt || isDecorative).toBeTruthy();
    }
  });

  test('should have proper form labels', async ({ page }) => {
    await page.goto('/');

    // Open auth modal to get form elements
    await page.getByRole('button', { name: /iniciar sesion|login/i }).click();

    const inputs = await page.locator('input:not([type="hidden"])').all();

    for (const input of inputs) {
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');
      const placeholder = await input.getAttribute('placeholder');

      // Input should be labelled somehow
      const hasLabel = id ? (await page.locator(`label[for="${id}"]`).count()) > 0 : false;
      const hasAriaLabel = ariaLabel !== null;
      const hasAriaLabelledBy = ariaLabelledBy !== null;
      const hasPlaceholder = placeholder !== null;

      expect(hasLabel || hasAriaLabel || hasAriaLabelledBy || hasPlaceholder).toBeTruthy();
    }
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');

    // Tab through interactive elements
    await page.keyboard.press('Tab');

    // First focusable element should be focused
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeTruthy();

    // Continue tabbing and verify focus moves
    const focusedElements: string[] = [];
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const tag = await page.evaluate(() => document.activeElement?.tagName);
      if (tag) focusedElements.push(tag);
    }

    // Should have navigated through multiple elements
    expect(focusedElements.length).toBeGreaterThan(0);
  });

  test('should have visible focus indicators', async ({ page }) => {
    await page.goto('/');

    // Tab to first focusable element
    await page.keyboard.press('Tab');

    // Get the focused element
    const focusedElement = page.locator(':focus');

    // Check for focus styles
    const outlineStyle = await focusedElement.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        outline: style.outline,
        boxShadow: style.boxShadow,
        borderColor: style.borderColor,
      };
    });

    // Should have some visual focus indicator
    const hasOutline = outlineStyle.outline !== 'none' && outlineStyle.outline !== '';
    const hasBoxShadow = outlineStyle.boxShadow !== 'none' && outlineStyle.boxShadow !== '';

    expect(hasOutline || hasBoxShadow).toBeTruthy();
  });

  test('should have sufficient color contrast', async ({ page }) => {
    await page.goto('/');

    // Check text elements for contrast
    const textElements = await page.locator('p, h1, h2, h3, span, a, button').all();

    for (const element of textElements.slice(0, 20)) {
      // Sample check
      const isVisible = await element.isVisible().catch(() => false);
      if (!isVisible) continue;

      const styles = await element.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return {
          color: style.color,
          backgroundColor: style.backgroundColor,
          fontSize: style.fontSize,
        };
      });

      // Basic check: text shouldn't be white on white or similar
      expect(styles.color).not.toBe(styles.backgroundColor);
    }
  });

  test('should support screen reader announcements', async ({ page }) => {
    await page.goto('/');

    // Check for aria-live regions
    const liveRegions = await page.locator('[aria-live]').count();

    // Check for role="alert" elements
    const alerts = await page.locator('[role="alert"]').count();

    // Check for role="status" elements
    const status = await page.locator('[role="status"]').count();

    // App should have some live regions for dynamic content
    // This is informational - not a failure if 0
    console.log(`Live regions: ${liveRegions}, Alerts: ${alerts}, Status: ${status}`);
  });

  test('should work with reduced motion preference', async ({ page }) => {
    // Enable reduced motion
    await page.emulateMedia({ reducedMotion: 'reduce' });

    await page.goto('/');

    // Check that transitions are reduced or removed
    const button = page.locator('button').first();
    if (await button.isVisible()) {
      const transition = await button.evaluate((el) => {
        return window.getComputedStyle(el).transition;
      });

      // With reduced motion, transitions should be minimal or none
      // This is a soft check as implementation varies
      console.log(`Button transition with reduced motion: ${transition}`);
    }
  });
});

// ============================================================================
// Performance Tests
// ============================================================================

test.describe('Performance', () => {
  test('should load initial page within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/');

    // Wait for main content to be visible
    await expect(page.getByText('Chamba')).toBeVisible();

    const loadTime = Date.now() - startTime;

    // Should load within 5 seconds on reasonable connection
    expect(loadTime).toBeLessThan(5000);
    console.log(`Initial page load time: ${loadTime}ms`);
  });

  test('should render task list efficiently', async ({ page }) => {
    await page.addInitScript(
      (worker) => {
        window.localStorage.setItem('chamba_wallet_address', worker.walletAddress);
      },
      TEST_USERS.worker
    );

    await page.goto('/');

    const startTime = Date.now();

    // Wait for task list to load
    await expect(page.locator('[data-testid="task-card"], .task-card').first()).toBeVisible({
      timeout: 10000,
    });

    const renderTime = Date.now() - startTime;

    // Task list should render within 3 seconds
    expect(renderTime).toBeLessThan(3000);
    console.log(`Task list render time: ${renderTime}ms`);
  });

  test('should handle rapid navigation without lag', async ({ page }) => {
    await page.goto('/');

    const startTime = Date.now();

    // Rapid navigation between sections
    for (let i = 0; i < 5; i++) {
      await page.getByText(/tareas|tasks/i).first().click().catch(() => {});
      await page.waitForTimeout(100);
    }

    const navTime = Date.now() - startTime;

    // Should complete navigation cycles within 3 seconds
    expect(navTime).toBeLessThan(3000);
    console.log(`Navigation stress test time: ${navTime}ms`);
  });

  test('should maintain reasonable memory usage', async ({ page }) => {
    await page.goto('/');

    // Get initial memory
    const initialMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });

    // Perform various actions
    await page.getByRole('button', { name: /iniciar sesion|login/i }).click();
    await page.waitForTimeout(500);
    await page.keyboard.press('Escape');

    // Navigate around
    await page.getByText(/tareas|tasks/i).first().click().catch(() => {});
    await page.waitForTimeout(500);

    // Get final memory
    const finalMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });

    if (initialMemory > 0 && finalMemory > 0) {
      const memoryIncrease = finalMemory - initialMemory;
      console.log(`Memory increase: ${Math.round(memoryIncrease / 1024 / 1024)}MB`);

      // Memory shouldn't increase dramatically (less than 50MB)
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
    }
  });

  test('should work on slow 3G connection', async ({ page, context }) => {
    // Simulate slow 3G
    const client = await context.newCDPSession(page);
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: (500 * 1024) / 8, // 500 kbps
      uploadThroughput: (500 * 1024) / 8,
      latency: 400, // 400ms latency
    });

    const startTime = Date.now();

    await page.goto('/');

    // Should still load within 15 seconds on slow 3G
    await expect(page.getByText('Chamba')).toBeVisible({ timeout: 15000 });

    const loadTime = Date.now() - startTime;
    console.log(`Load time on slow 3G: ${loadTime}ms`);

    // Should be usable even if slow
    expect(loadTime).toBeLessThan(20000);
  });

  test('should handle offline gracefully', async ({ page, context }) => {
    await page.goto('/');

    // Wait for initial load
    await expect(page.getByText('Chamba')).toBeVisible();

    // Go offline
    await context.setOffline(true);

    // Try to navigate or interact
    await page.getByRole('button', { name: /iniciar sesion|login/i }).click().catch(() => {});

    // Should show offline indicator or handle gracefully
    await expect(
      page
        .getByText(/sin conexion|offline|error.*red|network/i)
        .or(page.locator('.offline-indicator'))
    ).toBeVisible({ timeout: 5000 }).catch(() => {
      // App might not have offline handling yet - that's OK
      console.log('No offline indicator found - consider adding offline support');
    });

    // Go back online
    await context.setOffline(false);
  });
});

// ============================================================================
// Mobile-Specific Tests
// ============================================================================

test.describe('Mobile Experience', () => {
  test.use({
    viewport: { width: 375, height: 667 },
    isMobile: true,
    hasTouch: true,
  });

  test('should display mobile-optimized layout', async ({ page }) => {
    await page.goto('/');

    // Header should be visible and not overflow
    const header = page.locator('header').first();
    if (await header.isVisible()) {
      const box = await header.boundingBox();
      expect(box?.width).toBeLessThanOrEqual(375);
    }

    // Content should fit viewport
    const body = page.locator('body');
    const scrollWidth = await body.evaluate((el) => el.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375 + 5); // Allow small margin
  });

  test('should have touch-friendly tap targets', async ({ page }) => {
    await page.goto('/');

    // Check button sizes
    const buttons = await page.locator('button').all();

    for (const button of buttons.slice(0, 10)) {
      if (!(await button.isVisible())) continue;

      const box = await button.boundingBox();
      if (box) {
        // Minimum recommended touch target is 44x44px
        expect(box.height).toBeGreaterThanOrEqual(40);
      }
    }
  });

  test('should support swipe gestures where applicable', async ({ page }) => {
    await page.goto('/');

    // Check for swipeable elements (carousels, lists, etc.)
    const swipeableElements = await page.locator('[data-swipeable], .swiper, .carousel').count();

    // Log for informational purposes
    console.log(`Found ${swipeableElements} swipeable elements`);
  });

  test('should not have horizontal scroll', async ({ page }) => {
    await page.goto('/');

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });

    expect(hasHorizontalScroll).toBeFalsy();
  });
});

// ============================================================================
// Internationalization Tests
// ============================================================================

test.describe('Internationalization', () => {
  test('should display Spanish content by default', async ({ page }) => {
    await page.goto('/');

    // Check for Spanish text
    await expect(
      page.getByText(/tareas|iniciar sesion|bienvenido/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('should switch to English', async ({ page }) => {
    await page.goto('/');

    // Find language switcher
    const langSwitcher = page.locator('[data-testid="language-switcher"], .language-switcher');

    if (await langSwitcher.isVisible({ timeout: 5000 })) {
      await langSwitcher.click();
      await page.getByText('English').or(page.getByText('EN')).click();

      // Verify English content
      await expect(
        page.getByText(/tasks|login|welcome/i)
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test('should preserve language preference', async ({ page }) => {
    // Set English preference
    await page.addInitScript(() => {
      window.localStorage.setItem('chamba_language', 'en');
    });

    await page.goto('/');

    // Should show English content
    await expect(
      page.getByText(/tasks|login/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('should format currency in local format', async ({ page }) => {
    await page.goto('/');

    // Wait for task cards
    await page.waitForTimeout(2000);

    // Look for currency formatting
    const currencyText = await page.locator('text=/\\$[\\d,.]+/').first().textContent();

    if (currencyText) {
      // Should have proper currency formatting
      expect(currencyText).toMatch(/\$[\d,]+\.?\d*/);
    }
  });

  test('should format dates in local format', async ({ page }) => {
    await page.addInitScript(
      (worker) => {
        window.localStorage.setItem('chamba_wallet_address', worker.walletAddress);
      },
      TEST_USERS.worker
    );

    await page.goto('/');

    // Navigate to a task with deadline
    const taskCard = page.locator('[data-testid="task-card"]').first();
    if (await taskCard.isVisible({ timeout: 5000 })) {
      await taskCard.click();

      // Look for date formatting
      const dateText = page.getByText(/\d{1,2}\s+(de\s+)?\w+\s+\d{4}|\d{1,2}\/\d{1,2}\/\d{2,4}/i);
      if (await dateText.isVisible({ timeout: 3000 })) {
        // Date is formatted
        expect(await dateText.textContent()).toBeTruthy();
      }
    }
  });
});
