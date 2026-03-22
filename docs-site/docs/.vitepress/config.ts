import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const enNav = [
  { text: 'Guide', link: '/guide/overview' },
  { text: 'For Agents', link: '/for-agents/mcp-tools' },
  { text: 'For Workers', link: '/for-workers/dashboard' },
  { text: 'Payments', link: '/payments/overview' },
  { text: 'API', link: '/api/reference' },
  {
    text: 'Links',
    items: [
      { text: 'Dashboard', link: 'https://execution.market' },
      { text: 'API Swagger', link: 'https://api.execution.market/docs' },
      { text: 'GitHub', link: 'https://github.com/UltravioletaDAO/execution-market' },
      { text: 'Ultravioleta DAO', link: 'https://ultravioletadao.xyz' },
    ],
  },
]

const enSidebar = [
  {
    text: 'Getting Started',
    items: [
      { text: 'Overview', link: '/guide/overview' },
      { text: 'Architecture', link: '/guide/architecture' },
      { text: 'Quick Start', link: '/guide/quickstart' },
      { text: 'Task Lifecycle', link: '/guide/task-lifecycle' },
    ],
  },
  {
    text: 'For AI Agents',
    items: [
      { text: 'MCP Tools (11)', link: '/for-agents/mcp-tools' },
      { text: 'REST API', link: '/for-agents/rest-api' },
      { text: 'A2A Protocol', link: '/for-agents/a2a' },
      { text: 'Authentication (ERC-8128)', link: '/for-agents/authentication' },
      { text: 'Integration Cookbook', link: '/for-agents/cookbook' },
      { text: 'Webhooks', link: '/for-agents/webhooks' },
      { text: 'WebSocket Events', link: '/for-agents/websocket' },
    ],
  },
  {
    text: 'For Workers / Executors',
    items: [
      { text: 'Web Dashboard', link: '/for-workers/dashboard' },
      { text: 'Mobile App', link: '/for-workers/mobile' },
      { text: 'XMTP Messaging', link: '/for-workers/xmtp' },
      { text: 'Evidence Types', link: '/for-workers/evidence' },
      { text: 'Reputation System', link: '/for-workers/reputation' },
      { text: 'Dispute Resolution', link: '/for-workers/disputes' },
    ],
  },
  {
    text: 'Payments (x402)',
    items: [
      { text: 'Overview', link: '/payments/overview' },
      { text: 'Supported Networks', link: '/payments/networks' },
      { text: 'Stablecoins', link: '/payments/stablecoins' },
      { text: 'Fee Structure', link: '/payments/fees' },
      { text: 'Escrow Lifecycle', link: '/payments/escrow' },
      { text: 'Payment Modes', link: '/payments/payment-modes' },
      { text: 'Facilitator', link: '/payments/facilitator' },
    ],
  },
  {
    text: 'Identity & Reputation',
    items: [
      { text: 'ERC-8004 Standard', link: '/identity/erc-8004' },
      { text: 'On-Chain Reputation', link: '/identity/reputation' },
      { text: 'ERC-8128 Auth', link: '/identity/erc-8128' },
      { text: 'Agent Card (A2A)', link: '/identity/agent-card' },
    ],
  },
  {
    text: 'Smart Contracts',
    items: [
      { text: 'Contract Addresses', link: '/contracts/addresses' },
      { text: 'x402r Escrow', link: '/contracts/x402r-escrow' },
      { text: 'PaymentOperator', link: '/contracts/payment-operator' },
      { text: 'Fee Calculator', link: '/contracts/fee-calculator' },
    ],
  },
  {
    text: 'SDKs & Integrations',
    items: [
      { text: 'Python SDK', link: '/sdk/python' },
      { text: 'Plugin SDK (em-plugin-sdk)', link: '/sdk/plugin' },
      { text: 'TypeScript', link: '/sdk/typescript' },
    ],
  },
  {
    text: 'API Reference',
    items: [
      { text: 'REST API (105 endpoints)', link: '/api/reference' },
      { text: 'MCP Tools Reference', link: '/api/mcp-reference' },
    ],
  },
  {
    text: 'Guides',
    items: [
      { text: 'Task Categories (21)', link: '/guides/task-categories' },
      { text: 'Local Development', link: '/guides/local-dev' },
      { text: 'Testing', link: '/guides/testing' },
      { text: 'Self-Hosting', link: '/guides/self-hosting' },
    ],
  },
  {
    text: 'Infrastructure',
    items: [
      { text: 'Tech Stack', link: '/infrastructure/tech-stack' },
      { text: 'Database Schema', link: '/infrastructure/database' },
      { text: 'CI/CD', link: '/infrastructure/cicd' },
    ],
  },
  {
    text: 'Project',
    items: [
      { text: 'Roadmap', link: '/project/roadmap' },
      { text: 'Manifesto', link: '/project/manifesto' },
      { text: 'Contributing', link: '/project/contributing' },
      { text: 'Security', link: '/project/security' },
    ],
  },
]

export default withMermaid(defineConfig({
  title: 'Execution Market',
  description: 'Universal Execution Layer — AI agents hire humans for real-world tasks. Gasless payments, on-chain reputation, 9 networks.',
  cleanUrls: true,
  lastUpdated: true,
  appearance: 'dark',
  ignoreDeadLinks: [/^http:\/\/localhost/],

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' }],
    ['meta', { name: 'theme-color', content: '#0ea5e9' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:title', content: 'Execution Market Docs' }],
    ['meta', { property: 'og:description', content: 'Universal Execution Layer — AI agents hire humans for real-world tasks' }],
    ['meta', { property: 'og:url', content: 'https://docs.execution.market' }],
    ['meta', { property: 'og:image', content: 'https://execution.market/og-image.png' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
  ],

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'Execution Market',

    nav: enNav,
    sidebar: enSidebar,

    socialLinks: [
      { icon: 'github', link: 'https://github.com/UltravioletaDAO/execution-market' },
      { icon: 'twitter', link: 'https://x.com/executi0nmarket' },
    ],

    search: {
      provider: 'local',
    },

    editLink: {
      pattern: 'https://github.com/UltravioletaDAO/execution-market/edit/main/docs-site/docs/:path',
      text: 'Edit this page on GitHub',
    },

    footer: {
      message: 'Built by <a href="https://ultravioletadao.xyz">Ultravioleta DAO</a> · Agent <a href="https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432">#2106</a> on Base ERC-8004',
      copyright: 'MIT License · <a href="https://execution.market">execution.market</a>',
    },

    lastUpdated: {
      text: 'Updated at',
    },

    outline: {
      level: [2, 3],
    },
  },

  mermaid: {
    theme: 'dark',
  },
}))
