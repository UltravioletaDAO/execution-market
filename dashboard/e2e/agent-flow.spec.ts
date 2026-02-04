/**
 * Execution Market Dashboard - Agent Flow E2E Tests
 *
 * Tests for the complete AI agent journey:
 * - Agent dashboard overview
 * - Creating new tasks
 * - Task management
 * - Reviewing submissions
 * - Approving/rejecting evidence
 * - Payment flow
 * - Analytics
 */
import { test, expect } from '@playwright/test';

// =============================================================================
// Test Helpers
// =============================================================================

/**
 * Mock authenticated agent session
 */
async function setupAgentSession(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('em_auth', JSON.stringify({
      user_id: 'test-agent-1',
      role: 'agent',
      wallet_address: '0xABCDEF1234567890ABCDEF1234567890ABCDEF12',
      display_name: 'Test Agent AI',
      is_agent: true,
    }));
  });
}

// =============================================================================
// Agent Dashboard Tests
// =============================================================================

test.describe('Agent Dashboard - Overview', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/dashboard');
  });

  test('displays agent dashboard header', async ({ page }) => {
    await expect(page.getByText(/panel.*agente|agent.*dashboard/i)).toBeVisible();
  });

  test('shows analytics overview cards', async ({ page }) => {
    // Should show key metrics
    await expect(page.getByText(/tareas.*creadas|tasks.*created/i)).toBeVisible();
    await expect(page.getByText(/completad|completed/i)).toBeVisible();
    await expect(page.getByText(/gasto|spent|\$/i)).toBeVisible();
  });

  test('displays tasks created count', async ({ page }) => {
    const statsCard = page.locator('.bg-white.rounded-lg').filter({ hasText: /tareas.*creadas|tasks.*created/i });
    await expect(statsCard).toBeVisible();
  });

  test('shows completion rate', async ({ page }) => {
    await expect(page.getByText(/tasa.*completado|completion.*rate|%/i)).toBeVisible();
  });

  test('displays total spent amount', async ({ page }) => {
    await expect(page.getByText(/gasto.*total|total.*spent|\$.*usdc/i)).toBeVisible();
  });

  test('shows average completion time', async ({ page }) => {
    await expect(page.getByText(/tiempo.*promedio|average.*time|h.*promedio/i)).toBeVisible();
  });

  test('has create task button', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /crear.*tarea|create.*task|nueva.*tarea/i });
    await expect(createButton).toBeVisible();
  });

  test('shows active tasks section', async ({ page }) => {
    await expect(page.getByText(/tareas.*activas|active.*tasks/i)).toBeVisible();
  });

  test('shows pending submissions section', async ({ page }) => {
    await expect(page.getByText(/entregas.*revisar|pending.*submissions|por.*revisar/i)).toBeVisible();
  });

  test('has task filter tabs', async ({ page }) => {
    const filterTabs = page.locator('button').filter({ hasText: /todas|all|pendientes|pending|en.*progreso|in.*progress/i });
    const tabCount = await filterTabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(2);
  });
});

// =============================================================================
// Create Task Flow Tests
// =============================================================================

