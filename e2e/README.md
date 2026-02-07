# Execution Market E2E Tests

End-to-end tests for the Execution Market application using Playwright.

> **Note**: E2E tests are **disabled in CI** as of 2026-02-07. The auth setup references `[data-testid="login-form"]` which doesn't exist since the app uses Dynamic.xyz for authentication. Tests run fine locally against the dev server. Re-enable in CI after updating `fixtures/auth.ts` for Dynamic.xyz.

## Setup

```bash
cd e2e
npm install
npm run install-browsers
```

## Running Tests

```bash
# Run all tests (headless)
npm test

# Run with browser visible
npm run test:headed

# Run with Playwright UI
npm run test:ui

# Run in debug mode
npm run test:debug

# Run specific test file
npm run test:auth
npm run test:tasks
npm run test:agent
npm run test:evidence

# Run on specific browser
npm run test:chromium
npm run test:firefox
npm run test:webkit
```

## Test Structure

```
e2e/
├── playwright.config.ts    # Playwright configuration
├── package.json           # Dependencies and scripts
├── tsconfig.json          # TypeScript config
├── fixtures/              # Test helpers and mocks
│   ├── index.ts          # Central export
│   ├── auth.ts           # Authentication helpers
│   ├── mocks.ts          # API mocks and test data
│   └── tasks.ts          # Task manipulation helpers
└── tests/                 # Test files
    ├── auth.setup.ts     # Auth state setup
    ├── auth.spec.ts      # Authentication tests
    ├── tasks.spec.ts     # Task browsing tests
    ├── agent.spec.ts     # Agent dashboard tests
    └── evidence.spec.ts  # Evidence submission tests
```

## Test Files

### auth.spec.ts
- Landing page loads
- Login modal functionality
- Wallet connection (mocked MetaMask)
- Email/password login
- Logout
- Session persistence

### tasks.spec.ts
- Task list loading
- Task filtering by category
- Task detail view
- Task application flow
- Application status display

### agent.spec.ts
- Agent dashboard
- Task creation
- Submission review
- Approval/rejection workflows

### evidence.spec.ts
- Camera capture (mocked)
- Location capture (mocked geolocation)
- File upload
- Evidence submission
- Error handling

## Fixtures

### mocks.ts
Contains mock data and API interceptors for:
- Supabase REST API (tasks, submissions, applications)
- Supabase Auth
- Wallet provider (MetaMask)
- Geolocation API
- Camera/Media devices

### auth.ts
Authentication helpers:
- `loginWithEmail(page, user)` - Login via email
- `loginWithWallet(page)` - Login via wallet
- `logout(page)` - Logout
- `isLoggedIn(page)` - Check login state

### tasks.ts
Task manipulation helpers:
- `createTaskViaUI(page, input)` - Create task
- `applyToTask(page, taskId)` - Apply to task
- `approveSubmission(page, taskId, subId)` - Approve submission
- `filterByCategory(page, category)` - Filter tasks

## Configuration

### Base URL
Default: `http://localhost:3000`

Override with environment variable:
```bash
BASE_URL=http://localhost:5173 npm test
```

### Browsers
Tests run on:
- Chromium (default)
- Firefox
- WebKit (Safari)
- Mobile Chrome (Pixel 5)
- Mobile Safari (iPhone 12)

### Artifacts
- Screenshots on failure: `test-results/`
- Video on retry: `test-results/`
- HTML report: `playwright-report/`

View report:
```bash
npm run report
```

## Writing Tests

### Basic Test

```typescript
import { test, expect } from '@playwright/test'
import { setupMocks } from '../fixtures/mocks'
import { loginWithEmail, TEST_EXECUTOR } from '../fixtures/auth'

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page)
    await loginWithEmail(page, TEST_EXECUTOR)
  })

  test('should do something', async ({ page }) => {
    await page.goto('/my-page')
    await expect(page.locator('h1')).toContainText('Expected')
  })
})
```

### Using Test Data

```typescript
import { mockTasks, mockExecutor } from '../fixtures/mocks'

test('uses mock data', async ({ page }) => {
  const task = mockTasks[0]
  await page.goto(`/tasks/${task.id}`)
  await expect(page.locator('h1')).toContainText(task.title)
})
```

### Mocking API Errors

```typescript
test('handles API error', async ({ page }) => {
  await page.route('**/rest/v1/tasks*', async (route) => {
    await route.fulfill({
      status: 500,
      body: JSON.stringify({ error: 'Server error' }),
    })
  })

  await page.goto('/tasks')
  await expect(page.locator('[data-testid="error-state"]')).toBeVisible()
})
```

## Data-TestID Convention

Tests use `data-testid` attributes for selectors:

```html
<button data-testid="login-button">Login</button>
<div data-testid="task-card-{id}">...</div>
<input data-testid="email-input" />
```

Common patterns:
- `{feature}-{element}`: `login-button`, `task-title`
- `{feature}-{element}-{id}`: `task-card-001`
- `{feature}-{state}`: `loading-skeleton`, `error-state`

## CI Integration

E2E tests are currently **disabled in CI** (`ci.yml` and `deploy.yml`). To re-enable:

1. Update `fixtures/auth.ts` to work with Dynamic.xyz (replace `login-form` selectors)
2. Add the E2E job back to `.github/workflows/ci.yml`
3. Ensure dashboard dependencies are installed before E2E (Playwright's `webServer` starts Vite)

When running in CI, the config automatically:
- Retries failed tests 2 times
- Uses a single worker
- Generates JSON + HTML reports

Example GitHub Actions job:
```yaml
e2e-tests:
  name: E2E Tests
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "20"
        cache: 'npm'
        cache-dependency-path: dashboard/package-lock.json
    - run: npm ci
      working-directory: dashboard
    - run: npm install
      working-directory: e2e
    - run: npx playwright install --with-deps chromium
      working-directory: e2e
    - run: npx playwright test --project=chromium
      working-directory: e2e
      env:
        CI: true
```
