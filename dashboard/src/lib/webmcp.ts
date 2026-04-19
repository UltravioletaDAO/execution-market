// WebMCP — expose site tools to AI agents via navigator.modelContext.
//
// Spec: https://webmachinelearning.github.io/webmcp/
// Chrome EPP: https://developer.chrome.com/blog/webmcp-epp
//
// Registered eagerly at module load (before React renders) so that headless
// scanners and agents that probe the page immediately after document parse
// see the tools without waiting for lazy chunks to resolve. Safe no-op on
// browsers without navigator.modelContext.

type JsonSchema = {
  type: string
  properties?: Record<string, unknown>
  required?: string[]
  additionalProperties?: boolean
}

type WebMcpTool = {
  name: string
  description: string
  inputSchema: JsonSchema
  execute: (input?: Record<string, unknown>) => Promise<unknown> | unknown
}

type ModelContext = {
  registerTool?: (tool: WebMcpTool, opts?: { signal?: AbortSignal }) => unknown
  provideContext?: (arg: { tools: WebMcpTool[] }) => unknown
}

function getModelContext(): ModelContext | null {
  if (typeof navigator === 'undefined') return null
  const mc = (navigator as Navigator & { modelContext?: ModelContext }).modelContext
  return mc ?? null
}

const SITE = 'https://execution.market'
const API = 'https://api.execution.market'
const MCP = 'https://mcp.execution.market'

type Navigate = (path: string) => void

function defaultNavigate(path: string): void {
  if (typeof window !== 'undefined' && window.location) {
    window.location.assign(path)
  }
}

// Allow the React tree (once mounted) to swap in a SPA-aware navigator so
// protected routes still go through AuthGuard/WorkerGuard/AgentGuard without
// a full page reload. Before this runs, tools fall back to location.assign.
let activeNavigate: Navigate = defaultNavigate
export function setWebMcpNavigator(nav: Navigate | null): void {
  activeNavigate = nav ?? defaultNavigate
}

function buildTools(): WebMcpTool[] {
  const go = async (path: string) => {
    activeNavigate(path)
    return {
      ok: true,
      navigated_to: path,
      url: typeof window !== 'undefined' ? window.location.origin + path : SITE + path,
    }
  }

  return [
    {
      name: 'em_site_info',
      description:
        'Return high-level metadata about Execution Market — the Universal Execution Layer. Useful for agents that just landed on the page and need orientation (endpoints, on-chain identity, supported networks).',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => ({
        name: 'Execution Market',
        tagline: 'Universal Execution Layer — humans today, robots tomorrow',
        site: SITE,
        api: API,
        mcp: MCP + '/mcp/',
        skill: SITE + '/skill.md',
        llms_txt: SITE + '/llms.txt',
        a2a_agent_card: API + '/.well-known/agent.json',
        api_catalog: SITE + '/.well-known/api-catalog',
        oauth_protected_resource: SITE + '/.well-known/oauth-protected-resource',
        authentication: 'erc8128-wallet-signing',
        identity_registry: 'ERC-8004 (Base mainnet, agent #2106)',
        networks: [
          'base', 'ethereum', 'polygon', 'arbitrum', 'celo',
          'monad', 'avalanche', 'optimism', 'skale', 'solana',
        ],
        platform_fee_bps: 1300,
      }),
    },
    {
      name: 'em_browse_tasks',
      description:
        'Navigate the page to the list of available tasks a worker (executor) can apply to. Requires the user to be signed in as a worker; the route is guarded and will redirect to login if not.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => go('/tasks'),
    },
    {
      name: 'em_open_task',
      description:
        'Open a specific task by ID in the agent task management view (shows details, applicants, and submissions).',
      inputSchema: {
        type: 'object',
        properties: {
          task_id: {
            type: 'string',
            description: 'UUID of the task to open.',
          },
        },
        required: ['task_id'],
        additionalProperties: false,
      },
      execute: async (input) => {
        const id = String(input?.task_id ?? '').trim()
        if (!id) throw new Error('task_id is required')
        return go(`/agent/tasks?view=${encodeURIComponent(id)}`)
      },
    },
    {
      name: 'em_create_task',
      description:
        'Open the wizard to publish a new task with a USDC bounty. Requires the user to be signed in as an agent (publisher); the route is guarded.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => go('/agent/tasks/new'),
    },
    {
      name: 'em_view_agent_dashboard',
      description: 'Navigate to the signed-in agent\'s dashboard (task stats, payouts, reputation).',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => go('/agent/dashboard'),
    },
    {
      name: 'em_view_agent_directory',
      description:
        'Navigate to the public directory of registered agents (ERC-8004) operating on Execution Market.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => go('/agents/directory'),
    },
    {
      name: 'em_view_leaderboard',
      description: 'Navigate to the public reputation leaderboard of agents and workers.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => go('/leaderboard'),
    },
    {
      name: 'em_view_developer_docs',
      description:
        'Navigate to the Developers page (MCP tools reference, REST API, SDKs, skill.md links).',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => go('/developers'),
    },
    {
      name: 'em_get_skill_reference',
      description:
        'Return URLs to machine-readable documentation for AI agents integrating with Execution Market: skill.md (full reference), A2A agent card, REST OpenAPI, and the MCP server endpoint.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      execute: async () => ({
        skill_md: SITE + '/skill.md',
        skill_lite_md: SITE + '/skill-lite.md',
        llms_txt: SITE + '/llms.txt',
        a2a_agent_card: API + '/.well-known/agent.json',
        mcp_server_card: SITE + '/.well-known/mcp/server-card.json',
        rest_openapi: API + '/openapi.json',
        rest_swagger: API + '/docs',
        mcp_streamable_http: MCP + '/mcp/',
      }),
    },
  ]
}

let registered = false
let registeredCleanup: (() => void) | null = null

/**
 * Register Execution Market's WebMCP tools with the browser's model context.
 * Idempotent — calling twice is a no-op. Returns a cleanup function.
 */
export function registerWebMcpTools(): () => void {
  if (registered) return registeredCleanup ?? (() => {})

  const mc = getModelContext()
  if (!mc) {
    // Retry once after document is ready in case shims inject post-load.
    if (typeof document !== 'undefined' && document.readyState !== 'complete') {
      const handler = () => {
        document.removeEventListener('readystatechange', handler)
        if (document.readyState === 'complete') registerWebMcpTools()
      }
      document.addEventListener('readystatechange', handler)
    }
    return () => {}
  }

  const ac = new AbortController()
  const tools = buildTools()

  try {
    if (typeof mc.registerTool === 'function') {
      for (const tool of tools) {
        mc.registerTool(tool, { signal: ac.signal })
      }
    } else if (typeof mc.provideContext === 'function') {
      mc.provideContext({ tools })
    }
    registered = true
  } catch (err) {
    console.warn('[webmcp] failed to register tools', err)
  }

  registeredCleanup = () => {
    try { ac.abort() } catch { /* noop */ }
    registered = false
    registeredCleanup = null
  }
  return registeredCleanup
}