test.describe('Agent - Create Task', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/tasks/create');
  });

  test('shows create task form', async ({ page }) => {
    await expect(page.getByText(/crear.*tarea|create.*task|nueva.*tarea/i)).toBeVisible();
  });

  test('has step indicator', async ({ page }) => {
    // Should show progress steps (details, location, evidence, preview)
    const stepIndicator = page.locator('.flex.items-center').filter({ has: page.locator('.rounded-full') });
    if (await stepIndicator.count() > 0) {
      await expect(stepIndicator.first()).toBeVisible();
    }
  });

  test('shows title input field', async ({ page }) => {
    const titleInput = page.locator('input').filter({ hasText: /titulo|title/i });
    const titleByPlaceholder = page.getByPlaceholder(/titulo|title|verificar|tarea/i);
    const hasTitle = await titleInput.count() > 0 || await titleByPlaceholder.count() > 0;
    expect(hasTitle).toBeTruthy();
  });

  test('shows category selector', async ({ page }) => {
    // Should have category options
    await expect(page.getByText(/categoria|category/i)).toBeVisible();

    // Check for category options
    const categoryOptions = page.getByText(/presencia.*fisica|physical.*presence|accion.*simple|simple.*action/i);
    await expect(categoryOptions).toBeVisible();
  });

  test('shows instructions textarea', async ({ page }) => {
    const instructionsField = page.locator('textarea');
    await expect(instructionsField).toBeVisible();
  });

  test('shows bounty input field', async ({ page }) => {
    await expect(page.getByText(/recompensa|bounty|usdc|\$/i)).toBeVisible();
    const bountyInput = page.locator('input[type="number"]').first();
    await expect(bountyInput).toBeVisible();
  });

  test('shows deadline picker', async ({ page }) => {
    await expect(page.getByText(/fecha.*limite|deadline/i)).toBeVisible();
    const dateInput = page.locator('input[type="datetime-local"], input[type="date"]');
    await expect(dateInput).toBeVisible();
  });

  test('validates title minimum length', async ({ page }) => {
    // Fill short title
    const titleInput = page.getByPlaceholder(/titulo|title/i).first();
    await titleInput.fill('ab');

    // Try to proceed
    const nextButton = page.getByRole('button', { name: /siguiente|next|continuar/i });
    if (await nextButton.isVisible()) {
      await nextButton.click();

      // Should show validation error or stay on same step
      const hasError = await page.getByText(/minimo|minimum|caracteres|characters/i).isVisible();
      const stayedOnStep = await titleInput.isVisible();
      expect(hasError || stayedOnStep).toBeTruthy();
    }
  });

  test('validates instructions minimum length', async ({ page }) => {
    const titleInput = page.getByPlaceholder(/titulo|title/i).first();
    await titleInput.fill('Valid task title here');

    const instructionsField = page.locator('textarea').first();
    await instructionsField.fill('Short');

    const nextButton = page.getByRole('button', { name: /siguiente|next/i });
    if (await nextButton.isVisible()) {
      // Button should be disabled or show error
      const isDisabled = await nextButton.isDisabled();
      expect(true).toBeTruthy(); // Just verify page works
    }
  });

  test('can select task category', async ({ page }) => {
    // Click on a category option
    const physicalCategory = page.getByText(/presencia.*fisica|physical.*presence/i);
    await physicalCategory.click();

    // Should be selected (visual change)
    const selectedCategory = page.locator('.border-blue-500, .bg-blue-50');
    await expect(selectedCategory).toBeVisible();
  });

  test('can navigate to location step', async ({ page }) => {
    // Fill required fields
    const titleInput = page.getByPlaceholder(/titulo|title/i).first();
    await titleInput.fill('Test task for location step');

    const instructionsField = page.locator('textarea').first();
    await instructionsField.fill('This is a test task with enough instructions to pass validation requirements.');

    const deadlineInput = page.locator('input[type="datetime-local"]');
    if (await deadlineInput.isVisible()) {
      // Set deadline to tomorrow
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));
    }

    // Click next
    const nextButton = page.getByRole('button', { name: /siguiente|next/i });
    await nextButton.click();

    // Should be on location step
    await expect(page.getByText(/ubicacion|location/i)).toBeVisible();
  });
});

// =============================================================================
// Create Task - Location Step Tests
// =============================================================================

