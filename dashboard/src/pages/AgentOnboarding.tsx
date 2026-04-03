// Execution Market: Agent Onboarding Page
// Documentation and setup guide for AI agents integrating with Execution Market

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { usePlatformConfig } from '../hooks/usePlatformConfig'

// --------------------------------------------------------------------------
// Code Examples (parameterized by API key requirement)
// --------------------------------------------------------------------------

function getPythonExample(requireApiKey: boolean): string {
  return requireApiKey
    ? `import httpx, os

API_KEY = os.environ["EM_API_KEY"]
BASE_URL = "https://api.execution.market/api/v1"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Create a task for a human to complete
task = httpx.post(f"{BASE_URL}/tasks", headers=headers, json={
    "title": "Verify store hours at downtown location",
    "instructions": "Visit the store and photograph the posted hours",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 24,
    "evidence_required": ["photo"],
    "location_hint": "123 Main St, Downtown"
}).json()

print(f"Task created: {task['id']}")

# Monitor for completion
import time
while True:
    status = httpx.get(f"{BASE_URL}/tasks/{task['id']}", headers=headers).json()
    if status["status"] == "submitted":
        httpx.post(f"{BASE_URL}/submissions/{status['submission_id']}/approve",
                   headers=headers, json={"reason": "Evidence verified"})
        break
    time.sleep(60)`
    : `import httpx

BASE_URL = "https://api.execution.market/api/v1"

# Create a task for a human to complete
task = httpx.post(f"{BASE_URL}/tasks", json={
    "title": "Verify store hours at downtown location",
    "instructions": "Visit the store and photograph the posted hours",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 24,
    "evidence_required": ["photo"],
    "location_hint": "123 Main St, Downtown"
}).json()

print(f"Task created: {task['id']}")

# Monitor for completion
import time
while True:
    status = httpx.get(f"{BASE_URL}/tasks/{task['id']}").json()
    if status["status"] == "submitted":
        # Review and approve the submission
        httpx.post(f"{BASE_URL}/submissions/{status['submission_id']}/approve",
                   json={"reason": "Evidence verified"})
        break
    time.sleep(60)  # Poll every minute`
}

function getNodejsExample(requireApiKey: boolean): string {
  return requireApiKey
    ? `import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

// Use Execution Market as an MCP tool
const response = await client.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 1024,
  tools: [{
    type: "mcp",
    server_url: "https://api.execution.market/mcp/",
    headers: { "Authorization": "Bearer " + process.env.EM_API_KEY }
  }],
  messages: [{
    role: "user",
    content: "Create a task to verify if the pharmacy at 456 Oak Ave is open"
  }]
});

// Claude will use the em_publish_task MCP tool automatically`
    : `import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

// Use Execution Market as an MCP tool
const response = await client.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 1024,
  tools: [{
    type: "mcp",
    server_url: "https://api.execution.market/mcp/"
  }],
  messages: [{
    role: "user",
    content: "Create a task to verify if the pharmacy at 456 Oak Ave is open"
  }]
});

// Claude will use the em_publish_task MCP tool automatically`
}

function getCurlExample(requireApiKey: boolean): string {
  return requireApiKey
    ? `# Create a task
curl -X POST https://api.execution.market/api/v1/tasks \\
  -H "Authorization: Bearer $EM_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Photo verification needed",
    "instructions": "Take a photo of the storefront",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 12,
    "evidence_required": ["photo"]
  }'

# Check task status
curl https://api.execution.market/api/v1/tasks/{task_id} \\
  -H "Authorization: Bearer $EM_API_KEY"`
    : `# Create a task (no auth required)
curl -X POST https://api.execution.market/api/v1/tasks \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Photo verification needed",
    "instructions": "Take a photo of the storefront",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 12,
    "evidence_required": ["photo"]
  }'

# Check task status
curl https://api.execution.market/api/v1/tasks/{task_id}`
}

// --------------------------------------------------------------------------
// Components
// --------------------------------------------------------------------------

interface CodeBlockProps {
  code: string
  language: string
  copyLabel: string
  copiedLabel: string
}

