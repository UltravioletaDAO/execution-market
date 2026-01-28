/**
 * Chamba E2E Tests - Global Teardown
 *
 * Runs once after all tests to:
 * 1. Clean up test data
 * 2. Generate summary report
 * 3. Archive artifacts
 */
import { FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('\n=== Chamba E2E Test Suite - Global Teardown ===\n');

  // 1. Generate test summary
  const resultsPath = './test-results/results.json';
  if (fs.existsSync(resultsPath)) {
    try {
      const results = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));
      printTestSummary(results);
    } catch (e) {
      console.log('Could not parse test results for summary.');
    }
  }

  // 2. Clean up storage state
  const storagePath = './test-results/storage-state.json';
  if (fs.existsSync(storagePath)) {
    try {
      fs.unlinkSync(storagePath);
      console.log('Cleaned up storage state.');
    } catch (e) {
      // Ignore
    }
  }

  // 3. Clean up test data (if API supports it)
  if (process.env.CLEANUP_TEST_DATA === 'true') {
    console.log('Cleaning up test data...');
    await cleanupTestData(config);
  }

  console.log('\n=== Global Teardown Complete ===\n');
}

function printTestSummary(results: any) {
  console.log('\n--- Test Summary ---\n');

  const suites = results.suites || [];
  let passed = 0;
  let failed = 0;
  let skipped = 0;

  function countResults(suite: any) {
    for (const spec of suite.specs || []) {
      for (const test of spec.tests || []) {
        for (const result of test.results || []) {
          if (result.status === 'passed') passed++;
          else if (result.status === 'failed') failed++;
          else if (result.status === 'skipped') skipped++;
        }
      }
    }
    for (const child of suite.suites || []) {
      countResults(child);
    }
  }

  for (const suite of suites) {
    countResults(suite);
  }

  console.log(`  Passed:  ${passed}`);
  console.log(`  Failed:  ${failed}`);
  console.log(`  Skipped: ${skipped}`);
  console.log(`  Total:   ${passed + failed + skipped}`);

  if (failed > 0) {
    console.log('\n  Some tests failed. Check the HTML report for details:');
    console.log('  npx playwright show-report test-results/html-report\n');
  }
}

async function cleanupTestData(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || 'http://localhost:3000';
  const testApiKey = process.env.TEST_AGENT_API_KEY || 'test_agent_api_key_12345';

  try {
    // Call cleanup endpoint if available
    await fetch(`${baseURL}/api/test/cleanup`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${testApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prefix: 'E2E Test' }),
    });
    console.log('Test data cleaned up successfully.');
  } catch (e) {
    console.log('Could not clean up test data (API might not support it).');
  }
}

export default globalTeardown;