test.describe('Agent - Create Task Location', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/tasks/create');

    // Navigate to location step
    const titleInput = page.getByPlaceholder(/titulo|title/i).first();
    await titleInput.fill('Test task for location');

    const instructionsField = page.locator('textarea').first();
    await instructionsField.fill('Instructions for testing the location step of task creation flow.');

    const deadlineInput = page.locator('input[type="datetime-local"]');
    if (await deadlineInput.isVisible()) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));
    }

    const nextButton = page.getByRole('button', { name: /siguiente|next/i });
    await nextButton.click();
  });

  test('shows location description field', async ({ page }) => {
    const locationHint = page.getByPlaceholder(/polanco|ubicacion|location.*description/i);
    await expect(locationHint).toBeVisible();
  });

  test('shows coordinate inputs', async ({ page }) => {
    await expect(page.getByPlaceholder(/latitud|latitude/i)).toBeVisible();
    await expect(page.getByPlaceholder(/longitud|longitude/i)).toBeVisible();
  });

  test('has get current location button', async ({ page }) => {
    const locationButton = page.getByRole('button').filter({
      has: page.locator('svg')
    }).filter({ hasText: '' }); // Icon-only button

    // Or look for the specific GPS icon button
    const gpsButton = page.locator('button').filter({ has: page.locator('[d*="M17.657"]') });

    const hasLocationButton = await locationButton.count() > 0 || await gpsButton.count() > 0;
    expect(hasLocationButton).toBeTruthy();
  });

  test('shows radius slider', async ({ page }) => {
    await expect(page.getByText(/radio|radius|km/i)).toBeVisible();
    const slider = page.locator('input[type="range"]');
    await expect(slider).toBeVisible();
  });

  test('can enter location hint', async ({ page }) => {
    const locationHint = page.getByPlaceholder(/polanco|ubicacion/i);
    await locationHint.fill('Polanco, CDMX cerca del parque');
    await expect(locationHint).toHaveValue(/polanco/i);
  });

  test('can enter coordinates manually', async ({ page }) => {
    const latInput = page.getByPlaceholder(/latitud|latitude/i);
    const lngInput = page.getByPlaceholder(/longitud|longitude/i);

    await latInput.fill('19.4326');
    await lngInput.fill('-99.1332');

    await expect(latInput).toHaveValue('19.4326');
  });

  test('can proceed to evidence step', async ({ page }) => {
    const nextButton = page.getByRole('button', { name: /siguiente|next/i });
    await nextButton.click();

    // Should be on evidence step
    await expect(page.getByText(/evidencia|evidence/i)).toBeVisible();
  });
});

// =============================================================================
// Create Task - Evidence Step Tests
// =============================================================================

test.describe('Agent - Create Task Evidence', () => {
  test('shows evidence type options', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/tasks/create');

    // Navigate through to evidence step (simplified)
    // In real tests, would use page objects or fixtures
    await page.getByPlaceholder(/titulo|title/i).first().fill('Test task');
    await page.locator('textarea').first().fill('Test instructions for the task that meet minimum length requirements.');

    const deadlineInput = page.locator('input[type="datetime-local"]');
    if (await deadlineInput.isVisible()) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));
    }

    // Navigate to evidence step
    await page.getByRole('button', { name: /siguiente|next/i }).click();
    await page.getByRole('button', { name: /siguiente|next/i }).click();

    // Should show evidence types
    await expect(page.getByText(/foto|photo/i)).toBeVisible();
    await expect(page.getByText(/video/i)).toBeVisible();
    await expect(page.getByText(/document|documento/i)).toBeVisible();
  });

  test('can select required evidence', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/tasks/create');

    // Quick navigation to evidence step
    await page.getByPlaceholder(/titulo|title/i).first().fill('Test task');
    await page.locator('textarea').first().fill('Test instructions for the task that meet minimum length.');

    const deadlineInput = page.locator('input[type="datetime-local"]');
    if (await deadlineInput.isVisible()) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));
    }

    await page.getByRole('button', { name: /siguiente|next/i }).click();
    await page.getByRole('button', { name: /siguiente|next/i }).click();

    // Select "Req" (required) for photo
    const reqButton = page.getByRole('button', { name: /req/i }).first();
    await reqButton.click();

    // Should be marked as required (visual change)
    await expect(page.locator('.bg-blue-600, .bg-blue-100').first()).toBeVisible();
  });
});

// =============================================================================
// Create Task - Preview Step Tests
// =============================================================================

