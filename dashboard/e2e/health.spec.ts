import { test, expect } from '@playwright/test';

/**
 * Health Check Tests
 * These tests verify that the application is running and responsive.
 * This is the FIRST gate - if these fail, nothing else matters.
 */

test.describe('Health Checks', () => {
  test('API health endpoint returns 200', async ({ request }) => {
    const apiUrl = process.env.API_URL || 'http://localhost:8000';
    const response = await request.get(`${apiUrl}/health`);
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('Dashboard loads successfully', async ({ page }) => {
    await page.goto('/');
    
    // Should load without errors
    await expect(page).toHaveTitle(/Execution Market/i);
    
    // Main content should be visible
    await expect(page.locator('main')).toBeVisible();
  });

  test('No console errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Filter out known third-party errors
    const criticalErrors = errors.filter(e => 
      !e.includes('favicon') && 
      !e.includes('third-party')
    );

    expect(criticalErrors).toHaveLength(0);
  });
});