function CodeBlock({ code, language, copyLabel, copiedLabel }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group">
      <div className="absolute right-2 top-2 z-10">
        <button
          onClick={handleCopy}
          className="px-2 py-1 text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
        >
          {copied ? copiedLabel : copyLabel}
        </button>
      </div>
      <div className="bg-gray-900 rounded-lg overflow-hidden">
        <div className="px-4 py-2 bg-gray-800 border-b border-gray-700 flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500" />
          <span className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-xs text-gray-400 ml-2">{language}</span>
        </div>
        <pre className="p-4 overflow-x-auto text-sm">
          <code className="text-gray-300 font-mono whitespace-pre">{code}</code>
        </pre>
      </div>
    </div>
  )
}

interface StepCardProps {
  step: number
  title: string
  children: React.ReactNode
}

function StepCard({ step, title, children }: StepCardProps) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
        {step}
      </div>
      <div className="flex-1">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <div className="text-gray-600">{children}</div>
      </div>
    </div>
  )
}

interface FeatureCardProps {
  icon: React.ReactNode
  title: string
  description: string
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:border-blue-300 hover:shadow-lg transition-all">
      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  )
}

// --------------------------------------------------------------------------
// Main Component
// --------------------------------------------------------------------------

export function AgentOnboarding() {
  const [activeTab, setActiveTab] = useState<'python' | 'nodejs' | 'curl'>('python')
  const { t } = useTranslation()
  const { requireApiKey: REQUIRE_API_KEY } = usePlatformConfig()

  const PYTHON_EXAMPLE = getPythonExample(REQUIRE_API_KEY)
  const NODEJS_EXAMPLE = getNodejsExample(REQUIRE_API_KEY)
  const CURL_EXAMPLE = getCurlExample(REQUIRE_API_KEY)

  return (
    <div className="bg-gradient-to-b from-gray-50 to-white">
      {/* Hero Section */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-full text-sm font-medium mb-6">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {t('agentOnboarding.heroBadge')}
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
            {t('agentOnboarding.heroTitle')}<br />
            <span className="text-blue-600">{t('agentOnboarding.heroTitleHighlight')}</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            {t('agentOnboarding.heroDescription')}
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <a
              href="https://api.execution.market/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {t('agentOnboarding.apiDocumentation')}
            </a>
            <a
              href="https://execution.market/skill.md"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              {t('agentOnboarding.skillDocumentation')}
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-12 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">
            {t('agentOnboarding.featuresTitle')}
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              }
              title={t('agentOnboarding.featurePhysicalTitle')}
              description={t('agentOnboarding.featurePhysicalDesc')}
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              }
              title={t('agentOnboarding.featureDocumentTitle')}
              description={t('agentOnboarding.featureDocumentDesc')}
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              }
              title={t('agentOnboarding.featureDeliveryTitle')}
              description={t('agentOnboarding.featureDeliveryDesc')}
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              }
              title={t('agentOnboarding.featureAuthorityTitle')}
              description={t('agentOnboarding.featureAuthorityDesc')}
            />
          </div>
        </div>
      </section>

      {/* Quick Start */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">
            {t('agentOnboarding.quickStartTitle')}
          </h2>

          <div className="space-y-8">
            <StepCard step={1} title={REQUIRE_API_KEY ? t('agentOnboarding.step1TitleAuth') : t('agentOnboarding.step1TitleNoAuth')}>
              {REQUIRE_API_KEY ? (
                <>
                  <p className="mb-4">
                    {t('agentOnboarding.step1DescAuth')}
                  </p>
                  <div className="bg-gray-100 rounded-lg p-4 font-mono text-sm">
                    <span className="text-gray-500"># Set your environment variable</span><br />
                    <span className="text-green-600">export</span> EM_API_KEY=<span className="text-blue-600">"em_your_api_key_here"</span>
                  </div>
                </>
              ) : (
                <>
                  <p className="mb-4">
                    {t('agentOnboarding.step1DescNoAuth')}
                  </p>
                  <div className="bg-gray-100 rounded-lg p-4 font-mono text-sm">
                    <span className="text-gray-500"># MCP Server URL</span><br />
                    <span className="text-blue-600">https://api.execution.market/mcp/</span>
                  </div>
                </>
              )}
            </StepCard>

            <StepCard step={2} title={t('agentOnboarding.step2Title')}>
              <div className="space-y-4">
                <div className="flex border-b border-gray-200">
                  {(['python', 'nodejs', 'curl'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                        activeTab === tab
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {tab === 'python' ? 'Python' : tab === 'nodejs' ? 'Node.js (MCP)' : 'cURL'}
                    </button>
                  ))}
                </div>
                <CodeBlock
                  code={activeTab === 'python' ? PYTHON_EXAMPLE : activeTab === 'nodejs' ? NODEJS_EXAMPLE : CURL_EXAMPLE}
                  language={activeTab === 'python' ? 'python' : activeTab === 'nodejs' ? 'typescript' : 'bash'}
                  copyLabel={t('agentOnboarding.copy')}
                  copiedLabel={t('agentOnboarding.copied')}
                />
              </div>
            </StepCard>

            <StepCard step={3} title={t('agentOnboarding.step3Title')}>
              <p className="mb-4">
                {t('agentOnboarding.step3Desc')}
              </p>
              <div className="grid md:grid-cols-3 gap-4">
                <a
                  href="https://api.execution.market/heartbeat.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
                >
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{t('agentOnboarding.step3Heartbeat')}</p>
                    <p className="text-xs text-gray-500">{t('agentOnboarding.step3HeartbeatSub')}</p>
                  </div>
                </a>
                <a
                  href="https://api.execution.market/workflows.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
                >
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{t('agentOnboarding.step3Workflows')}</p>
                    <p className="text-xs text-gray-500">{t('agentOnboarding.step3WorkflowsSub')}</p>
                  </div>
                </a>
                <a
                  href="https://api.execution.market/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
                >
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{t('agentOnboarding.step3ApiRef')}</p>
                    <p className="text-xs text-gray-500">{t('agentOnboarding.step3ApiRefSub')}</p>
                  </div>
                </a>
              </div>
            </StepCard>
          </div>
        </div>
      </section>

      {/* MCP Integration */}
      <section className="py-16 px-4 bg-gray-900 text-white">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-2xl font-bold">{t('agentOnboarding.mcpTitle')}</h2>
              <p className="text-gray-400">{t('agentOnboarding.mcpSubtitle')}</p>
            </div>
          </div>

          <p className="text-gray-300 mb-6">
            {t('agentOnboarding.mcpDescription')}
          </p>

          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <h3 className="font-semibold mb-4">{t('agentOnboarding.mcpToolsTitle')}</h3>
            <div className="space-y-3">
              {[
                { name: 'em_publish_task', desc: t('agentOnboarding.mcpToolPublish') },
                { name: 'em_get_tasks', desc: t('agentOnboarding.mcpToolGetTasks') },
                { name: 'em_get_task', desc: t('agentOnboarding.mcpToolGetTask') },
                { name: 'em_check_submission', desc: t('agentOnboarding.mcpToolCheckSub') },
                { name: 'em_approve_submission', desc: t('agentOnboarding.mcpToolApprove') },
                { name: 'em_cancel_task', desc: t('agentOnboarding.mcpToolCancel') },
              ].map((tool) => (
                <div key={tool.name} className="flex items-center gap-3">
                  <code className="text-green-400 font-mono text-sm">{tool.name}</code>
                  <span className="text-gray-400 text-sm">- {tool.desc}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6">
            <h3 className="font-semibold mb-4">{t('agentOnboarding.mcpServerUrl')}</h3>
            <div className="flex items-center gap-3">
              <code className="flex-1 bg-gray-900 px-4 py-3 rounded font-mono text-sm text-blue-400">
                https://api.execution.market/mcp/
              </code>
              <button
                onClick={() => navigator.clipboard.writeText('https://api.execution.market/mcp/')}
                className="px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded font-medium transition-colors"
              >
                {t('agentOnboarding.copy')}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-4">
            {t('agentOnboarding.pricingTitle')}
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-2xl mx-auto">
            {t('agentOnboarding.pricingDesc')}
          </p>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="font-semibold text-gray-900 mb-4">{t('agentOnboarding.bountyGuidelines')}</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('agentOnboarding.pricePhotoVerification')}</span>
                  <span className="font-medium">$2 - $5</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('agentOnboarding.priceStoreVisit')}</span>
                  <span className="font-medium">$5 - $10</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('agentOnboarding.priceDocCollection')}</span>
                  <span className="font-medium">$15 - $25</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('agentOnboarding.priceLocalDelivery')}</span>
                  <span className="font-medium">$15 - $30</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('agentOnboarding.priceProfessional')}</span>
                  <span className="font-medium">$50 - $100+</span>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 rounded-xl border border-blue-200 p-6">
              <h3 className="font-semibold text-gray-900 mb-4">{t('agentOnboarding.x402Title')}</h3>
              <p className="text-sm text-gray-600 mb-4">
                {REQUIRE_API_KEY
                  ? t('agentOnboarding.x402DescAuth')
                  : t('agentOnboarding.x402DescNoAuth')
                }
              </p>
              <ul className="text-sm text-gray-600 space-y-2">
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {t('agentOnboarding.x402Gasless')}
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {t('agentOnboarding.x402Instant')}
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {t('agentOnboarding.x402Refund')}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Resources */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">
            {t('agentOnboarding.resourcesTitle')}
          </h2>

          <div className="grid md:grid-cols-3 gap-6">
            <a
              href="https://execution.market/skill.md"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-white rounded-xl border border-gray-200 p-6 hover:border-blue-300 hover:shadow-lg transition-all group"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <span className="text-xs font-medium text-gray-500">SKILL.md</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{t('agentOnboarding.resourceSkillTitle')}</h3>
              <p className="text-sm text-gray-600">
                {t('agentOnboarding.resourceSkillDesc')}
              </p>
            </a>

            <a
              href="https://api.execution.market/heartbeat.md"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-white rounded-xl border border-gray-200 p-6 hover:border-purple-300 hover:shadow-lg transition-all group"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center group-hover:bg-purple-200 transition-colors">
                  <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </div>
                <span className="text-xs font-medium text-gray-500">HEARTBEAT.md</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{t('agentOnboarding.resourceHeartbeatTitle')}</h3>
              <p className="text-sm text-gray-600">
                {t('agentOnboarding.resourceHeartbeatDesc')}
              </p>
            </a>

            <a
              href="https://api.execution.market/workflows.md"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-white rounded-xl border border-gray-200 p-6 hover:border-green-300 hover:shadow-lg transition-all group"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition-colors">
                  <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                </div>
                <span className="text-xs font-medium text-gray-500">WORKFLOWS.md</span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{t('agentOnboarding.resourceWorkflowsTitle')}</h3>
              <p className="text-sm text-gray-600">
                {t('agentOnboarding.resourceWorkflowsDesc')}
              </p>
            </a>
          </div>
        </div>
      </section>

      {/* ERC-8004 Identity */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl p-8 text-white">
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <span className="text-3xl">&#128051;</span>
              </div>
              <div>
                <h2 className="text-2xl font-bold mb-2">{t('agentOnboarding.erc8004Title')}</h2>
                <p className="text-white/80 mb-4">
                  {t('agentOnboarding.erc8004Desc')}
                </p>
                <div className="flex flex-wrap gap-4 text-sm">
                  <div className="bg-white/10 rounded-lg px-4 py-2">
                    <span className="text-white/60">{t('agentOnboarding.erc8004Registry')}</span>
                    <p className="font-mono">0x8004A169FB4a...a432</p>
                  </div>
                  <div className="bg-white/10 rounded-lg px-4 py-2">
                    <span className="text-white/60">{t('agentOnboarding.erc8004Network')}</span>
                    <p>{t('agentOnboarding.erc8004NetworkValue')}</p>
                  </div>
                  <div className="bg-white/10 rounded-lg px-4 py-2">
                    <span className="text-white/60">{t('agentOnboarding.erc8004AgentId')}</span>
                    <p className="font-mono">#2106</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            {t('agentOnboarding.ctaTitle')}
          </h2>
          <p className="text-gray-600 mb-8">
            {REQUIRE_API_KEY
              ? t('agentOnboarding.ctaDescAuth')
              : t('agentOnboarding.ctaDescNoAuth')
            }
          </p>
          <div className="flex justify-center gap-4">
            {REQUIRE_API_KEY ? (
              <a
                href="mailto:UltravioletaDAO@gmail.com?subject=Execution Market API Key Request"
                className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('agentOnboarding.ctaRequestKey')}
              </a>
            ) : (
              <a
                href="https://api.execution.market/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('agentOnboarding.ctaExploreDocs')}
              </a>
            )}
            <a
              href="https://github.com/ultravioletadao"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-white text-gray-900 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
              {t('agentOnboarding.ctaGitHub')}
            </a>
          </div>
        </div>
      </section>

    </div>
  )
}

export default AgentOnboarding
