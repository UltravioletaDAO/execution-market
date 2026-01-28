import { test, expect } from '@playwright/test';

/**
 * Internationalization Tests
 * Test language switching and translations.
 */

test.describe('Internationalization', () => {
  test('default language is Spanish', async ({ page }) => {
    await page.goto('/');
    
    // Page should have Spanish content
    const htmlLang = await page.locator('html').getAttribute('lang');
    expect(htmlLang).toMatch(/es|es-CO|es-419/);
  });

  test('can switch to English', async ({ page }) => {
    await page.goto('/');
    
    const langSwitcher = page.locator('[data-testid="language-switcher"], button:has-text("ES"), button:has-text("EN")');
    
    if (await langSwitcher.isVisible()) {
      await langSwitcher.click();
      
      // Select English
      await page.click('text=English, text=EN');
      
      // Content should change to English
      await expect(page.locator('html')).toHaveAttribute('lang', /en/);
    }
  });

  test('language preference persists', async ({ page }) => {
    await page.goto('/');
    
    // Switch to English
    const langSwitcher = page.locator('[data-testid="language-switcher"]');
    if (await langSwitcher.isVisible()) {
      await langSwitcher.click();
      await page.click('text=English, text=EN');
      
      // Reload page
      await page.reload();
      
      // Should still be English
      const htmlLang = await page.locator('html').getAttribute('lang');
      expect(htmlLang).toMatch(/en/);
    }
  });

  test('all UI elements have translations', async ({ page }) => {
    await page.goto('/');
    
    // Check for untranslated keys (usually appear as translation.key)
    const body = await page.locator('body').textContent();
    const hasUntranslated = /\b[a-z]+\.[a-z]+\.[a-z]+\b/i.test(body || '');
    
    // Should not have obvious untranslated keys
    // This is a soft check - some technical terms might match
    expect(hasUntranslated).toBeFalsy();
  });
});