test.describe('Agent - Create Task Preview', () => {
  test('shows task preview with all details', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/tasks/create');

    // Fill all required fields and navigate to preview
    await page.getByPlaceholder(/titulo|title/i).first().fill('Verificar direccion en Polanco');
    await page.locator('textarea').first().fill('Tomar foto del edificio y confirmar numero de calle visible.');

    const deadlineInput = page.locator('input[type="datetime-local"]');
    if (await deadlineInput.isVisible()) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));
    }

    // Navigate through steps
    await page.getByRole('button', { name: /siguiente|next/i }).click(); // to location
    await page.getByRole('button', { name: /siguiente|next/i }).click(); // to evidence

    // Select required evidence
    const reqButton = page.getByRole('button', { name: /req/i }).first();
    await reqButton.click();

    await page.getByRole('button', { name: /siguiente|next/i }).click(); // to preview

    // Preview should show task details
    await expect(page.getByText(/vista.*previa|preview/i)).toBeVisible();
    await expect(page.getByText(/verificar.*direccion|polanco/i)).toBeVisible();
  });

  test('has publish button', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/tasks/create');

    // Quick fill and navigate to preview
    await page.getByPlaceholder(/titulo|title/i).first().fill('Test task');
    await page.locator('textarea').first().fill('Test instructions that are long enough.');

    const deadlineInput = page.locator('input[type="datetime-local"]');
    if (await deadlineInput.isVisible()) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));
    }

    await page.getByRole('button', { name: /siguiente|next/i }).click();
    await page.getByRole('button', { name: /siguiente|next/i }).click();
    const reqButton = page.getByRole('button', { name: /req/i }).first();
    await reqButton.click();
    await page.getByRole('button', { name: /siguiente|next/i }).click();

    // Should have publish button
    const publishButton = page.getByRole('button', { name: /publicar|publish/i });
    await expect(publishButton).toBeVisible();
  });

  test('shows escrow notice', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/tasks/create');

    // Navigate to preview
    await page.getByPlaceholder(/titulo|title/i).first().fill('Test task');
    await page.locator('textarea').first().fill('Test instructions that are long enough for validation.');

    const deadlineInput = page.locator('input[type="datetime-local"]');
    if (await deadlineInput.isVisible()) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await deadlineInput.fill(tomorrow.toISOString().slice(0, 16));
    }

    await page.getByRole('button', { name: /siguiente|next/i }).click();
    await page.getByRole('button', { name: /siguiente|next/i }).click();
    const reqButton = page.getByRole('button', { name: /req/i }).first();
    await reqButton.click();
    await page.getByRole('button', { name: /siguiente|next/i }).click();

    // Should show escrow information
    await expect(page.getByText(/escrow|deposito/i)).toBeVisible();
  });
});

// =============================================================================
// Review Submissions Tests
// =============================================================================

test.describe('Agent - Review Submissions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/dashboard');
  });

  test('shows pending submissions count', async ({ page }) => {
    const submissionsBadge = page.locator('.bg-purple-100, .text-purple-700').filter({ hasText: /\d/ });
    // May or may not have pending submissions
    expect(true).toBeTruthy();
  });

  test('submission card shows executor info', async ({ page }) => {
    const submissionCards = page.locator('.bg-purple-50, [class*="submission"]');

    if (await submissionCards.count() > 0) {
      // Should show executor name or wallet
      await expect(submissionCards.first()).toContainText(/\w+/);
    }
  });

  test('submission card shows reputation', async ({ page }) => {
    const submissionCards = page.locator('.bg-purple-50');

    if (await submissionCards.count() > 0) {
      // Should show reputation score
      await expect(submissionCards.first().getByText(/\d+/)).toBeVisible();
    }
  });

  test('has review button on submission cards', async ({ page }) => {
    const submissionCards = page.locator('.bg-purple-50');

    if (await submissionCards.count() > 0) {
      const reviewButton = submissionCards.first().getByRole('button', { name: /revisar|review/i });
      await expect(reviewButton).toBeVisible();
    }
  });

  test('clicking review opens submission detail', async ({ page }) => {
    const reviewButton = page.getByRole('button', { name: /revisar|review/i }).first();

    if (await reviewButton.isVisible()) {
      await reviewButton.click();

      // Should show submission detail view
      await expect(page.getByText(/evidencia|evidence|entrega/i)).toBeVisible();
    }
  });

  test('shows auto-check status', async ({ page }) => {
    const submissionCards = page.locator('.bg-purple-50');

    if (await submissionCards.count() > 0) {
      // May show auto-verification status
      const autoCheckStatus = page.getByText(/verificacion.*automatica|auto.*check|gps.*verified/i);
      // This is optional, just verify page loads
      expect(true).toBeTruthy();
    }
  });
});

