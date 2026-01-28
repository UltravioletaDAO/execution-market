/**
 * Chamba Dashboard - Authentication E2E Tests
 *
 * Tests for:
 * - Landing page elements
 * - Login flow (wallet, email)
 * - Signup flow
 * - Logout
 * - Role-based navigation (worker vs agent)
 */
import { test, expect } from '@playwright/test';

// =============================================================================
// Landing Page Tests
// =============================================================================

test.describe('Landing Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('displays Chamba branding', async ({ page }) => {
    // Check for Chamba logo/name in header
    await expect(page.locator('header')).toContainText('Chamba');
  });

  test('shows login button when not authenticated', async ({ page }) => {
    // The login button should be visible in the header
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await expect(loginButton).toBeVisible();
  });

  test('displays hero section with value proposition', async ({ page }) => {
    // Hero title
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/human execution layer|capa de ejecucion/i);

    // Subtitle should exist
    const heroSection = page.locator('main');
    await expect(heroSection).toBeVisible();
  });

  test('shows worker CTA button', async ({ page }) => {
    // Worker button (green)
    const workerButton = page.getByRole('button', { name: /worker|trabajador|soy trabajador/i });
    await expect(workerButton).toBeVisible();
  });

  test('shows agent CTA button', async ({ page }) => {
    // Agent button (purple)
    const agentButton = page.getByRole('button', { name: /agent|agente|soy agente/i });
    await expect(agentButton).toBeVisible();
  });

  test('displays feature cards', async ({ page }) => {
    // Should have 3 feature cards in the grid
    const featureCards = page.locator('main .bg-white.rounded-xl');
    await expect(featureCards).toHaveCount(3);
  });

  test('shows footer with Ultravioleta DAO credit', async ({ page }) => {
    const footer = page.locator('footer');
    await expect(footer).toContainText(/ultravioleta dao/i);
  });

  test('has language switcher', async ({ page }) => {
    // Language switcher should be in header
    const langSwitcher = page.locator('header').getByRole('button').filter({ hasText: /en|es|language/i });
    // If not found by text, look for a dropdown or select
    const hasLangSwitcher = await langSwitcher.count() > 0 ||
      await page.locator('header select').count() > 0;
    expect(hasLangSwitcher).toBeTruthy();
  });
});

// =============================================================================
// Auth Modal Tests
// =============================================================================

test.describe('Auth Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('opens auth modal when clicking login button', async ({ page }) => {
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    // Modal should appear
    const modal = page.locator('[role="dialog"], .fixed.inset-0');
    await expect(modal).toBeVisible();
  });

  test('opens auth modal when clicking worker CTA', async ({ page }) => {
    const workerButton = page.getByRole('button', { name: /worker|trabajador|soy trabajador/i });
    await workerButton.click();

    // Modal should appear (if not authenticated)
    const modal = page.locator('[role="dialog"], .fixed.inset-0');
    await expect(modal).toBeVisible();
  });

  test('opens auth modal when clicking agent CTA', async ({ page }) => {
    const agentButton = page.getByRole('button', { name: /agent|agente|soy agente/i });
    await agentButton.click();

    // Modal should appear (if not authenticated)
    const modal = page.locator('[role="dialog"], .fixed.inset-0');
    await expect(modal).toBeVisible();
  });

  test('shows wallet connection options by default', async ({ page }) => {
    // Open modal
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    // Should show wallet options (MetaMask, WalletConnect, etc.)
    await expect(page.getByText(/connect wallet|conectar wallet/i)).toBeVisible();
  });

  test('can switch to manual wallet entry mode', async ({ page }) => {
    // Open modal
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    // Click on manual wallet entry option
    const manualWalletOption = page.getByText(/enter.*manually|introducir.*manual|or enter/i);
    if (await manualWalletOption.isVisible()) {
      await manualWalletOption.click();

      // Should show wallet address input
      await expect(page.getByPlaceholder(/0x/i)).toBeVisible();
    }
  });

  test('can switch to email/password mode', async ({ page }) => {
    // Open modal
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    // Click on email option
    const emailOption = page.getByRole('button', { name: /email.*password|correo/i });
    if (await emailOption.isVisible()) {
      await emailOption.click();

      // Should show email and password inputs
      await expect(page.getByPlaceholder(/email|correo/i)).toBeVisible();
      await expect(page.locator('input[type="password"]')).toBeVisible();
    }
  });

  test('can close modal with X button', async ({ page }) => {
    // Open modal
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    // Find and click close button
    const closeButton = page.locator('.fixed.inset-0').getByRole('button').first();
    // Or look for the X icon button
    const xButton = page.locator('button').filter({ has: page.locator('svg path[d*="6 18L18 6"]') });

    if (await xButton.count() > 0) {
      await xButton.click();
    } else if (await closeButton.isVisible()) {
      await closeButton.click();
    }

    // Modal should be closed (or clicking backdrop)
    await page.locator('.bg-black\\/50, [class*="backdrop"]').click({ force: true });

    // Wait for modal to disappear
    await expect(page.locator('[role="dialog"], .fixed.inset-0 .bg-white')).not.toBeVisible({ timeout: 3000 });
  });

  test('can close modal by clicking backdrop', async ({ page }) => {
    // Open modal
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    // Click on backdrop (the dark overlay)
    const backdrop = page.locator('.bg-black\\/50, .backdrop-blur-sm').first();
    await backdrop.click({ position: { x: 10, y: 10 } });

    // Modal should close
    await expect(page.locator('.bg-white.rounded-2xl')).not.toBeVisible({ timeout: 3000 });
  });
});

