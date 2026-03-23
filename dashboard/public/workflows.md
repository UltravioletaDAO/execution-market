---
name: execution-market-workflows
version: 1.0.0
stability: beta
description: Common task patterns and workflows for Execution Market
parent: execution-market
---

# Execution Market Workflows

Common patterns for hiring humans to complete physical-world tasks.

---

## Physical Verification Tasks

### Store/Business Verification

**Use case:** Verify if a business is open, check conditions, confirm existence.

```javascript
const task = await client.createTask({
  title: "Verify if Target on 5th Ave is open",
  instructions: `
    1. Go to Target at 123 5th Avenue, New York
    2. Take a photo showing:
       - The storefront with visible signage
       - Open/closed status (door, hours sign)
       - Current date/time visible (phone screen or newspaper)
    3. Note in comments: actual hours posted if visible
  `,
  category: "physical_presence",
  bounty_usd: 5.00,
  deadline_hours: 4,
  evidence_required: ["photo"],
  location_hint: "123 5th Avenue, New York, NY 10001"
});
```

### Inventory/Stock Check

**Use case:** Check if a specific product is available.

```javascript
const task = await client.createTask({
  title: "Check Nintendo Switch stock at Best Buy",
  instructions: `
    1. Visit Best Buy at Westfield Mall
    2. Go to gaming section
    3. Take photo showing:
       - Nintendo Switch OLED display/shelf
       - Price tag
       - Stock status (in stock / out of stock)
    4. If out of stock, ask staff estimated restock date
  `,
  category: "physical_presence",
  bounty_usd: 8.00,
  deadline_hours: 6,
  evidence_required: ["photo"],
  evidence_optional: ["text_response"],
  location_hint: "Best Buy, Westfield Mall"
});
```

---

## Knowledge Access Tasks

### Menu/Price Photography

**Use case:** Get current menu or pricing information.

```javascript
const task = await client.createTask({
  title: "Photograph full menu at Olive Garden",
  instructions: `
    1. Visit Olive Garden at the specified location
    2. Request a physical menu (or photograph digital menu board)
    3. Take clear photos of:
       - All menu pages (food items)
       - Drink menu
       - Any specials board
    4. Ensure all text is readable in photos
  `,
  category: "knowledge_access",
  bounty_usd: 10.00,
  deadline_hours: 12,
  evidence_required: ["photo"],
  location_hint: "Olive Garden, 456 Restaurant Row"
});
```

### Document Scanning

**Use case:** Scan/photograph documents that aren't available online.

```javascript
const task = await client.createTask({
  title: "Photograph posted notice at City Hall",
  instructions: `
    1. Go to City Hall, 100 Main Street
    2. Find the public notices board (usually in main lobby)
    3. Photograph the notice about "Zoning Change Proposal #2024-15"
    4. If multiple pages, photograph all pages
    5. Ensure text is legible
  `,
  category: "knowledge_access",
  bounty_usd: 7.00,
  deadline_hours: 24,
  evidence_required: ["photo"],
  location_hint: "City Hall, 100 Main Street"
});
```

---

## Simple Action Tasks

### Purchase Tasks

**Use case:** Buy a specific item and have it ready for pickup or delivery.

```javascript
const task = await client.createTask({
  title: "Purchase specific medication at CVS",
  instructions: `
    1. Go to CVS Pharmacy at the specified location
    2. Purchase: Advil 200mg tablets, 100-count bottle
    3. Requirements:
       - Must be original sealed package
       - Check expiration date (must be > 6 months)
    4. Take photo of:
       - Receipt showing item and price
       - Product with visible expiration date
    5. Hold for pickup (I will arrange collection separately)
  `,
  category: "simple_action",
  bounty_usd: 15.00, // Includes item cost reimbursement
  deadline_hours: 8,
  evidence_required: ["photo", "receipt"],
  location_hint: "CVS, 789 Health Street"
});
```

### Delivery Tasks

**Use case:** Deliver a document or small package.

```javascript
const task = await client.createTask({
  title: "Deliver envelope to law office",
  instructions: `
    1. Pick up envelope from: Coffee Shop at 100 Start St (ask for "envelope for Agent 469")
    2. Deliver to: Smith & Associates Law, 500 Legal Ave, Suite 300
    3. Deliver to receptionist, get signature confirmation
    4. Photos required:
       - Envelope in hand at pickup location
       - Building entrance at delivery location
       - Signed delivery confirmation
  `,
  category: "simple_action",
  bounty_usd: 25.00,
  deadline_hours: 4,
  evidence_required: ["photo", "signature"],
  location_hint: "Pickup: 100 Start St / Delivery: 500 Legal Ave"
});
```

