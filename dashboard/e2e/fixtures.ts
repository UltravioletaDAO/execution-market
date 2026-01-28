/**
 * Chamba Dashboard - E2E Test Fixtures
 *
 * Shared test utilities, mock data, and helper functions
 */
import { test as base, expect, type Page } from '@playwright/test';

// =============================================================================
// Mock Data
// =============================================================================

export const MOCK_WORKER = {
  user_id: 'test-worker-1',
  role: 'executor' as const,
  wallet_address: '0x1234567890123456789012345678901234567890',
  display_name: 'Test Worker',
  reputation_score: 75,
  tasks_completed: 12,
  total_earnings: 245.50,
};

export const MOCK_AGENT = {
  user_id: 'test-agent-1',
  role: 'agent' as const,
  wallet_address: '0xABCDEF1234567890ABCDEF1234567890ABCDEF12',
  display_name: 'Test Agent AI',
  is_agent: true,
  tasks_created: 47,
  total_spent: 1892.50,
};

export const MOCK_TASK = {
  id: 'task-1',
  title: 'Verificar direccion de entrega en Polanco',
  instructions: 'Tomar foto del exterior del edificio y confirmar numero de calle visible. Asegurarse de que el GPS este habilitado.',
  category: 'physical_presence',
  location_hint: 'Polanco, CDMX',
  bounty_usd: 15.00,
  deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  status: 'published',
  min_reputation: 50,
  evidence_required: ['photo_geo'],
};

export const MOCK_SUBMISSION = {
  id: 'sub-1',
  task_id: 'task-1',
  executor_id: MOCK_WORKER.user_id,
  submitted_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  auto_check_passed: true,
  evidence: {
    photo_geo: { file: 'photo.jpg', verified: true },
  },
};

// =============================================================================
// Session Setup Helpers
// =============================================================================

/**
 * Set up an authenticated worker session
 */
export async function setupWorkerSession(page: Page): Promise<void> {
  await page.addInitScript((worker) => {
    window.localStorage.setItem('chamba_auth', JSON.stringify(worker));
    window.localStorage.setItem('chamba_role', 'worker');
  }, MOCK_WORKER);
}

/**
 * Set up an authenticated agent session
 */
export async function setupAgentSession(page: Page): Promise<void> {
  await page.addInitScript((agent) => {
    window.localStorage.setItem('chamba_auth', JSON.stringify(agent));
    window.localStorage.setItem('chamba_role', 'agent');
  }, MOCK_AGENT);
}

/**
 * Clear authentication state
 */
export async function clearSession(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.removeItem('chamba_auth');
    window.localStorage.removeItem('chamba_role');
  });
}

// =============================================================================
// Navigation Helpers
// =============================================================================

/**
 * Navigate to a page and wait for it to load
 */
export async function navigateTo(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

/**
 * Wait for page to fully load including API calls
 */
export async function waitForPageReady(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  // Wait for any loading indicators to disappear
  const loadingIndicator = page.locator('.animate-pulse, .animate-spin, [class*="loading"]');
  if (await loadingIndicator.count() > 0) {
    await loadingIndicator.first().waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
  }
}

// =============================================================================
// UI Interaction Helpers
// =============================================================================

/**
 * Fill a form field by label or placeholder
 */
export async function fillField(
  page: Page,
  labelOrPlaceholder: string | RegExp,
  value: string
): Promise<void> {
  const input = page.getByLabel(labelOrPlaceholder).or(page.getByPlaceholder(labelOrPlaceholder));
  await input.fill(value);
}

/**
 * Click a button by name
 */
export async function clickButton(page: Page, name: string | RegExp): Promise<void> {
  await page.getByRole('button', { name }).click();
}

/**
 * Check if an element is visible
 */
export async function isVisible(page: Page, textOrLocator: string | RegExp): Promise<boolean> {
  const element = page.getByText(textOrLocator);
  return element.isVisible();
}

/**
 * Wait for a toast/notification to appear
 */
export async function waitForToast(page: Page, text?: string | RegExp): Promise<void> {
  const toast = text
    ? page.getByText(text)
    : page.locator('[class*="toast"], [class*="notification"], [role="alert"]');
  await expect(toast.first()).toBeVisible({ timeout: 5000 });
}

// =============================================================================
// Task Flow Helpers
// =============================================================================

/**
 * Create a task through the UI (for agent tests)
 */
export async function createTask(
  page: Page,
  options: {
    title: string;
    instructions: string;
    bounty: number;
    category?: string;
    evidence?: string[];
  }
): Promise<void> {
  await navigateTo(page, '/agent/tasks/create');

  // Fill details
  await page.getByPlaceholder(/titulo|title/i).fill(options.title);
  await page.locator('textarea').first().fill(options.instructions);

  // Set bounty
  const bountyInput = page.locator('input[type="number"]').first();
  await bountyInput.fill(options.bounty.toString());

  // Set deadline (tomorrow)
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const deadlineInput = page.locator('input[type="datetime-local"]');
  await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));

  // Navigate through steps
  await clickButton(page, /siguiente|next/i);
  await clickButton(page, /siguiente|next/i);

  // Select required evidence
  const reqButton = page.getByRole('button', { name: /req/i }).first();
  await reqButton.click();

  await clickButton(page, /siguiente|next/i);

  // Preview and publish
  await clickButton(page, /publicar|publish/i);
}

/**
 * Accept a task as a worker
 */
export async function acceptTask(page: Page, taskId: string): Promise<void> {
  await navigateTo(page, `/tasks/${taskId}`);
  await clickButton(page, /aceptar|accept/i);

  // Wait for confirmation or navigation
  await waitForPageReady(page);
}

/**
 * Submit evidence for a task
 */
export async function submitEvidence(
  page: Page,
  taskId: string,
  files: { name: string; type: string; content: string }[]
): Promise<void> {
  await navigateTo(page, `/tasks/${taskId}/submit`);

  // Upload each file
  for (const file of files) {
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.type,
      buffer: Buffer.from(file.content),
    });
  }

  await clickButton(page, /enviar|submit/i);
  await waitForPageReady(page);
}

// =============================================================================
// Assertion Helpers
// =============================================================================

/**
 * Assert that a specific text is visible on the page
 */
export async function assertTextVisible(page: Page, text: string | RegExp): Promise<void> {
  await expect(page.getByText(text)).toBeVisible();
}

/**
 * Assert that a button is enabled/disabled
 */
export async function assertButtonEnabled(
  page: Page,
  name: string | RegExp,
  enabled: boolean
): Promise<void> {
  const button = page.getByRole('button', { name });
  if (enabled) {
    await expect(button).toBeEnabled();
  } else {
    await expect(button).toBeDisabled();
  }
}

/**
 * Assert current URL matches pattern
 */
export async function assertUrl(page: Page, pattern: string | RegExp): Promise<void> {
  await expect(page).toHaveURL(pattern);
}

// =============================================================================
// Extended Test Fixture
// =============================================================================

/**
 * Extended test fixture with common utilities
 */
export const test = base.extend<{
  workerPage: Page;
  agentPage: Page;
}>({
  workerPage: async ({ page }, use) => {
    await setupWorkerSession(page);
    await use(page);
  },

  agentPage: async ({ page }, use) => {
    await setupAgentSession(page);
    await use(page);
  },
});

export { expect };
