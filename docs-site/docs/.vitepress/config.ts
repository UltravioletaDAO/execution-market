import { defineConfig } from 'vitepress'

const enNav = [
  { text: 'Guide', link: '/guide/overview' },
  { text: 'API', link: '/api/reference' },
  { text: 'Payments', link: '/payments/x402-overview' },
  { text: 'Contracts', link: '/contracts/addresses' },
  {
    text: 'Links',
    items: [
      { text: 'App', link: 'https://execution.market' },
      { text: 'GitHub', link: 'https://github.com/UltravioletaDAO/execution-market' },
      { text: 'Ultravioleta DAO', link: 'https://ultravioletadao.xyz' },
    ],
  },
]

const esNav = [
  { text: 'Guía', link: '/es/guide/overview' },
  { text: 'API', link: '/es/api/reference' },
  { text: 'Pagos', link: '/es/payments/x402-overview' },
  { text: 'Contratos', link: '/es/contracts/addresses' },
  {
    text: 'Enlaces',
    items: [
      { text: 'App', link: 'https://execution.market' },
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
      { text: 'Architecture', link: '/architecture/system' },
      { text: 'Quick Start', link: '/guide/quickstart' },
    ],
  },
  {
    text: 'Payments (x402)',
    items: [
      { text: 'x402 Overview', link: '/payments/x402-overview' },
      { text: 'Payment Modes', link: '/payments/payment-modes' },
      { text: 'Escrow Lifecycle', link: '/payments/escrow-lifecycle' },
      { text: 'Fee Structure', link: '/payments/fees' },
      { text: 'Supported Networks', link: '/payments/networks' },
      { text: 'Facilitator', link: '/payments/facilitator' },
      { text: 'Testing Scenarios', link: '/payments/testing-scenarios' },
    ],
  },
  {
    text: 'Smart Contracts',
    items: [
      { text: 'Contract Addresses', link: '/contracts/addresses' },
      { text: 'Legacy Escrow (Deprecated)', link: '/contracts/chamba-escrow' },
      { text: 'x402r Escrow', link: '/contracts/x402r-escrow' },
      { text: 'Audit Summary', link: '/contracts/audits' },
    ],
  },
  {
    text: 'Agent Identity',
    items: [
      { text: 'ERC-8004 Registration', link: '/architecture/erc8004' },
      { text: 'A2A Protocol', link: '/architecture/a2a-protocol' },
      { text: 'Agent Card', link: '/architecture/agent-card' },
    ],
  },
  {
    text: 'API Reference',
    items: [
      { text: 'REST API', link: '/api/reference' },
      { text: 'MCP Tools', link: '/api/mcp-tools' },
      { text: 'Authentication', link: '/api/authentication' },
      { text: 'Webhooks', link: '/api/webhooks' },
    ],
  },
  {
    text: 'Guides',
    items: [
      { text: 'For AI Agents', link: '/guides/for-agents' },
      { text: 'For Workers', link: '/guides/for-workers' },
      { text: 'Task Categories', link: '/guides/task-categories' },
      { text: 'Dispute Resolution', link: '/guides/disputes' },
    ],
  },
]

const esSidebar = [
  {
    text: 'Primeros Pasos',
    items: [
      { text: 'Descripción General', link: '/es/guide/overview' },
      { text: 'Arquitectura', link: '/es/architecture/system' },
      { text: 'Inicio Rápido', link: '/es/guide/quickstart' },
    ],
  },
  {
    text: 'Pagos (x402)',
    items: [
      { text: 'Descripción de x402', link: '/es/payments/x402-overview' },
      { text: 'Modos de Pago', link: '/es/payments/payment-modes' },
      { text: 'Ciclo de Vida del Escrow', link: '/es/payments/escrow-lifecycle' },
      { text: 'Estructura de Comisiones', link: '/es/payments/fees' },
      { text: 'Redes Soportadas', link: '/es/payments/networks' },
      { text: 'Facilitador', link: '/es/payments/facilitator' },
      { text: 'Escenarios de Prueba', link: '/es/payments/testing-scenarios' },
    ],
  },
  {
    text: 'Contratos Inteligentes',
    items: [
      { text: 'Direcciones de Contratos', link: '/es/contracts/addresses' },
      { text: 'Escrow Legacy (Deprecado)', link: '/es/contracts/chamba-escrow' },
      { text: 'x402r Escrow', link: '/es/contracts/x402r-escrow' },
      { text: 'Resumen de Auditoría', link: '/es/contracts/audits' },
    ],
  },
  {
    text: 'Identidad del Agente',
    items: [
      { text: 'Registro ERC-8004', link: '/es/architecture/erc8004' },
      { text: 'Protocolo A2A', link: '/es/architecture/a2a-protocol' },
      { text: 'Tarjeta de Agente', link: '/es/architecture/agent-card' },
    ],
  },
  {
    text: 'Referencia API',
    items: [
      { text: 'API REST', link: '/es/api/reference' },
      { text: 'Herramientas MCP', link: '/es/api/mcp-tools' },
      { text: 'Autenticación', link: '/es/api/authentication' },
      { text: 'Webhooks', link: '/es/api/webhooks' },
    ],
  },
  {
    text: 'Guías',
    items: [
      { text: 'Para Agentes IA', link: '/es/guides/for-agents' },
      { text: 'Para Trabajadores', link: '/es/guides/for-workers' },
      { text: 'Categorías de Tareas', link: '/es/guides/task-categories' },
      { text: 'Resolución de Disputas', link: '/es/guides/disputes' },
    ],
  },
]

export default defineConfig({
  title: 'Execution Market',
  description: 'Universal Execution Layer - Documentation',
  cleanUrls: true,

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' }],
    ['meta', { name: 'theme-color', content: '#0ea5e9' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:title', content: 'Execution Market Docs' }],
    ['meta', { property: 'og:description', content: 'Universal Execution Layer' }],
    ['meta', { property: 'og:url', content: 'https://docs.execution.market' }],
  ],

  locales: {
    root: {
      label: 'English',
      lang: 'en-US',
      themeConfig: {
        nav: enNav,
        sidebar: enSidebar,
        editLink: {
          pattern: 'https://github.com/UltravioletaDAO/execution-market/edit/main/docs-site/docs/:path',
          text: 'Edit this page on GitHub',
        },
        footer: {
          message: 'Built by Ultravioleta DAO',
          copyright: 'Agent #469 on ERC-8004 Sepolia Registry',
        },
      },
    },
    es: {
      label: 'Español',
      lang: 'es-MX',
      link: '/es/',
      themeConfig: {
        nav: esNav,
        sidebar: esSidebar,
        outlineTitle: 'En esta página',
        lastUpdatedText: 'Última actualización',
        docFooter: {
          prev: 'Anterior',
          next: 'Siguiente',
        },
        editLink: {
          pattern: 'https://github.com/UltravioletaDAO/execution-market/edit/main/docs-site/docs/:path',
          text: 'Editar esta página en GitHub',
        },
        footer: {
          message: 'Construido por Ultravioleta DAO',
          copyright: 'Agente #469 en el Registro ERC-8004 de Sepolia',
        },
      },
    },
  },

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'Execution Market Docs',

    socialLinks: [
      { icon: 'github', link: 'https://github.com/UltravioletaDAO/execution-market' },
      { icon: 'twitter', link: 'https://twitter.com/ultravioletadao' },
    ],

    search: {
      provider: 'local',
    },
  },
})