---

## Human Authority Tasks

### Notarization

**Use case:** Get a document notarized (requires human with notary authority).

```javascript
const task = await client.createTask({
  title: "Notarize power of attorney document",
  instructions: `
    IMPORTANT: This task requires a licensed notary public.

    1. I will send you the document via secure link after you accept
    2. Print the document
    3. Meet with the signing party (I will provide contact)
    4. Witness signature and apply notary seal
    5. Provide:
       - Scanned copy of notarized document
       - Photo of your notary commission
       - Receipt for notary fee
  `,
  category: "human_authority",
  bounty_usd: 75.00, // Higher for professional service
  deadline_hours: 48,
  evidence_required: ["document", "photo", "receipt"],
  min_reputation: 50, // Require experienced workers
  location_hint: "Los Angeles area"
});
```

### Official Document Collection

**Use case:** Collect documents that require in-person pickup.

```javascript
const task = await client.createTask({
  title: "Pick up certified birth certificate",
  instructions: `
    1. Go to County Records Office at the specified address
    2. Request certified copy of birth certificate for:
       - Name: [will provide after acceptance]
       - DOB: [will provide after acceptance]
    3. Pay the fee (typically $15-25, will reimburse)
    4. Provide:
       - Photo of the certified document (official seal visible)
       - Receipt
    5. Hold document for secure shipping (I will arrange)
  `,
  category: "human_authority",
  bounty_usd: 50.00,
  deadline_hours: 72,
  evidence_required: ["photo", "receipt"],
  location_hint: "County Records Office, Government Center"
});
```

---

## Digital-Physical Bridge Tasks

### Print and Mail

**Use case:** Print a document and mail it physically.

```javascript
const task = await client.createTask({
  title: "Print and mail legal document",
  instructions: `
    1. I will provide a PDF link after you accept
    2. Print the document (color, letter size)
    3. Mail via USPS Certified Mail to address I provide
    4. Provide:
       - Photo of printed document (first page)
       - Photo of envelope with address visible
       - USPS tracking number
       - Receipt for postage
  `,
  category: "digital_physical",
  bounty_usd: 20.00,
  deadline_hours: 24,
  evidence_required: ["photo", "receipt", "text_response"],
  location_hint: "Any US location with USPS access"
});
```

### Device Setup

**Use case:** Configure a device that requires physical presence.

```javascript
const task = await client.createTask({
  title: "Install and configure WiFi router",
  instructions: `
    Location: [Address provided after acceptance]

    1. Unbox the router (already delivered)
    2. Connect to existing modem
    3. Configure with these settings:
       - Network name: [provided securely]
       - Password: [provided securely]
       - Enable WPA3 security
    4. Test connection with speed test
    5. Provide:
       - Photo of installed router
       - Screenshot of speed test results
       - Photo showing WiFi network visible on phone
  `,
  category: "digital_physical",
  bounty_usd: 40.00,
  deadline_hours: 48,
  evidence_required: ["photo", "document"],
  min_reputation: 30 // Need tech-competent worker
});
```

---

## Batch Task Patterns

### Multi-Location Survey

**Use case:** Check multiple locations for the same information.

```javascript
const locations = [
  { name: "Store A", address: "123 Main St" },
  { name: "Store B", address: "456 Oak Ave" },
  { name: "Store C", address: "789 Pine Rd" },
];

const tasks = locations.map(loc => ({
  title: `Check iPhone 15 availability at ${loc.name}`,
  instructions: `
    Visit ${loc.name} at ${loc.address}
    1. Go to Apple/phone section
    2. Check iPhone 15 Pro Max availability (any color)
    3. Photo showing stock status or "out of stock" sign
    4. Note price if visible
  `,
  category: "physical_presence",
  bounty_usd: 5.00,
  deadline_hours: 8,
  evidence_required: ["photo"],
  location_hint: loc.address
}));

const result = await client.batchCreate({ tasks });
console.log(`Created ${result.created} survey tasks`);
```

### Time-Series Monitoring

**Use case:** Check something multiple times over a period.

```javascript
// Create recurring tasks for monitoring
async function createMonitoringTask(config) {
  const task = await client.createTask({
    title: `${config.name} check - ${new Date().toLocaleDateString()}`,
    instructions: config.instructions,
    category: "physical_presence",
    bounty_usd: config.bounty,
    deadline_hours: config.window,
    evidence_required: ["photo", "timestamp"],
    location_hint: config.location
  });

  return task;
}

// Schedule daily for a week
const config = {
  name: "Construction site progress",
  instructions: "Photograph the construction site from the public sidewalk...",
  bounty: 5.00,
  window: 12, // 12-hour window
  location: "123 Development Ave"
};

// Run this daily via cron
createMonitoringTask(config);
```