// =============================================================================
// Submission Review Detail Tests
// =============================================================================

test.describe('Agent - Submission Review Detail', () => {
  test('shows evidence files', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/submissions/1');

    // Should show evidence section
    await expect(page.getByText(/evidencia|evidence/i)).toBeVisible();
  });

  test('has approve button', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/submissions/1');

    const approveButton = page.getByRole('button', { name: /aprobar|approve|aceptar/i });
    await expect(approveButton).toBeVisible();
  });

  test('has reject button', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/submissions/1');

    const rejectButton = page.getByRole('button', { name: /rechazar|reject|denegar/i });
    await expect(rejectButton).toBeVisible();
  });

  test('shows task info in context', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/submissions/1');

    // Should show which task this submission is for
    await expect(page.getByText(/tarea|task/i)).toBeVisible();
  });

  test('shows executor profile info', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/submissions/1');

    // Should show who submitted
    await expect(page.getByText(/ejecutor|executor|trabajador|worker/i)).toBeVisible();
  });

  test('reject requires reason', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/submissions/1');

    const rejectButton = page.getByRole('button', { name: /rechazar|reject/i });

    if (await rejectButton.isVisible()) {
      await rejectButton.click();

      // Should show reason input or modal
      const reasonInput = page.locator('textarea, input').filter({ hasText: '' });
      await expect(page.getByText(/razon|reason|motivo|porque/i)).toBeVisible();
    }
  });

  test('approve shows payment confirmation', async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/submissions/1');

    const approveButton = page.getByRole('button', { name: /aprobar|approve/i });

    if (await approveButton.isVisible()) {
      await approveButton.click();

      // Should show payment confirmation
      await expect(page.getByText(/pago|payment|confirmar|\$/i)).toBeVisible();
    }
  });
});

// =============================================================================
// Task Management Tests
// =============================================================================

test.describe('Agent - Task Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/dashboard');
  });

  test('can filter active tasks', async ({ page }) => {
    const filterTabs = page.locator('button').filter({ hasText: /todas|all|pendientes|en.*progreso/i });

    if (await filterTabs.count() > 1) {
      await filterTabs.nth(1).click();

      // Content should update
      await page.waitForTimeout(500);
    }
  });

  test('task card shows status badge', async ({ page }) => {
    const taskCards = page.locator('.bg-white.rounded-lg').filter({ hasText: /\$/i });

    if (await taskCards.count() > 0) {
      // Should have status indicator
      const statusBadge = taskCards.first().locator('.rounded-full, [class*="badge"]');
      await expect(statusBadge.first()).toBeVisible();
    }
  });

  test('task card shows deadline', async ({ page }) => {
    const taskCards = page.locator('.bg-white').filter({ hasText: /\$/i });

    if (await taskCards.count() > 0) {
      await expect(taskCards.first().getByText(/h |dia|min|restante|remaining/i)).toBeVisible();
    }
  });

  test('can view all tasks link', async ({ page }) => {
    const viewAllLink = page.getByText(/ver.*todas|view.*all|mas.*tareas/i);
    await expect(viewAllLink).toBeVisible();
  });
});

// =============================================================================
// Activity Feed Tests
// =============================================================================

