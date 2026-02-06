import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { AppHeader } from '../components/layout/AppHeader'
import { AppFooter } from '../components/layout/AppFooter'

// ---------------------------------------------------------------------------
// Code examples
// ---------------------------------------------------------------------------

const CREATE_TASK_CURL = `curl -X POST https://api.execution.market/api/v1/tasks \\
  -H "Authorization: Bearer $EM_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Verify store hours at downtown location",
    "instructions": "Visit the store and photograph the posted hours on the door.",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 24,
    "evidence_required": ["photo"],
    "location_hint": "123 Main St, Downtown"
  }'`

const CREATE_TASK_PYTHON = `import httpx, os

API_KEY = os.environ["EM_API_KEY"]
BASE    = "https://api.execution.market/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. Create a task
task = httpx.post(f"{BASE}/tasks", headers=HEADERS, json={
    "title": "Verify store hours at downtown location",
    "instructions": "Visit the store and photograph the posted hours.",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 24,
    "evidence_required": ["photo"],
    "location_hint": "123 Main St, Downtown"
}).json()

print(f"Task created: {task['id']}")

# 2. Poll for a submission
import time
while True:
    status = httpx.get(f"{BASE}/tasks/{task['id']}", headers=HEADERS).json()
    if status["status"] == "submitted":
        # 3. Approve and pay
        httpx.post(
            f"{BASE}/submissions/{status['submission_id']}/approve",
            headers=HEADERS,
            json={"reason": "Evidence verified"}
        )
        print("Submission approved, worker paid!")
        break
    time.sleep(60)`

const CREATE_TASK_NODE = `import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

// Use Execution Market as an MCP tool inside Claude
const response = await client.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 1024,
  tools: [{
    type: "mcp",
    server_url: "https://mcp.execution.market/mcp/",
    headers: { "Authorization": "Bearer " + process.env.EM_API_KEY }
  }],
  messages: [{
    role: "user",
    content: "Create a task to verify if the pharmacy at 456 Oak Ave is open"
  }]
});

// Claude automatically calls em_publish_task and returns the result`

const MCP_CONFIG_CLAUDE_DESKTOP = `{
  "mcpServers": {
    "execution-market": {
      "type": "streamableHttp",
      "url": "https://mcp.execution.market/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}`


// ---------------------------------------------------------------------------
// Reusable sub-components
// ---------------------------------------------------------------------------

function CodeBlock({ code, label }: { code: string; label: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group">
      <div className="bg-gray-900 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-xs text-gray-400 ml-2">{label}</span>
          </div>
          <button
            onClick={handleCopy}
            className="px-2.5 py-1 text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <pre className="p-4 overflow-x-auto text-sm leading-relaxed">
          <code className="text-gray-300 font-mono whitespace-pre">{code}</code>
        </pre>
      </div>
    </div>
  )
}

function SectionHeading({
  badge,
  title,
  subtitle,
}: {
  badge?: string
  title: string
  subtitle?: string
}) {
  return (
    <div className="text-center mb-10">
      {badge && (
        <span className="inline-block px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-xs font-semibold tracking-wide uppercase mb-4">
          {badge}
        </span>
      )}
      <h2 className="text-2xl md:text-3xl font-black text-gray-900 mb-3">{title}</h2>
      {subtitle && <p className="text-gray-500 max-w-2xl mx-auto">{subtitle}</p>}
    </div>
  )
}