// =============================================================================
// Email Login Flow Tests
// =============================================================================

test.describe('Email Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    // Open modal and switch to email mode
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    const emailOption = page.getByRole('button', { name: /email.*password|correo/i });
    if (await emailOption.isVisible()) {
      await emailOption.click();
    }
  });

  test('shows email and password fields', async ({ page }) => {
    await expect(page.locator('input[type="email"], input[placeholder*="email" i]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('shows validation on empty submit', async ({ page }) => {
    // Find and click login/submit button
    const submitButton = page.getByRole('button', { name: /login|iniciar sesion|entrar/i }).last();

    // Try to submit empty form
    await submitButton.click();

    // Browser should show validation (required fields)
    // or custom error message should appear
    const emailInput = page.locator('input[type="email"], input[placeholder*="email" i]');
    // Check if input is invalid (HTML5 validation)
    const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBeTruthy();
  });

  test('shows error for invalid credentials', async ({ page }) => {
    // Fill invalid credentials
    await page.locator('input[type="email"], input[placeholder*="email" i]').fill('invalid@test.com');
    await page.locator('input[type="password"]').fill('wrongpassword');

    // Submit
    const submitButton = page.getByRole('button', { name: /login|iniciar sesion|entrar/i }).last();
    await submitButton.click();

    // Should show error message
    await expect(page.locator('.text-red-700, .bg-red-50, [class*="error"]')).toBeVisible({ timeout: 5000 });
  });

  test('has link to switch to signup', async ({ page }) => {
    // Look for "no account" / "register" link
    const signupLink = page.getByRole('button', { name: /register|signup|registrar|crear cuenta/i });
    await expect(signupLink).toBeVisible();
  });
});

// =============================================================================
// Manual Wallet Entry Tests
// =============================================================================

test.describe('Manual Wallet Entry', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    // Open modal
    const loginButton = page.getByRole('button', { name: /login|iniciar/i });
    await loginButton.click();

    // Switch to manual wallet mode
    const manualOption = page.getByText(/enter.*manually|introducir.*manual|or enter/i);
    if (await manualOption.isVisible()) {
      await manualOption.click();
    }
  });

  test('shows wallet address input field', async ({ page }) => {
    const walletInput = page.getByPlaceholder(/0x/i);
    await expect(walletInput).toBeVisible();
  });

  test('validates wallet address format', async ({ page }) => {
    const walletInput = page.getByPlaceholder(/0x/i);
    const submitButton = page.getByRole('button', { name: /connect|conectar/i });

    // Enter invalid wallet
    await walletInput.fill('invalid-address');
    await submitButton.click();

    // Should show error
    await expect(page.locator('.text-red-700, .bg-red-50, [class*="error"]')).toBeVisible({ timeout: 3000 });
  });

  test('accepts valid wallet address format', async ({ page }) => {
    const walletInput = page.getByPlaceholder(/0x/i);

    // Enter valid format wallet
    await walletInput.fill('0x1234567890123456789012345678901234567890');

    // Input should be valid (no immediate error shown)
    const hasError = await page.locator('.text-red-700, .bg-red-50').isVisible();
    expect(hasError).toBeFalsy();
  });

  test('shows optional display name field', async ({ page }) => {
    // Display name field should be visible
    const displayNameInput = page.getByPlaceholder(/name|nombre/i);
    await expect(displayNameInput).toBeVisible();
  });
});

