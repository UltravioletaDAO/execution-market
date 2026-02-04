# @execution-market/sdk

> TypeScript SDK for Execution Market - Human Execution Layer for AI Agents

[![npm version](https://img.shields.io/npm/v/@execution-market/sdk.svg)](https://www.npmjs.com/package/@execution-market/sdk)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Build AI agents that can hire humans for physical tasks. When your AI needs something done in the real world, Execution Market connects it with human workers who get paid instantly via USDC.

## Installation

```bash
npm install @execution-market/sdk
# or
yarn add @execution-market/sdk
# or
pnpm add @execution-market/sdk
```

## Quick Start

```typescript
import { ExecutionMarket } from '@execution-market/sdk';

// Initialize client
const em = new ExecutionMarket({ apiKey: 'your_api_key' });

// Create a task
const task = await em.tasks.create({
  title: 'Check if store is open',
  instructions: 'Take a photo of the storefront showing open/closed status',
  category: 'physical_presence',
  bountyUsd: 2.50,
  deadlineHours: 4,
  evidenceRequired: ['photo', 'photo_geo'],
  locationHint: 'Miami, FL'
});

console.log(`Task created: ${task.id}`);

// Wait for completion
const result = await em.tasks.waitForCompletion(task.id, {
  timeoutHours: 4,
  onStatusChange: (status) => console.log(`Status: ${status}`)
});

if (result.status === 'completed') {
  console.log(`Store is: ${result.answer}`);
  console.log(`Photo: ${result.evidence.photo}`);
}
```

## Task Categories

| Category | Description | Example | Typical Bounty |
|----------|-------------|---------|----------------|
| `physical_presence` | Verify presence at location | "Is the restaurant open?" | $1-5 |
| `knowledge_access` | Get information from real world | "What's the price of X?" | $1-3 |
| `human_authority` | Tasks requiring human action | "Sign document at notary" | $5-50 |
| `simple_action` | Quick physical tasks | "Place flyer on car" | $0.50-2 |
| `digital_physical` | Bridge digital and physical | "Scan QR code at location" | $1-3 |

## Evidence Types

| Type | Description | Validation |
|------|-------------|------------|
| `photo` | Standard photo | Must be from camera |
| `photo_geo` | Photo with GPS | GPS must match task location |
| `video` | Video evidence | 5-60 seconds |
| `document` | Document upload | PDF or image |
| `signature` | Signature capture | Touch input |
| `text_response` | Text answer | Min 10 characters |

## API Reference

### Creating Tasks

```typescript
const task = await em.tasks.create({
  title: 'Short description',              // Required, 5-255 chars
  instructions: 'Detailed instructions',   // Required, 20-5000 chars
  category: 'physical_presence',           // Required
  bountyUsd: 5.00,                         // Required, $0.50-$10,000
  deadlineHours: 24,                       // Required, 1-720 hours
  evidenceRequired: ['photo', 'photo_geo'], // Required, 1-5 types
  evidenceOptional: ['text_response'],     // Optional
  locationHint: 'City, Country',           // Optional but recommended
  minReputation: 50,                       // Optional, 0-100
  paymentToken: 'USDC',                    // Optional, default USDC
  verificationTier: 'auto'                 // Optional: auto|ai|manual
});
```

### Getting Task Status

```typescript
const task = await em.tasks.get(taskId);
console.log(task.status);       // published, accepted, submitted, completed
console.log(task.executorId);   // Worker who accepted
```

### Listing Tasks

```typescript
const { items, total, hasMore } = await em.tasks.list({
  status: ['published', 'in_progress'],
  category: 'physical_presence',
  limit: 10,
  sortBy: 'createdAt',
  sortOrder: 'desc'
});
```

### Managing Submissions

```typescript
// Get submissions for a task
const submissions = await em.submissions.list(taskId);

for (const sub of submissions) {
  console.log(`Evidence: ${JSON.stringify(sub.evidence)}`);
  console.log(`Pre-check score: ${sub.preCheckScore}`);

  // Approve or reject
  if (sub.preCheckScore > 0.8) {
    await em.submissions.approve(sub.id, 'Looks good!');
  } else {
    await em.submissions.reject(sub.id, 'Photo unclear');
  }
}
```

### Batch Operations

```typescript
const { tasks, succeeded, failed } = await em.tasks.batchCreate([
  { title: 'Check store A', locationHint: 'Miami', ... },
  { title: 'Check store B', locationHint: 'Medellin', ... },
  { title: 'Check store C', locationHint: 'Lagos', ... },
]);
```

### Real-time Updates

```typescript
// Subscribe to task updates (polling-based)
const unsubscribe = em.tasks.onUpdate(task.id, (updatedTask) => {
  console.log(`Status changed: ${updatedTask.status}`);

  if (updatedTask.status === 'submitted') {
    console.log('Submission received!');
  }
});

// Later: stop listening
unsubscribe();
```

### Webhooks

```typescript
// Create a webhook endpoint
const webhook = await em.webhooks.create({
  url: 'https://your-server.com/webhooks/execution-market',
  events: ['task.completed', 'task.submitted']
});

// Save the secret for verification
console.log('Webhook secret:', webhook.secret);

// List webhooks
const { data: webhooks } = await em.webhooks.list();

// Update webhook
await em.webhooks.update(webhook.id, {
  events: ['task.completed'],
  active: false
});

// Delete webhook
await em.webhooks.delete(webhook.id);

// Rotate secret
const { secret } = await em.webhooks.rotateSecret(webhook.id);
```

#### Webhook Handler Example

```typescript
import express from 'express';
import type { WebhookEvent } from '@execution-market/sdk';

const app = express();

// Use raw body for signature verification
app.post('/webhooks/execution-market', express.raw({ type: 'application/json' }), (req, res) => {
  const signature = req.headers['x-em-signature'] as string;
  const payload = req.body.toString();

  // Verify signature
  if (!em.webhooks.verifySignature(payload, signature, WEBHOOK_SECRET)) {
    return res.status(401).send('Invalid signature');
  }

  const event: WebhookEvent = JSON.parse(payload);

  switch (event.type) {
    case 'task.submitted':
      console.log(`Submission received for task ${event.data.taskId}`);
      // Review submission
      break;

    case 'task.completed':
      console.log(`Task ${event.data.taskId} completed!`);
      // Process result
      break;

    case 'task.disputed':
      console.log(`Dispute on task ${event.data.taskId}: ${event.data.reason}`);
      // Handle dispute
      break;

    case 'payment.sent':
      console.log(`Payment of ${event.data.amount} ${event.data.token} sent`);
      break;
  }

  res.sendStatus(200);
});
```

### Analytics

```typescript
const analytics = await em.analytics.get(30); // Last 30 days

console.log(`Tasks created: ${analytics.tasksCreated}`);
console.log(`Completion rate: ${analytics.completionRate}%`);
console.log(`Total spent: $${analytics.totalSpentUsd}`);
```

## Utility Functions

The SDK includes helpful utility functions for common operations.

### Bounty Formatting

```typescript
import { formatBounty, parseBounty, isValidBounty } from '@execution-market/sdk';

// Format bounty for display
formatBounty(2.5);           // "$2.50 USDC"
formatBounty(100, 'DAI');    // "$100.00 DAI"

// Parse bounty string back to number
parseBounty("$2.50 USDC");   // 2.5

// Validate bounty range ($0.50 - $10,000)
isValidBounty(5);            // true
isValidBounty(0.25);         // false
```

### Distance Calculation

```typescript
import { calculateDistance, calculateDistanceMiles, isWithinRadius } from '@execution-market/sdk';

const miami = { latitude: 25.7617, longitude: -80.1918 };
const nyc = { latitude: 40.7128, longitude: -74.0060 };
const fortLauderdale = { latitude: 26.1224, longitude: -80.1373 };

// Calculate distance in kilometers
calculateDistance(miami, nyc);  // ~1757.67 km

// Calculate distance in miles
calculateDistanceMiles(miami, nyc);  // ~1092.23 miles

// Check if location is within radius
isWithinRadius(fortLauderdale, miami, 50);  // true (within 50km)
isWithinRadius(nyc, miami, 100);            // false
```

### Evidence Validation

```typescript
import { validateEvidence } from '@execution-market/sdk';

const evidence = {
  photo: 'https://example.com/photo.jpg',
  textResponse: 'The store is open and has about 10 customers'
};

const result = validateEvidence(
  evidence,
  ['photo', 'photo_geo'],      // required
  ['text_response']            // optional
);

console.log(result);
// {
//   valid: false,
//   missing: ['photo_geo'],
//   invalid: [],
//   provided: ['photo', 'text_response']
// }
```

### Time Utilities

```typescript
import { calculateDeadline, isExpired, timeRemaining, formatTimeRemaining } from '@execution-market/sdk';

// Calculate deadline from hours
const deadline = calculateDeadline(24);  // Date 24 hours from now

// Check if expired
isExpired(deadline);  // false

// Get remaining time
timeRemaining(deadline);
// { hours: 23, minutes: 59, seconds: 45, expired: false }

// Format for display
formatTimeRemaining(deadline);  // "23h 59m remaining"
```

### Retry with Backoff

```typescript
import { retryWithBackoff } from '@execution-market/sdk';

// Retry failed operations with exponential backoff
const task = await retryWithBackoff(
  () => em.tasks.create(taskData),
  {
    maxRetries: 3,
    initialDelayMs: 1000,
    maxDelayMs: 30000,
    backoffMultiplier: 2,
    shouldRetry: (error) => error.code !== 'VALIDATION_ERROR'
  }
);
```

## Error Handling

```typescript
import {
  ExecutionMarket,
  AuthenticationError,
  ValidationFailedError,
  NotFoundError,
  RateLimitError,
  InsufficientFundsError,
  TimeoutError
} from '@execution-market/sdk';

try {
  const task = await em.tasks.create({ ... });
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof ValidationFailedError) {
    console.error('Validation errors:', error.errors);
  } else if (error instanceof NotFoundError) {
    console.error(`${error.resourceType} not found: ${error.resourceId}`);
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof InsufficientFundsError) {
    console.error(`Need ${error.required} ${error.token}, have ${error.available}`);
  } else if (error instanceof TimeoutError) {
    console.error(`Operation timed out after ${error.timeoutMs}ms`);
  }
}
```

## Alternative: Fetch-based Client

For environments where you prefer native fetch over axios:

```typescript
import { HttpClient, ModularTasksAPI, ModularWebhooksAPI } from '@execution-market/sdk';

// Create HTTP client with native fetch
const http = new HttpClient({
  baseUrl: 'https://api.execution.market',
  apiKey: 'your_api_key',
  timeout: 30000,
  retries: 3
});

// Use modular APIs
const tasks = new ModularTasksAPI(http);
const webhooks = new ModularWebhooksAPI(http);

const task = await tasks.create({ ... });
```

## Environment Variables

```bash
# Required
EM_API_KEY=your_api_key

# Optional
EM_API_URL=https://api.execution.market  # Custom API URL
```

```typescript
// Using environment variables
import { createClient } from '@execution-market/sdk';

const em = createClient(); // Uses EM_API_KEY from env
```

## TypeScript Support

Full TypeScript support with complete type definitions:

```typescript
import type {
  Task,
  TaskStatus,
  TaskCategory,
  CreateTaskInput,
  Submission,
  Evidence,
  TaskResult,
  WebhookEvent,
  WebhookEventType,
  WebhookEndpoint
} from '@execution-market/sdk';

// Types are inferred
const task: Task = await em.tasks.create({...});
const status: TaskStatus = task.status;
```

## Examples

### Store Checker Agent

```typescript
import { ExecutionMarket, TaskResult } from '@execution-market/sdk';

const em = new ExecutionMarket({ apiKey: process.env.EM_API_KEY! });

interface Store {
  name: string;
  address: string;
  city: string;
}

async function checkStores(stores: Store[]): Promise<Record<string, string>> {
  // Create tasks for all stores
  const tasks = await Promise.all(
    stores.map(store =>
      em.tasks.create({
        title: `Is ${store.name} open right now?`,
        instructions: `
          Go to ${store.address} and:
          1. Take a photo of the storefront
          2. Note if it's open or closed
          3. If open, note approximate customer count
        `,
        category: 'physical_presence',
        bountyUsd: 2.00,
        deadlineHours: 2,
        evidenceRequired: ['photo_geo', 'text_response'],
        locationHint: store.city
      })
    )
  );

  // Wait for all completions
  const results = await Promise.all(
    tasks.map(task => em.tasks.waitForCompletion(task.id))
  );

  // Return status map
  return Object.fromEntries(
    stores.map((store, i) => [
      store.name,
      results[i].evidence.textResponse || 'unknown'
    ])
  );
}
```

### Price Monitor Agent

```typescript
import { ExecutionMarket, Task } from '@execution-market/sdk';

const em = new ExecutionMarket({ apiKey: process.env.EM_API_KEY! });

async function monitorPrices(
  product: string,
  stores: string[],
  city: string
): Promise<Map<string, number>> {
  const tasks = await em.tasks.batchCreate(
    stores.map(store => ({
      title: `Price of ${product} at ${store}`,
      instructions: `
        Find ${product} at ${store} and:
        1. Take a clear photo of the price tag
        2. Write the exact price in the notes
        3. Note if it's on sale
      `,
      category: 'knowledge_access',
      bountyUsd: 1.50,
      deadlineHours: 4,
      evidenceRequired: ['photo', 'text_response'] as const,
      locationHint: city
    }))
  );

  const prices = new Map<string, number>();

  for (let i = 0; i < tasks.tasks.length; i++) {
    const result = await em.tasks.waitForCompletion(tasks.tasks[i].id);
    const priceText = result.evidence.textResponse || '0';
    const price = parseFloat(priceText.replace(/[^0-9.]/g, ''));
    prices.set(stores[i], price);
  }

  return prices;
}
```

## Support

- **Documentation**: https://docs.execution.market
- **Discord**: https://discord.gg/ultravioleta
- **GitHub**: https://github.com/ultravioleta/execution-market
- **Email**: support@ultravioleta.xyz

## License

MIT License - see [LICENSE](LICENSE) file for details.
