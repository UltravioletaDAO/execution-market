# Execution Market E2E Tests

Comprehensive end-to-end tests for the Execution Market platform using Playwright.

## Test Coverage

### Worker Flow (`worker-flow.spec.ts`)
- Onboarding & Authentication
  - Language selection
  - Wallet connection (manual, MetaMask, WalletConnect)
  - Email signup
  - Profile setup
- Task Discovery
  - Browse available tasks
  - Filter by category
  - Filter by location
  - View task details
- Task Acceptance
  - Apply to tasks
  - Reputation requirements validation
  - Prevent duplicate acceptance
- Evidence Submission
  - Photo upload
  - GPS/EXIF verification
  - Required evidence validation
  - Submission confirmation
- Payment & Earnings
  - View payment status
  - Payment history
  - Reputation updates
  - Withdrawal initiation
- Profile Management
  - Update display name
  - Change language preference

### Agent Flow (`agent-flow.spec.ts`)
- API Authentication
  - Valid/invalid API keys
  - Agent profile retrieval
- Task Creation
  - Simple tasks
  - Location-based tasks
  - Multi-evidence tasks
  - Validation (required fields, bounty minimum, deadline)
- Dashboard Management
  - Task list with filters
  - View task details
  - Cancel tasks
- Submission Review
  - View pending submissions
  - Evidence viewer
  - Auto-check results
- Approval/Rejection
  - Approve with notes
  - Reject with reason
  - Reason validation
- Payment Authorization
  - Trigger payments
  - Escrow balance
- Analytics
  - Task statistics
  - Completion rates
  - Spending summary
  - Activity feed

### Dispute Flow (`dispute-flow.spec.ts`)
- Dispute Creation
  - Worker dispute rejection
  - Reason requirement
  - Timeline display
- Dispute Listing
  - Filter by status
  - View details
  - Vote progress
- Evidence Management
  - Add additional evidence
  - View both parties' evidence
- Validator Voting
  - Vote interface
  - Vote for worker/agent
  - Stake requirements
  - Prevent double voting
- Resolution
  - Quorum detection
  - Payment release
  - Stake return
- Appeal Process
  - Appeal option
  - Cost display
  - Gnosis Safe escalation
  - Deadline tracking

### Accessibility & Performance (`accessibility-performance.spec.ts`)
- Accessibility
  - Heading hierarchy
  - Alt text for images
  - Form labels
  - Keyboard navigation
  - Focus indicators
  - Color contrast
  - Screen reader support
  - Reduced motion support
- Performance
  - Initial load time
  - Task list rendering
  - Navigation speed
  - Memory usage
  - Slow 3G behavior
  - Offline handling
- Mobile Experience
  - Responsive layout
  - Touch targets
  - No horizontal scroll
- Internationalization
  - Spanish/English toggle
  - Language persistence
  - Currency/date formatting

## Setup

```bash
# Install dependencies
cd tests/e2e
npm install

# Install Playwright browsers
npx playwright install
```

## Running Tests

```bash
# Run all tests
npm test

# Run with UI mode (recommended for debugging)
npm run test:ui

# Run specific test file
npm run test:worker
npm run test:agent
npm run test:dispute
npm run test:a11y

# Run mobile tests only
npm run test:mobile

# Run in debug mode
npm run test:debug

# View test report
npm run report
```

## Configuration

The tests are configured in `playwright.config.ts` with:

- **Desktop browsers**: Chromium, Firefox, WebKit
- **Mobile devices**: Pixel 5, iPhone 13, low-end Android
- **Locale**: es-MX (Mexico)
- **Geolocation**: Mexico City (19.4326, -99.1332)

### Environment Variables

```bash
# Override base URL
BASE_URL=http://localhost:3000

# API URL for agent tests
API_URL=http://localhost:3000/api

# Cleanup test data after run
CLEANUP_TEST_DATA=true

# Test agent API key
TEST_AGENT_API_KEY=your_key_here
```

## Test Data

Test fixtures are defined in `fixtures/test-fixtures.ts`:

- `TEST_USERS` - Worker, agent, and validator test accounts
- `TEST_LOCATIONS` - Mexico City, Bogota, Lima coordinates
- `TASK_TEMPLATES` - Common task configurations

## Writing New Tests

```typescript
import { test, expect } from './fixtures/test-fixtures';

test.describe('My Feature', () => {
  test('should do something', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Execution Market')).toBeVisible();
  });
});
```

### Custom Fixtures

- `workerPage` - Page with worker context
- `agentPage` - Page with agent API key
- `validatorPage` - Page with validator stake
- `authenticatedWorker` - Pre-authenticated worker session

### Helper Functions

- `waitForNetworkIdle(page)` - Wait for network to settle
- `generateTestWallet()` - Generate random wallet address
- `createDeadline(hours)` - Create future deadline
- `mockGeolocation(page, coords)` - Set mock GPS location
- `mockPhotoUpload(page, selector)` - Upload test image
- `waitForToast(page, text)` - Wait for notification
- `clearAuthState(page)` - Clear auth storage

## CI/CD Integration

For GitHub Actions:

```yaml
- name: Run E2E Tests
  run: |
    cd tests/e2e
    npm ci
    npx playwright install --with-deps
    npm test
  env:
    CI: true
    BASE_URL: http://localhost:3000
```

## Troubleshooting

### Tests fail with "App not accessible"
Make sure the Execution Market dashboard is running:
```bash
cd dashboard
npm run dev
```

### Flaky tests on CI
Increase timeouts in `playwright.config.ts` or add explicit waits.

### Browser not installed
```bash
npx playwright install chromium
```

## Architecture Notes

Tests are designed to be:
- **Resilient**: Handle missing UI elements gracefully
- **Realistic**: Simulate actual LATAM user scenarios
- **Fast**: Run in parallel where possible
- **Maintainable**: Use data-testid attributes and semantic selectors
