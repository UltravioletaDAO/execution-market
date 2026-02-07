/**
 * Debug test for production - captures console errors and network failures
 */
import { test, expect } from '@playwright/test';

test.describe('Production Debug', () => {
  test('check landing page for errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    const networkErrors: string[] = [];

    // Capture console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(`[Console Error] ${msg.text()}`);
      }
    });

    // Capture network failures
    page.on('requestfailed', (request) => {
      networkErrors.push(`[Network Failed] ${request.url()} - ${request.failure()?.errorText}`);
    });

    // Capture responses
    page.on('response', async (response) => {
      if (response.status() >= 400) {
        const body = await response.text().catch(() => '');
        networkErrors.push(`[HTTP ${response.status()}] ${response.url()} - ${body.slice(0, 200)}`);
      }
    });

    // Go to production
    await page.goto('https://execution.market', { waitUntil: 'networkidle' });

    // Wait for page to stabilize
    await page.waitForTimeout(3000);

    // Log what we found
    console.log('\n=== CONSOLE ERRORS ===');
    consoleErrors.forEach(e => console.log(e));
    console.log('\n=== NETWORK ERRORS ===');
    networkErrors.forEach(e => console.log(e));

    // Take screenshot
    await page.screenshot({ path: 'debug-landing.png', fullPage: true });

    // Check for Dynamic.xyz widget
    const dynamicWidget = page.locator('[data-dynamic-widget]');
    const hasDynamic = await dynamicWidget.count() > 0;
    console.log('\n=== DYNAMIC WIDGET ===');
    console.log(`Dynamic widget found: ${hasDynamic}`);

    // Check auth state from localStorage
    const authState = await page.evaluate(() => {
      const keys = Object.keys(localStorage).filter(k =>
        k.includes('dynamic') || k.includes('em_') || k.includes('supabase')
      );
      const result: Record<string, string> = {};
      keys.forEach(k => result[k] = localStorage.getItem(k) || '');
      return result;
    });
    console.log('\n=== LOCALSTORAGE AUTH ===');
    console.log(JSON.stringify(authState, null, 2));
  });

  test('simulate wallet connection and check profile', async ({ page }) => {
    const consoleMessages: string[] = [];
    const networkRequests: { url: string; status: number; body?: string }[] = [];

    // Capture ALL console messages
    page.on('console', (msg) => {
      consoleMessages.push(`[${msg.type()}] ${msg.text()}`);
    });

    // Capture network responses
    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('supabase') || url.includes('execution.market')) {
        const body = await response.text().catch(() => '');
        networkRequests.push({
          url: url.split('?')[0],
          status: response.status(),
          body: body.slice(0, 500)
        });
      }
    });

    // Go to production
    await page.goto('https://execution.market', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Look for connect wallet button
    const connectButtons = page.getByRole('button').filter({ hasText: /connect|wallet|iniciar|login/i });
    const connectButtonCount = await connectButtons.count();
    console.log(`\n=== CONNECT BUTTONS FOUND: ${connectButtonCount} ===`);

    for (let i = 0; i < Math.min(connectButtonCount, 5); i++) {
      const text = await connectButtons.nth(i).textContent();
      console.log(`Button ${i}: "${text}"`);
    }

    // Take screenshot of landing
    await page.screenshot({ path: 'debug-landing-buttons.png', fullPage: true });

    // Try to navigate to profile directly
    console.log('\n=== NAVIGATING TO /profile ===');
    await page.goto('https://execution.market/profile', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Check page content
    const pageContent = await page.content();
    const hasLoading = pageContent.includes('Cargando') || pageContent.includes('loading');
    const hasError = pageContent.includes('error') || pageContent.includes('Error');
    console.log(`Page has loading text: ${hasLoading}`);
    console.log(`Page has error text: ${hasError}`);

    // Take screenshot
    await page.screenshot({ path: 'debug-profile.png', fullPage: true });

    // Log console messages
    console.log('\n=== CONSOLE MESSAGES ===');
    consoleMessages.slice(-30).forEach(m => console.log(m));

    // Log network requests
    console.log('\n=== NETWORK REQUESTS ===');
    networkRequests.forEach(r => {
      console.log(`[${r.status}] ${r.url}`);
      if (r.status >= 400) {
        console.log(`  Body: ${r.body}`);
      }
    });
  });

  test('check supabase connection directly', async ({ page }) => {
    await page.goto('https://execution.market', { waitUntil: 'networkidle' });

    // Test Supabase connection from browser
    const result = await page.evaluate(async () => {
      // @ts-expect-error - accessing global supabase client
      const supabaseUrl = 'https://puyhpytmtkyevnxffksl.supabase.co';
      const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1eWhweXRtdGt5ZXZueGZma3NsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg2NzgzOTMsImV4cCI6MjA4NDI1NDM5M30.R4Sf4SwDo-5yRhRMOazQ-4Jn972YLT7lYunjdqiGjaU';

      try {
        // Test tasks query
        const tasksRes = await fetch(`${supabaseUrl}/rest/v1/tasks?select=id,title,status&limit=5`, {
          headers: {
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`
          }
        });
        const tasks = await tasksRes.json();

        // Test executors query
        const execRes = await fetch(`${supabaseUrl}/rest/v1/executors?select=id,wallet_address,display_name&limit=5`, {
          headers: {
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`
          }
        });
        const executors = await execRes.json();

        return {
          tasksStatus: tasksRes.status,
          tasksCount: Array.isArray(tasks) ? tasks.length : 'error',
          tasks: tasks,
          executorsStatus: execRes.status,
          executorsCount: Array.isArray(executors) ? executors.length : 'error',
          executors: executors
        };
      } catch (e) {
        return { error: String(e) };
      }
    });

    console.log('\n=== SUPABASE DIRECT TEST ===');
    console.log(JSON.stringify(result, null, 2));
  });
});
