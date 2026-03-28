/**
 * Mock data for admin dashboard tests.
 *
 * These objects mirror the shapes returned by /api/v1/admin/* endpoints.
 * Use them in tests with vi.fn() or globalThis.fetch mocks — no MSW needed.
 */

// -- /api/v1/admin/config --
export const mockConfig = {
  items: [
    {
      key: 'platform_fee',
      value: 0.13,
      description: 'Platform fee percentage (0-1)',
      updated_at: '2026-03-01T00:00:00Z',
    },
    {
      key: 'max_bounty',
      value: 100,
      description: 'Maximum bounty in USDC',
      updated_at: '2026-03-01T00:00:00Z',
    },
    {
      key: 'require_erc8004',
      value: true,
      description: 'Require ERC-8004 identity for task creation',
      updated_at: '2026-03-15T00:00:00Z',
    },
  ],
}

// -- /api/v1/admin/stats --
export const mockStats = {
  total_tasks: 142,
  active_tasks: 23,
  completed_tasks: 98,
  cancelled_tasks: 21,
  total_users: 57,
  total_executors: 34,
  total_agents: 12,
  total_volume_usd: 1284.56,
  average_bounty_usd: 9.05,
}

// -- /api/v1/admin/tasks --
export const mockTasks = {
  tasks: [
    {
      id: 'task-001',
      title: 'Verify store hours at 123 Main St',
      description: 'Take a photo of the store sign showing opening hours.',
      status: 'published',
      category: 'physical_presence',
      bounty: 0.15,
      currency: 'USDC',
      network: 'base',
      agent_id: '2106',
      executor_id: null,
      created_at: '2026-03-20T10:00:00Z',
      deadline: '2026-03-20T10:30:00Z',
    },
    {
      id: 'task-002',
      title: 'Scan pages 10-15 of textbook',
      description: 'Photograph pages 10-15 clearly.',
      status: 'completed',
      category: 'knowledge_access',
      bounty: 0.10,
      currency: 'USDC',
      network: 'base',
      agent_id: '2106',
      executor_id: 'exec-001',
      created_at: '2026-03-19T14:00:00Z',
      deadline: '2026-03-19T14:30:00Z',
    },
    {
      id: 'task-003',
      title: 'Deliver package to office',
      description: 'Pick up from lobby, deliver to suite 400.',
      status: 'in_progress',
      category: 'simple_action',
      bounty: 0.20,
      currency: 'USDC',
      network: 'polygon',
      agent_id: '2106',
      executor_id: 'exec-002',
      created_at: '2026-03-20T08:00:00Z',
      deadline: '2026-03-20T09:00:00Z',
    },
  ],
  total: 142,
  page: 1,
  per_page: 20,
}

// -- /api/v1/admin/payments & /api/v1/admin/payments/stats --
export const mockPayments = {
  payments: [
    {
      id: 'pay-001',
      task_id: 'task-002',
      type: 'release',
      amount: 0.087,
      fee: 0.013,
      currency: 'USDC',
      network: 'base',
      from_wallet: '0xAgent001',
      to_wallet: '0xWorker001',
      tx_hash: '0xabc123',
      status: 'confirmed',
      created_at: '2026-03-19T14:25:00Z',
    },
    {
      id: 'pay-002',
      task_id: 'task-004',
      type: 'refund',
      amount: 0.15,
      fee: 0,
      currency: 'USDC',
      network: 'base',
      from_wallet: '0xEscrow',
      to_wallet: '0xAgent002',
      tx_hash: '0xdef456',
      status: 'confirmed',
      created_at: '2026-03-20T09:10:00Z',
    },
  ],
  total: 87,
  page: 1,
  per_page: 20,
}

export const mockPaymentStats = {
  total_volume: 1284.56,
  total_fees: 167.0,
  total_refunds: 42.3,
  transaction_count: 87,
  average_payment: 14.76,
  networks: {
    base: { volume: 980.2, count: 62 },
    polygon: { volume: 204.1, count: 18 },
    arbitrum: { volume: 100.26, count: 7 },
  },
}

// -- /api/v1/admin/users/:type --
export const mockUsers = {
  agents: {
    users: [
      {
        id: 'agent-2106',
        type: 'agent',
        name: 'Execution Market',
        wallet: '0xPlatformWallet',
        erc8004_id: 2106,
        status: 'active',
        tasks_created: 142,
        total_spent: 1284.56,
        created_at: '2026-01-15T00:00:00Z',
      },
    ],
    total: 12,
    page: 1,
    per_page: 20,
  },
  executors: {
    users: [
      {
        id: 'exec-001',
        type: 'executor',
        name: 'Alice Worker',
        wallet: '0xWorker001',
        erc8004_id: null,
        status: 'active',
        tasks_completed: 14,
        total_earned: 1.22,
        reputation: 4.8,
        created_at: '2026-02-01T00:00:00Z',
      },
      {
        id: 'exec-002',
        type: 'executor',
        name: 'Bob Builder',
        wallet: '0xWorker002',
        erc8004_id: 3001,
        status: 'active',
        tasks_completed: 7,
        total_earned: 0.61,
        reputation: 4.5,
        created_at: '2026-02-10T00:00:00Z',
      },
    ],
    total: 34,
    page: 1,
    per_page: 20,
  },
}

// -- /api/v1/admin/config/audit --
export const mockAuditLog = {
  entries: [
    {
      id: 'audit-001',
      action: 'config.update',
      category: 'config',
      actor: 'admin',
      detail: 'Updated platform_fee from 0.10 to 0.13',
      created_at: '2026-03-15T12:00:00Z',
    },
    {
      id: 'audit-002',
      action: 'user.suspend',
      category: 'users',
      actor: 'admin',
      detail: 'Suspended user exec-003 for policy violation',
      created_at: '2026-03-16T09:30:00Z',
    },
  ],
  total: 45,
  page: 1,
  per_page: 20,
}

// -- /api/v1/admin/analytics --
export const mockAnalytics = {
  period: '7d',
  tasks_by_day: [
    { date: '2026-03-14', created: 5, completed: 3, cancelled: 1 },
    { date: '2026-03-15', created: 8, completed: 6, cancelled: 0 },
    { date: '2026-03-16', created: 3, completed: 4, cancelled: 1 },
    { date: '2026-03-17', created: 7, completed: 5, cancelled: 2 },
    { date: '2026-03-18', created: 10, completed: 7, cancelled: 1 },
    { date: '2026-03-19', created: 6, completed: 8, cancelled: 0 },
    { date: '2026-03-20', created: 9, completed: 4, cancelled: 1 },
  ],
  top_categories: [
    { category: 'physical_presence', count: 52 },
    { category: 'knowledge_access', count: 38 },
    { category: 'simple_action', count: 29 },
    { category: 'digital_physical', count: 15 },
    { category: 'human_authority', count: 8 },
  ],
}

/**
 * Helper: create a mock fetch that routes by URL path.
 * Usage in tests:
 *   globalThis.fetch = createMockFetch({ '/api/v1/admin/stats': mockStats })
 */
export function createMockFetch(
  routes: Record<string, unknown>,
  fallbackStatus = 404,
) {
  return async (input: RequestInfo | URL, _init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input.toString()

    for (const [path, data] of Object.entries(routes)) {
      if (url.includes(path)) {
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
    }

    return new Response(JSON.stringify({ detail: 'Not found' }), {
      status: fallbackStatus,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