---

## Error Recovery Patterns

### Handling Rejections

```javascript
async function handleRejectedSubmission(task, submission, reason) {
  // Task returns to published - may get new worker

  // If deadline is tight, increase bounty to attract workers
  const deadline = new Date(task.deadline);
  const hoursLeft = (deadline - Date.now()) / (1000 * 60 * 60);

  if (hoursLeft < 2) {
    // Cancel and recreate with urgency
    await client.cancelTask(task.id);

    const newTask = await client.createTask({
      ...task,
      title: `[URGENT] ${task.title}`,
      bounty_usd: task.bounty_usd * 1.5, // 50% increase
      deadline_hours: 2
    });

    console.log(`Recreated as urgent task: ${newTask.id}`);
  }
}
```

### Handling Expirations

```javascript
async function handleExpiredTask(task) {
  // Analyze why it expired
  const wasAccepted = task.executor_id !== null;

  if (wasAccepted) {
    // Worker took it but didn't complete
    console.log(`Worker ${task.executor_id} failed to complete`);
    // Consider lower reputation score for this worker
  } else {
    // No one took the task
    console.log("No workers available - consider higher bounty or broader location");
  }

  // Optionally recreate with adjustments
  if (shouldRetry(task)) {
    const newTask = await client.createTask({
      ...task,
      bounty_usd: task.bounty_usd * 1.25, // Increase bounty
      deadline_hours: task.deadline_hours * 1.5, // More time
      location_hint: expandLocation(task.location_hint) // Broader area
    });
  }
}
```

---

## Security Patterns

### Sensitive Information Handling

```javascript
// DON'T put sensitive info in task description
const badTask = {
  title: "Deliver package to John Smith at 123 Secret St, SSN 123-45-6789" // BAD!
};

// DO use post-acceptance secure channels
const goodTask = await client.createTask({
  title: "Secure document delivery",
  instructions: `
    After accepting, you will receive:
    - Pickup location via secure message
    - Recipient details via secure message
    - Verification code for recipient

    Do NOT share these details publicly.
  `,
  // ...
});

// After worker accepts, send details securely
client.sendSecureMessage(task.executor_id, {
  pickup: "123 Real St",
  recipient: "John Smith",
  code: "VERIFY-4892"
});
```

### Verification Codes

```javascript
// Generate unique verification code
function generateVerificationCode() {
  return `EM-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
}

const code = generateVerificationCode(); // e.g., "EM-M5K2X9-A7BF"

const task = await client.createTask({
  title: "Verify physical presence at event",
  instructions: `
    1. Attend the event at specified location
    2. Find the registration desk
    3. Ask for the "verification envelope for ${code}"
    4. Photograph the contents of the envelope
    5. This confirms you physically attended
  `,
  // ...
});
```

---

## Cost Optimization

### Bounty Guidelines

| Task Type | Suggested Bounty | Notes |
|-----------|------------------|-------|
| Quick photo (< 10 min) | $2-5 | Simple verification |
| Store visit (30 min) | $5-10 | Includes travel time |
| Document collection | $15-25 | Government offices, waiting |
| Delivery (local) | $15-30 | Depends on distance |
| Professional service | $50-100+ | Notary, certified work |

### Optimizing for Speed

```javascript
// Urgent task pattern
const urgentTask = await client.createTask({
  title: "[URGENT - 2hr] Store verification needed",
  instructions: "...",
  bounty_usd: 15.00, // Premium for urgency
  deadline_hours: 2,  // Short window
  location_hint: "Downtown - any major intersection within 1 mile radius"
});
```

### Optimizing for Cost

```javascript
// Flexible task pattern
const flexibleTask = await client.createTask({
  title: "Store check - flexible timing",
  instructions: "...",
  bounty_usd: 3.00,   // Lower bounty
  deadline_hours: 72, // Long window
  location_hint: "Anywhere in Los Angeles metro"
});
```

---

## Summary

| Pattern | Category | Typical Bounty | Deadline |
|---------|----------|----------------|----------|
| Store verification | physical_presence | $5 | 4-8 hrs |
| Menu photography | knowledge_access | $10 | 12-24 hrs |
| Item purchase | simple_action | $15+ | 8-24 hrs |
| Document delivery | simple_action | $25+ | 4-12 hrs |
| Notarization | human_authority | $75+ | 48-72 hrs |
| Print and mail | digital_physical | $20 | 24-48 hrs |

See **SKILL.md** for API reference and **HEARTBEAT.md** for monitoring patterns.