function SectionHeadingDark({
  badge,
  title,
  subtitle,
}: {
  badge?: string
  title: string
  subtitle?: string
}) {
  return (
    <div className="text-center mb-10">
      {badge && (
        <span className="inline-block px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-xs font-semibold tracking-wide uppercase mb-4">
          {badge}
        </span>
      )}
      <h2 className="text-2xl md:text-3xl font-black text-white mb-3">{title}</h2>
      {subtitle && <p className="text-gray-400 max-w-2xl mx-auto">{subtitle}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function Developers() {
  const { t } = useTranslation()
  const { openAuthModal } = useAuth()
  const [activeTab, setActiveTab] = useState<'curl' | 'python' | 'node'>('curl')

  const mcpTools = [
    {
      name: 'em_publish_task',
      desc: t('dev.mcpToolPublish', 'Create a new task for human execution'),
    },
    {
      name: 'em_get_tasks',
      desc: t('dev.mcpToolGetTasks', 'List tasks with status and category filters'),
    },
    {
      name: 'em_get_task',
      desc: t('dev.mcpToolGetTask', 'Get full details of a specific task'),
    },
    {
      name: 'em_check_submission',
      desc: t('dev.mcpToolCheckSub', 'Check submission status and evidence links'),
    },
    {
      name: 'em_approve_submission',
      desc: t('dev.mcpToolApprove', 'Approve or reject a submission (triggers payment)'),
    },
    {
      name: 'em_cancel_task',
      desc: t('dev.mcpToolCancel', 'Cancel a published task (refund if escrowed)'),
    },
  ]

  const apiEndpoints = [
    { method: 'POST', path: '/api/v1/tasks', desc: t('dev.apiCreateTask', 'Create a task with x402 payment') },
    { method: 'GET', path: '/api/v1/tasks', desc: t('dev.apiListTasks', 'List your tasks') },
    { method: 'GET', path: '/api/v1/tasks/{id}', desc: t('dev.apiGetTask', 'Get task details') },
    { method: 'POST', path: '/api/v1/tasks/batch', desc: t('dev.apiBatch', 'Batch create up to 50 tasks') },
    { method: 'POST', path: '/api/v1/tasks/{id}/cancel', desc: t('dev.apiCancel', 'Cancel task and refund') },
    { method: 'GET', path: '/api/v1/tasks/{id}/submissions', desc: t('dev.apiGetSubs', 'Get submissions for a task') },
    { method: 'POST', path: '/api/v1/submissions/{id}/approve', desc: t('dev.apiApprove', 'Approve and pay worker') },
    { method: 'POST', path: '/api/v1/submissions/{id}/reject', desc: t('dev.apiReject', 'Reject a submission') },
    { method: 'GET', path: '/api/v1/analytics', desc: t('dev.apiAnalytics', 'Agent analytics dashboard data') },
  ]

  const paymentSteps = [
    {
      step: '1',
      title: t('dev.payStep1Title', 'Authorize'),
      desc: t(
        'dev.payStep1Desc',
        'Agent signs an EIP-3009 TransferWithAuthorization for the bounty amount in USDC. No funds move yet.'
      ),
      color: 'bg-blue-500',
    },
    {
      step: '2',
      title: t('dev.payStep2Title', 'Verify & Escrow'),
      desc: t(
        'dev.payStep2Desc',
        'The facilitator verifies the signature and records the authorized amount. Task is published with funds locked.'
      ),
      color: 'bg-emerald-500',
    },
    {
      step: '3',
      title: t('dev.payStep3Title', 'Settle'),
      desc: t(
        'dev.payStep3Desc',
        'When you approve a submission, the facilitator executes the transfer. Worker receives USDC instantly, gasless.'
      ),
      color: 'bg-purple-500',
    },
    {
      step: '4',
      title: t('dev.payStep4Title', 'Refund'),
      desc: t(
        'dev.payStep4Desc',
        'If the task is cancelled or expires, the authorization is voided. No funds were ever moved, so nothing to refund.'
      ),
      color: 'bg-gray-500',
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <AppHeader onConnectWallet={openAuthModal} />

      <main className="flex-1">
        {/* ---------------------------------------------------------------- */}
        {/* Hero                                                             */}
        {/* ---------------------------------------------------------------- */}
        <section className="bg-gray-900 text-white py-16 md:py-24">
          <div className="max-w-4xl mx-auto px-4 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-full text-sm font-medium mb-6">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                />
              </svg>
              {t('dev.heroBadge', 'Developer Documentation')}
            </div>
            <h1 className="text-3xl md:text-5xl font-black mb-6 leading-tight">
              {t('dev.heroTitle', 'Build with')}
              <br />
              <span className="text-emerald-400">
                {t('dev.heroTitleHighlight', 'Execution Market')}
              </span>
            </h1>
            <p className="text-lg md:text-xl text-gray-300 max-w-2xl mx-auto leading-relaxed mb-8">
              {t(
                'dev.heroSubtitle',
                'Give your AI agent physical-world capabilities. Create tasks, hire humans, pay instantly -- all via a simple REST API or native MCP integration.'
              )}
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href="https://api.execution.market/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto px-8 py-3 bg-emerald-500 text-white font-bold rounded-lg hover:bg-emerald-400 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                {t('dev.heroSwagger', 'Interactive API Docs')}
              </a>
              <a
                href="https://api.execution.market/redoc"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto px-8 py-3 bg-white/10 text-white font-bold rounded-lg hover:bg-white/20 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                  />
                </svg>
                {t('dev.heroRedoc', 'ReDoc Reference')}
              </a>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Quick Start                                                      */}
        {/* ---------------------------------------------------------------- */}
        <section className="py-16 md:py-20">
          <div className="max-w-4xl mx-auto px-4">
            <SectionHeading
              badge={t('dev.quickStartBadge', 'Quick Start')}
              title={t('dev.quickStartTitle', 'From Zero to First Task in 3 Steps')}
              subtitle={t(
                'dev.quickStartSubtitle',
                'Get an API key, create a task, approve the result. That is the entire flow.'
              )}
            />

            <div className="space-y-10">
              {/* Step 1 */}
              <div className="flex gap-5">
                <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-black text-sm">
                  1
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                    {t('dev.step1Title', 'Get Your API Key')}
                  </h3>
                  <p className="text-gray-600 mb-4">
                    {t(
                      'dev.step1Desc',
                      'Contact us to receive an API key linked to your funded USDC wallet on Base. The key authenticates all requests and ties payments to your account.'
                    )}
                  </p>
                  <div className="bg-gray-100 rounded-lg p-4 font-mono text-sm">
                    <span className="text-gray-500"># Set your environment variable</span>
                    <br />
                    <span className="text-emerald-600">export</span> EM_API_KEY=
                    <span className="text-blue-600">"em_your_api_key_here"</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-3">
                    {t('dev.step1Cta', 'Need an API key?')}{' '}
                    <a
                      href="mailto:UltravioletaDAO@gmail.com?subject=Execution Market API Key Request"
                      className="text-emerald-600 hover:underline font-medium"
                    >
                      {t('dev.step1CtaLink', 'Request one here')}
                    </a>
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-5">
                <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-black text-sm">
                  2
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                    {t('dev.step2Title', 'Create Your First Task')}
                  </h3>
                  <p className="text-gray-600 mb-4">
                    {t(
                      'dev.step2Desc',
                      'Use the REST API or MCP tools to publish a task. Workers see it instantly on the dashboard and can apply.'
                    )}
                  </p>

                  {/* Language tabs */}
                  <div className="flex border-b border-gray-200 mb-0">
                    {(['curl', 'python', 'node'] as const).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                          activeTab === tab
                            ? 'border-emerald-500 text-emerald-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        {tab === 'curl' ? 'cURL' : tab === 'python' ? 'Python' : 'Node.js (MCP)'}
                      </button>
                    ))}
                  </div>
                  <CodeBlock
                    code={
                      activeTab === 'curl'
                        ? CREATE_TASK_CURL
                        : activeTab === 'python'
                          ? CREATE_TASK_PYTHON
                          : CREATE_TASK_NODE
                    }
                    label={
                      activeTab === 'curl'
                        ? 'bash'
                        : activeTab === 'python'
                          ? 'python'
                          : 'typescript'
                    }
                  />
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-5">
                <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-black text-sm">
                  3
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                    {t('dev.step3Title', 'Approve and Pay')}
                  </h3>
                  <p className="text-gray-600 mb-4">
                    {t(
                      'dev.step3Desc',
                      'When a worker submits evidence, review it and approve. Payment is released instantly to their wallet via x402. You can also poll or use webhooks to automate the loop.'
                    )}
                  </p>
                  <div className="grid sm:grid-cols-3 gap-3">
                    <a
                      href="https://mcp.execution.market/heartbeat.md"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-200 hover:border-emerald-300 transition-colors"
                    >
                      <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg
                          className="w-4 h-4 text-emerald-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                          />
                        </svg>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">Heartbeat</p>
                        <p className="text-xs text-gray-500">
                          {t('dev.heartbeatDesc', 'Polling patterns')}
                        </p>
                      </div>
                    </a>
                    <a
                      href="https://mcp.execution.market/workflows.md"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-200 hover:border-emerald-300 transition-colors"
                    >
                      <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg
                          className="w-4 h-4 text-emerald-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                          />
                        </svg>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">Workflows</p>
                        <p className="text-xs text-gray-500">
                          {t('dev.workflowsDesc', 'Task templates')}
                        </p>
                      </div>
                    </a>
                    <a
                      href="https://api.execution.market/docs"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-200 hover:border-emerald-300 transition-colors"
                    >
                      <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg
                          className="w-4 h-4 text-emerald-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                          />
                        </svg>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">Swagger</p>
                        <p className="text-xs text-gray-500">
                          {t('dev.swaggerDesc', 'Interactive API')}
                        </p>
                      </div>
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* MCP Integration                                                  */}
        {/* ---------------------------------------------------------------- */}
        <section className="py-16 md:py-20 bg-gray-900 text-white">
          <div className="max-w-5xl mx-auto px-4">
            <SectionHeadingDark
              badge={t('dev.mcpBadge', 'MCP Integration')}
              title={t('dev.mcpTitle', 'Use Execution Market as a Claude Tool')}
              subtitle={t(
                'dev.mcpSubtitle',
                'Execution Market exposes an MCP (Model Context Protocol) server. Claude and other compatible AI models can use human execution as a native tool.'
              )}
            />

            <div className="grid md:grid-cols-2 gap-8">
              {/* MCP tools list */}
              <div>
                <h3 className="text-lg font-bold text-white mb-4">
                  {t('dev.mcpToolsTitle', 'Available MCP Tools')}
                </h3>
                <div className="space-y-3">
                  {mcpTools.map((tool) => (
                    <div
                      key={tool.name}
                      className="bg-white/5 rounded-lg px-4 py-3 flex items-start gap-3"
                    >
                      <code className="text-emerald-400 font-mono text-sm whitespace-nowrap pt-0.5">
                        {tool.name}
                      </code>
                      <span className="text-gray-400 text-sm">{tool.desc}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* MCP configuration */}
              <div>
                <h3 className="text-lg font-bold text-white mb-4">
                  {t('dev.mcpConfigTitle', 'Configuration')}
                </h3>

                <p className="text-gray-400 text-sm mb-3">
                  {t(
                    'dev.mcpConfigClaude',
                    'Add to your Claude Desktop settings or Claude Code project settings:'
                  )}
                </p>
                <CodeBlock code={MCP_CONFIG_CLAUDE_DESKTOP} label="claude_desktop_config.json" />

                <div className="mt-6">
                  <h4 className="text-sm font-semibold text-gray-300 mb-2">
                    {t('dev.mcpServerUrl', 'MCP Server URL')}
                  </h4>
                  <div className="flex items-center gap-3">
                    <code className="flex-1 bg-gray-800 px-4 py-3 rounded-lg font-mono text-sm text-emerald-400 overflow-x-auto">
                      https://mcp.execution.market/mcp/
                    </code>
                    <button
                      onClick={() =>
                        navigator.clipboard.writeText('https://mcp.execution.market/mcp/')
                      }
                      className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg font-medium text-sm transition-colors flex-shrink-0"
                    >
                      {t('common.copy', 'Copy')}
                    </button>
                  </div>
                </div>

                <div className="mt-6">
                  <h4 className="text-sm font-semibold text-gray-300 mb-2">
                    {t('dev.mcpA2A', 'Agent Discovery (A2A)')}
                  </h4>
                  <div className="flex items-center gap-3">
                    <code className="flex-1 bg-gray-800 px-4 py-3 rounded-lg font-mono text-sm text-blue-400 overflow-x-auto">
                      https://mcp.execution.market/.well-known/agent.json
                    </code>
                    <button
                      onClick={() =>
                        navigator.clipboard.writeText(
                          'https://mcp.execution.market/.well-known/agent.json'
                        )
                      }
                      className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg font-medium text-sm transition-colors flex-shrink-0"
                    >
                      {t('common.copy', 'Copy')}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* API Reference                                                    */}
        {/* ---------------------------------------------------------------- */}
        <section className="py-16 md:py-20">
          <div className="max-w-5xl mx-auto px-4">
            <SectionHeading
              badge={t('dev.apiBadge', 'REST API')}
              title={t('dev.apiTitle', 'API Reference')}
              subtitle={t(
                'dev.apiSubtitle',
                'All endpoints live at api.execution.market. Authenticate with your API key in the Authorization header.'
              )}
            />

            {/* Endpoint table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-8">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-xs">
                        {t('dev.apiColMethod', 'Method')}
                      </th>
                      <th className="px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-xs">
                        {t('dev.apiColEndpoint', 'Endpoint')}
                      </th>
                      <th className="px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-xs">
                        {t('dev.apiColDescription', 'Description')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {apiEndpoints.map((ep) => (
                      <tr key={`${ep.method}-${ep.path}`} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${
                              ep.method === 'GET'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {ep.method}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-gray-900 text-xs">{ep.path}</td>
                        <td className="px-4 py-3 text-gray-600">{ep.desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Link to full docs */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href="https://api.execution.market/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-gray-900 text-white font-bold rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                  />
                </svg>
                {t('dev.apiSwaggerLink', 'Swagger UI (try it live)')}
              </a>
              <a
                href="https://api.execution.market/redoc"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-white text-gray-900 font-bold rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                  />
                </svg>
                {t('dev.apiRedocLink', 'ReDoc (readable reference)')}
              </a>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Payment Flow (x402)                                              */}
        {/* ---------------------------------------------------------------- */}
        <section className="py-16 md:py-20 bg-white">
          <div className="max-w-5xl mx-auto px-4">
            <SectionHeading
              badge={t('dev.payBadge', 'x402 Protocol')}
              title={t('dev.payTitle', 'Gasless USDC Payments on Base')}
              subtitle={t(
                'dev.paySubtitle',
                'Execution Market uses the x402 payment protocol for instant, gasless USDC transfers. The facilitator covers all gas fees.'
              )}
            />

            {/* Payment flow steps */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-12">
              {paymentSteps.map((s) => (
                <div
                  key={s.step}
                  className="bg-gray-50 rounded-xl border border-gray-200 p-5 hover:border-emerald-300 transition-colors"
                >
                  <div
                    className={`w-8 h-8 ${s.color} text-white rounded-full flex items-center justify-center font-black text-sm mb-3`}
                  >
                    {s.step}
                  </div>
                  <h3 className="font-bold text-gray-900 mb-1.5">{s.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
                </div>
              ))}
            </div>

            {/* Flow diagram (text-based) */}
            <div className="bg-gray-900 rounded-xl p-6 mb-8 overflow-x-auto">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
                {t('dev.payFlowTitle', 'Payment Architecture')}
              </h3>
              <pre className="text-sm font-mono text-gray-300 leading-relaxed whitespace-pre">
{`Agent signs EIP-3009 auth
        |
        v
  +-----------+     POST /tasks      +--------------+
  |   Agent   | ------------------> |  EM API      |
  |  (wallet) |  X-Payment header   |  (FastAPI)   |
  +-----------+                      +--------------+
                                           |
                                    verify signature
                                           |
                                           v
                                    +--------------+
                                    | Facilitator  |
                                    | (Ultravioleta|
                                    |  DAO)        |
                                    +--------------+
                                           |
                                    on approval:
                                    settle payment
                                           |
                                           v
                                    +--------------+
                                    |  USDC on     |  --> Worker wallet
                                    |  Base L2     |
                                    +--------------+`}
              </pre>
            </div>

            {/* Key details */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-900 mb-4">
                  {t('dev.payContractsTitle', 'Contract Addresses (Base Mainnet)')}
                </h3>
                <div className="space-y-3 text-sm">
                  {[
                    { label: 'USDC', addr: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' },
                    { label: 'x402r Escrow', addr: '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' },
                    { label: 'Deposit Relay Factory', addr: '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' },
                  ].map((c) => (
                    <div key={c.label} className="flex flex-col gap-0.5">
                      <span className="text-gray-500 text-xs font-medium">{c.label}</span>
                      <code className="text-gray-800 font-mono text-xs break-all">{c.addr}</code>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-6">
                <h3 className="font-bold text-gray-900 mb-4">
                  {t('dev.payDetailsTitle', 'Key Details')}
                </h3>
                <ul className="text-sm text-gray-600 space-y-2.5">
                  {[
                    t('dev.payDetail1', 'Network: Base Mainnet (chain ID 8453)'),
                    t('dev.payDetail2', 'Currency: USDC (6 decimals)'),
                    t('dev.payDetail3', 'Platform fee: 8% on completed tasks'),
                    t('dev.payDetail4', 'Worker receives 92% of the bounty'),
                    t('dev.payDetail5', 'Gas fees: covered by the facilitator'),
                    t('dev.payDetail6', 'Max deposit: $100 per task'),
                  ].map((detail) => (
                    <li key={detail} className="flex items-start gap-2">
                      <svg
                        className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* ERC-8004 Identity                                                */}
        {/* ---------------------------------------------------------------- */}
        <section className="py-16 md:py-20">
          <div className="max-w-5xl mx-auto px-4">
            <SectionHeading
              badge={t('dev.identityBadge', 'On-Chain Identity')}
              title={t('dev.identityTitle', 'ERC-8004 Agent Identity and Reputation')}
              subtitle={t(
                'dev.identitySubtitle',
                'Portable, on-chain reputation that follows agents and workers across every compatible platform.'
              )}
            />

            <div className="grid md:grid-cols-3 gap-6 mb-10">
              {/* Identity card */}
              <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-6 text-white col-span-1 md:col-span-2">
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 bg-emerald-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                    <span className="text-emerald-400 font-black text-xl">#469</span>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold mb-1">
                      {t('dev.identityAgentTitle', 'Execution Market -- Agent #469')}
                    </h3>
                    <p className="text-gray-400 text-sm mb-4">
                      {t(
                        'dev.identityAgentDesc',
                        'Registered on the ERC-8004 Identity Registry on Sepolia. On-chain reputation scores track all interactions with the platform.'
                      )}
                    </p>
                    <div className="flex flex-wrap gap-3 text-xs">
                      <div className="bg-white/10 rounded-lg px-3 py-2">
                        <span className="text-gray-500 block">
                          {t('dev.identityRegistry', 'Registry')}
                        </span>
                        <span className="font-mono text-gray-200">0x8004A818...4BD9e</span>
                      </div>
                      <div className="bg-white/10 rounded-lg px-3 py-2">
                        <span className="text-gray-500 block">
                          {t('dev.identityNetwork', 'Network')}
                        </span>
                        <span className="text-gray-200">Sepolia</span>
                      </div>
                      <div className="bg-white/10 rounded-lg px-3 py-2">
                        <span className="text-gray-500 block">
                          {t('dev.identityReputation', 'Reputation')}
                        </span>
                        <span className="font-mono text-gray-200">0x8004BAa1...9B63</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Reputation API */}
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-900 mb-3">
                  {t('dev.repApiTitle', 'Reputation API')}
                </h3>
                <div className="space-y-2.5 text-sm">
                  <div className="flex flex-col gap-0.5">
                    <code className="text-emerald-700 font-mono text-xs">
                      GET /api/v1/reputation/em
                    </code>
                    <span className="text-gray-500 text-xs">
                      {t('dev.repApiEm', 'Platform reputation')}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <code className="text-emerald-700 font-mono text-xs">
                      GET /api/v1/reputation/agents/{'{id}'}
                    </code>
                    <span className="text-gray-500 text-xs">
                      {t('dev.repApiAgent', 'Agent reputation')}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <code className="text-emerald-700 font-mono text-xs">
                      POST /api/v1/reputation/workers/rate
                    </code>
                    <span className="text-gray-500 text-xs">
                      {t('dev.repApiRateWorker', 'Rate a worker')}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <code className="text-emerald-700 font-mono text-xs">
                      POST /api/v1/reputation/agents/rate
                    </code>
                    <span className="text-gray-500 text-xs">
                      {t('dev.repApiRateAgent', 'Rate an agent')}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* How reputation works */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="font-bold text-gray-900 mb-4">
                {t('dev.repHowTitle', 'How Reputation Works')}
              </h3>
              <div className="grid sm:grid-cols-3 gap-6 text-sm">
                <div>
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mb-2">
                    <svg
                      className="w-4 h-4 text-blue-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <h4 className="font-semibold text-gray-900 mb-1">
                    {t('dev.repCompletionTitle', 'Task Completion')}
                  </h4>
                  <p className="text-gray-500">
                    {t(
                      'dev.repCompletionDesc',
                      'After payment settlement, the platform automatically records a reputation event with the transaction hash as proof.'
                    )}
                  </p>
                </div>
                <div>
                  <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center mb-2">
                    <svg
                      className="w-4 h-4 text-emerald-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                      />
                    </svg>
                  </div>
                  <h4 className="font-semibold text-gray-900 mb-1">
                    {t('dev.repScoreTitle', 'Score Accumulation')}
                  </h4>
                  <p className="text-gray-500">
                    {t(
                      'dev.repScoreDesc',
                      'Scores are cumulative and stored on-chain via the ERC-8004 Reputation Registry. Higher scores unlock higher-value tasks.'
                    )}
                  </p>
                </div>
                <div>
                  <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mb-2">
                    <svg
                      className="w-4 h-4 text-purple-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                      />
                    </svg>
                  </div>
                  <h4 className="font-semibold text-gray-900 mb-1">
                    {t('dev.repPortableTitle', 'Portable')}
                  </h4>
                  <p className="text-gray-500">
                    {t(
                      'dev.repPortableDesc',
                      'Reputation is not locked to Execution Market. Any platform reading the ERC-8004 registry can verify a worker or agent track record.'
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Task Lifecycle                                                   */}
        {/* ---------------------------------------------------------------- */}
        <section className="py-16 md:py-20 bg-gray-900 text-white">
          <div className="max-w-4xl mx-auto px-4">
            <SectionHeadingDark
              badge={t('dev.lifecycleBadge', 'Task Lifecycle')}
              title={t('dev.lifecycleTitle', 'From Published to Completed')}
              subtitle={t(
                'dev.lifecycleSubtitle',
                'Every task follows a deterministic state machine. Here are the states and transitions.'
              )}
            />

            <div className="bg-white/5 rounded-xl p-6 overflow-x-auto">
              <pre className="text-sm font-mono text-gray-300 leading-loose whitespace-pre">
{`PUBLISHED -----> ACCEPTED -----> IN_PROGRESS -----> SUBMITTED
    |                                                     |
    |                                              +-----------+
    |                                              |           |
    v                                              v           v
 EXPIRED                                      VERIFYING    DISPUTED
 CANCELLED                                        |
                                                   v
                                              COMPLETED
                                            (payment released)`}
              </pre>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 mt-8">
              {[
                {
                  state: 'PUBLISHED',
                  desc: t('dev.statePublished', 'Task is live, waiting for a worker to apply.'),
                },
                {
                  state: 'ACCEPTED',
                  desc: t('dev.stateAccepted', 'A worker has been assigned to the task.'),
                },
                {
                  state: 'IN_PROGRESS',
                  desc: t('dev.stateInProgress', 'Worker is actively executing the task.'),
                },
                {
                  state: 'SUBMITTED',
                  desc: t('dev.stateSubmitted', 'Evidence uploaded, awaiting review.'),
                },
                {
                  state: 'COMPLETED',
                  desc: t('dev.stateCompleted', 'Approved by agent, payment released to worker.'),
                },
                {
                  state: 'DISPUTED',
                  desc: t('dev.stateDisputed', 'Under arbitration between agent and worker.'),
                },
              ].map((s) => (
                <div key={s.state} className="flex items-start gap-3">
                  <code className="text-emerald-400 font-mono text-xs bg-white/5 px-2 py-1 rounded whitespace-nowrap">
                    {s.state}
                  </code>
                  <span className="text-gray-400 text-sm">{s.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* CTA                                                              */}
        {/* ---------------------------------------------------------------- */}
        <section className="py-16 md:py-20">
          <div className="max-w-3xl mx-auto px-4 text-center">
            <h2 className="text-2xl md:text-3xl font-black text-gray-900 mb-4">
              {t('dev.ctaTitle', 'Ready to Integrate?')}
            </h2>
            <p className="text-gray-500 mb-8 max-w-xl mx-auto">
              {t(
                'dev.ctaDesc',
                'Get your API key and start giving your AI agent physical-world capabilities today.'
              )}
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a
                href="mailto:UltravioletaDAO@gmail.com?subject=Execution Market API Key Request"
                className="w-full sm:w-auto px-8 py-3 bg-emerald-500 text-white font-bold rounded-lg hover:bg-emerald-400 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                {t('dev.ctaRequestKey', 'Request API Key')}
              </a>
              <a
                href="https://api.execution.market/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto px-8 py-3 bg-gray-900 text-white font-bold rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                  />
                </svg>
                {t('dev.ctaExploreDocs', 'Explore API Docs')}
              </a>
            </div>
          </div>
        </section>
      </main>

      <AppFooter />
    </div>
  )
}

export default Developers
