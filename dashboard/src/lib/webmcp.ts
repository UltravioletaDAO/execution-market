// WebMCP — expose site tools to AI agents via navigator.modelContext.
//
// Spec: https://webmachinelearning.github.io/webmcp/
// Chrome EPP: https://developer.chrome.com/blog/webmcp-epp
//
// Registers a small set of navigational/informational tools when the browser
// exposes navigator.modelContext. Safe no-op on browsers without support.
// All tools return JSON-serializable results. Writes are gated via execute
// callbacks that go through React Router's navigate(), so the React guards
// (AuthGuard/WorkerGuard/AgentGuard) still apply to protected routes.

import { useEffect } from 'react'
import type { NavigateFunction } from 'react-router-dom'

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

function buildTools(navigate: NavigateFunction): WebMcpTool[] {
  const go = async (path: string) => {
    navigate(path)
    return { ok: true, navigated_to: path, url: window.location.origin + path }
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

/**
 * Register Execution Market's WebMCP tools with the browser's model context.
 * Returns a cleanup function. Safe no-op when the API is not present.
 */
export function registerWebMcpTools(navigate: NavigateFunction): () => void {
  const mc = getModelContext()
  if (!mc) return () => {}

  const ac = new AbortController()
  const tools = buildTools(navigate)

  try {
    if (typeof mc.registerTool === 'function') {
      for (const tool of tools) {
        mc.registerTool(tool, { signal: ac.signal })
      }
    } else if (typeof mc.provideContext === 'function') {
      mc.provideContext({ tools })
    }
  } catch (err) {
    console.warn('[webmcp] failed to register tools', err)
  }

  return () => {
    try { ac.abort() } catch { /* noop */ }
  }
}

/**
 * React hook — registers WebMCP tools on mount, unregisters on unmount.
 * Must be called inside a <BrowserRouter> (requires useNavigate context).
 */
export function useWebMcp(navigate: NavigateFunction): void {
  useEffect(() => {
    const cleanup = registerWebMcpTools(navigate)
    return cleanup
  }, [navigate])
}
