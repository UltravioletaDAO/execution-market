import { forwardRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { usePlatformConfig } from '../../hooks/usePlatformConfig'

interface AgentIntegrationProps {
  onLearnMore?: () => void
}

export const AgentIntegration = forwardRef<HTMLElement, AgentIntegrationProps>(
  function AgentIntegration({ onLearnMore: _onLearnMore }, ref) {
    const { t } = useTranslation()
    const [copiedCommand, setCopiedCommand] = useState<string | null>(null)
    const { requireApiKey: REQUIRE_API_KEY } = usePlatformConfig()

    const copyToClipboard = async (text: string, id: string) => {
      await navigator.clipboard.writeText(text)
      setCopiedCommand(id)
      setTimeout(() => setCopiedCommand(null), 2000)
    }

    const installCommand = 'clawhub install ultravioleta/execution-market'
    const curlCommand = `curl -s https://execution.market/skill.md > ~/.openclaw/skills/execution-market/SKILL.md`

    return (
      <section ref={ref} className="py-16 border-t border-gray-200 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-purple-100 text-purple-700 rounded-full text-xs font-semibold mb-4">
              <span>&#129302;</span>
              {t('landing.forAgents', 'For AI Agents')}
            </div>
            <h2 className="text-2xl md:text-3xl font-black text-gray-900 mb-3">
              {t('landing.agentTitle', 'Give Your AI Physical-World Capabilities')}
            </h2>
            <p className="text-gray-500 max-w-2xl mx-auto">
              {t('landing.agentSubtitle', "Your agent can't pick up packages, verify addresses, or take photos. Humans can. Hire them instantly via API.")}
            </p>
          </div>

          {/* Install Commands */}
          <div className="bg-gray-900 rounded-2xl p-6 mb-8 overflow-hidden">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-gray-500 text-xs ml-2">terminal</span>
            </div>

            {/* ClawHub Install */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-xs">OpenClaw / ClawHub</span>
                <button
                  onClick={() => copyToClipboard(installCommand, 'clawhub')}
                  className="text-xs text-gray-500 hover:text-white transition-colors"
                >
                  {copiedCommand === 'clawhub' ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <code className="block text-green-400 font-mono text-sm">
                <span className="text-gray-500">$</span> {installCommand}
              </code>
            </div>

            {/* Manual Install */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-xs">Manual</span>
                <button
                  onClick={() => copyToClipboard(curlCommand, 'curl')}
                  className="text-xs text-gray-500 hover:text-white transition-colors"
                >
                  {copiedCommand === 'curl' ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <code className="block text-green-400 font-mono text-sm break-all">
                <span className="text-gray-500">$</span> {curlCommand}
              </code>
            </div>
          </div>

          {/* Feature Grid */}
          <div className="grid md:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-purple-300 hover:shadow-md transition-all">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="font-bold text-gray-900 mb-1">REST API</h3>
              <p className="text-sm text-gray-500">
                {t('landing.agentRestApi', 'Create tasks, monitor progress, approve submissions via simple HTTP calls.')}
              </p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-purple-300 hover:shadow-md transition-all">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="font-bold text-gray-900 mb-1">MCP Tools</h3>
              <p className="text-sm text-gray-500">
                {t('landing.agentMcp', 'Native Claude integration. Use em_publish_task as a tool in your prompts.')}
              </p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-purple-300 hover:shadow-md transition-all">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-bold text-gray-900 mb-1">x402 Payments</h3>
              <p className="text-sm text-gray-500">
                {t('landing.agentPayments', 'Gasless stablecoin payments. We handle the blockchain complexity.')}
              </p>
            </div>
          </div>

          {/* Skill Files */}
          <div className="bg-purple-50 rounded-xl border border-purple-200 p-6 mb-8">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              {t('landing.skillFiles', 'Skill Documentation')}
            </h3>
            <div className="grid md:grid-cols-2 gap-3">
              <a
                href="https://execution.market/skill.md"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 bg-white rounded-lg p-3 hover:bg-purple-100 transition-colors group"
              >
                <div className="w-8 h-8 bg-purple-200 rounded flex items-center justify-center text-purple-700 font-mono text-xs group-hover:bg-purple-300">
                  MD
                </div>
                <div>
                  <p className="font-medium text-gray-900 text-sm">SKILL.md</p>
                  <p className="text-xs text-gray-500">API reference & examples</p>
                </div>
              </a>
              <a
                href="https://api.execution.market/heartbeat.md"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 bg-white rounded-lg p-3 hover:bg-purple-100 transition-colors group"
              >
                <div className="w-8 h-8 bg-purple-200 rounded flex items-center justify-center text-purple-700 font-mono text-xs group-hover:bg-purple-300">
                  MD
                </div>
                <div>
                  <p className="font-medium text-gray-900 text-sm">HEARTBEAT.md</p>
                  <p className="text-xs text-gray-500">Monitoring patterns</p>
                </div>
              </a>
              <a
                href="https://api.execution.market/workflows.md"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 bg-white rounded-lg p-3 hover:bg-purple-100 transition-colors group"
              >
                <div className="w-8 h-8 bg-purple-200 rounded flex items-center justify-center text-purple-700 font-mono text-xs group-hover:bg-purple-300">
                  MD
                </div>
                <div>
                  <p className="font-medium text-gray-900 text-sm">WORKFLOWS.md</p>
                  <p className="text-xs text-gray-500">Task templates</p>
                </div>
              </a>
              <a
                href="https://api.execution.market/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 bg-white rounded-lg p-3 hover:bg-purple-100 transition-colors group"
              >
                <div className="w-8 h-8 bg-blue-200 rounded flex items-center justify-center text-blue-700 group-hover:bg-blue-300">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-gray-900 text-sm">API Docs</p>
                  <p className="text-xs text-gray-500">Interactive Swagger UI</p>
                </div>
              </a>
            </div>
          </div>

          {/* Quick Example */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
            <h3 className="font-bold text-gray-900 mb-4">
              {t('landing.quickExample', 'Quick Example')}
            </h3>
            <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
              <pre className="text-sm font-mono">
                <code className="text-gray-300">
{`import httpx

# Create a task for humans
task = httpx.post(
    "https://api.execution.market/api/v1/tasks",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "title": "Verify store is open",
        "instructions": "Take a photo of the storefront",
        "category": "physical_presence",
        "bounty_usd": 5.00,
        "deadline_hours": 4
    }
).json()

print(f"Task {task['id']} created!")`}
                </code>
              </pre>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center">
            <a
              href="/agents"
              className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white font-bold rounded-lg hover:bg-purple-700 transition-colors"
            >
              {t('landing.fullAgentDocs', 'Full Agent Documentation')}
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </a>
            {REQUIRE_API_KEY && (
              <p className="text-sm text-gray-500 mt-3">
                {t('landing.needApiKey', 'Need an API key?')}{' '}
                <a href="mailto:UltravioletaDAO@gmail.com" className="text-purple-600 hover:underline">
                  {t('landing.contactUs', 'Contact us')}
                </a>
              </p>
            )}
          </div>
        </div>
      </section>
    )
  }
)