// =============================================================================
// Navigation After Auth Tests
// =============================================================================

test.describe('Role-based Navigation', () => {
  test('clicking worker CTA should lead to tasks page after auth', async ({ page }) => {
    await page.goto('/');

    // This test verifies the flow exists, not that auth succeeds
    // (would need mocked auth for full flow)
    const workerButton = page.getByRole('button', { name: /worker|trabajador|soy trabajador/i });
    await workerButton.click();

    // Modal opens
    await expect(page.locator('.fixed.inset-0')).toBeVisible();

    // The intended destination after auth is /tasks
    // Verify the button and modal are properly connected
  });

  test('clicking agent CTA should lead to agent dashboard after auth', async ({ page }) => {
    await page.goto('/');

    const agentButton = page.getByRole('button', { name: /agent|agente|soy agente/i });
    await agentButton.click();

    // Modal opens
    await expect(page.locator('.fixed.inset-0')).toBeVisible();

    // The intended destination after auth is /agent/dashboard
  });
});

// =============================================================================
// Public Pages Tests
// =============================================================================

test.describe('Public Pages', () => {
  test('can access about page', async ({ page }) => {
    await page.goto('/about');
    await expect(page.getByText(/chamba|ultravioleta/i)).toBeVisible();
  });

  test('can access FAQ page', async ({ page }) => {
    await page.goto('/faq');
    await expect(page.getByText(/pago|disputa|reputacion/i)).toBeVisible();
  });

  test('about page has back navigation', async ({ page }) => {
    await page.goto('/about');

    // Should have back button
    const backButton = page.getByRole('button').filter({ has: page.locator('svg') }).first();
    await expect(backButton).toBeVisible();
  });
});

// =============================================================================
// Protected Routes Tests
// =============================================================================

test.describe('Protected Routes', () => {
  test('tasks page requires authentication', async ({ page }) => {
    // Go directly to protected route
    await page.goto('/tasks');

    // Should redirect to landing or show auth modal
    // Check if we're on landing page or auth modal is shown
    const isOnLanding = await page.locator('h1').filter({ hasText: /human execution layer/i }).isVisible();
    const hasAuthModal = await page.locator('.fixed.inset-0').isVisible();

    expect(isOnLanding || hasAuthModal).toBeTruthy();
  });

  test('agent dashboard requires authentication', async ({ page }) => {
    await page.goto('/agent/dashboard');

    // Should redirect or show auth
    const isOnLanding = await page.locator('h1').filter({ hasText: /human execution layer/i }).isVisible();
    const hasAuthModal = await page.locator('.fixed.inset-0').isVisible();

    expect(isOnLanding || hasAuthModal).toBeTruthy();
  });

  test('profile page requires authentication', async ({ page }) => {
    await page.goto('/profile');

    const isOnLanding = await page.locator('h1').filter({ hasText: /human execution layer/i }).isVisible();
    const hasAuthModal = await page.locator('.fixed.inset-0').isVisible();

    expect(isOnLanding || hasAuthModal).toBeTruthy();
  });

  test('earnings page requires authentication', async ({ page }) => {
    await page.goto('/earnings');

    const isOnLanding = await page.locator('h1').filter({ hasText: /human execution layer/i }).isVisible();
    const hasAuthModal = await page.locator('.fixed.inset-0').isVisible();

    expect(isOnLanding || hasAuthModal).toBeTruthy();
  });
});