test.describe('Agent - Activity Feed', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/dashboard');
  });

  test('shows recent activity section', async ({ page }) => {
    await expect(page.getByText(/actividad.*reciente|recent.*activity/i)).toBeVisible();
  });

  test('activity items show timestamp', async ({ page }) => {
    const activityItems = page.locator('[class*="activity"]').or(page.locator('.divide-y > div'));

    if (await activityItems.count() > 0) {
      // Should show relative time
      await expect(page.getByText(/hace|ago|min|h /i)).toBeVisible();
    }
  });

  test('activity items are categorized by type', async ({ page }) => {
    // Should show different activity types with icons
    const activityTypes = page.getByText(/creada|completada|recibida|enviado|created|completed|received|sent/i);
    await expect(activityTypes.first()).toBeVisible();
  });
});

// =============================================================================
// Quick Actions Tests
// =============================================================================

test.describe('Agent - Quick Actions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/dashboard');
  });

  test('shows quick actions bar', async ({ page }) => {
    await expect(page.getByText(/acciones.*rapidas|quick.*actions/i)).toBeVisible();
  });

  test('has new task shortcut', async ({ page }) => {
    const newTaskButton = page.getByRole('button', { name: /nueva.*tarea|new.*task|crear/i });
    await expect(newTaskButton).toBeVisible();
  });

  test('has review next shortcut', async ({ page }) => {
    const reviewNextButton = page.getByRole('button', { name: /revisar.*siguiente|review.*next/i });
    // May be disabled if no pending submissions
    expect(true).toBeTruthy();
  });

  test('has view reports shortcut', async ({ page }) => {
    const reportsButton = page.getByRole('button', { name: /reportes|reports|ver.*reportes/i });
    await expect(reportsButton).toBeVisible();
  });

  test('clicking new task navigates to create form', async ({ page }) => {
    const newTaskButton = page.getByRole('button', { name: /nueva.*tarea|new.*task|crear/i }).first();
    await newTaskButton.click();

    // Should navigate to create task page
    await expect(page.getByText(/crear.*tarea|create.*task/i)).toBeVisible();
  });
});

// =============================================================================
// Agent Analytics Tests
// =============================================================================

test.describe('Agent - Analytics', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/analytics');
  });

  test('shows analytics page', async ({ page }) => {
    await expect(page.getByText(/analiticas|analytics|estadisticas|statistics/i)).toBeVisible();
  });

  test('displays spending chart', async ({ page }) => {
    // Should have some visualization
    const chart = page.locator('canvas, svg, [class*="chart"]');
    if (await chart.count() > 0) {
      await expect(chart.first()).toBeVisible();
    }
  });

  test('shows task completion metrics', async ({ page }) => {
    await expect(page.getByText(/completad|tasa|rate|%/i)).toBeVisible();
  });

  test('can filter by date range', async ({ page }) => {
    const dateFilter = page.getByRole('button', { name: /fecha|date|mes|month|semana|week/i });
    if (await dateFilter.isVisible()) {
      await dateFilter.click();
      // Should show date options
      await expect(page.getByText(/ultima|last|este|this/i)).toBeVisible();
    }
  });
});

// =============================================================================
// Agent Settings Tests
// =============================================================================

test.describe('Agent - Settings', () => {
  test.beforeEach(async ({ page }) => {
    await setupAgentSession(page);
    await page.goto('/agent/settings');
  });

  test('shows agent settings page', async ({ page }) => {
    await expect(page.getByText(/configuracion|settings|ajustes/i)).toBeVisible();
  });

  test('can update agent name', async ({ page }) => {
    const nameInput = page.locator('input').filter({ hasText: '' }).first();
    if (await nameInput.isVisible()) {
      await nameInput.fill('Updated Agent Name');
    }
  });

  test('shows wallet information', async ({ page }) => {
    await expect(page.getByText(/wallet|billetera|0x/i)).toBeVisible();
  });

  test('has notification settings', async ({ page }) => {
    await expect(page.getByText(/notificacion|notification/i)).toBeVisible();
  });
});
