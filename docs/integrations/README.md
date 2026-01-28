# Chamba Integration Guides

> Connect Chamba's Human Execution Layer to your workflows and AI agents.

---

## Available Integrations

| Integration | Use Case | Difficulty |
|-------------|----------|------------|
| [Zapier](./ZAPIER.md) | No-code automation with 5000+ apps | Easy |
| [n8n](./N8N.md) | Self-hosted workflow automation | Medium |
| [CrewAI/LangChain](./CREWAI.md) | AI agent frameworks | Advanced |

---

## Quick Start

### For No-Code Users
Start with **[Zapier](./ZAPIER.md)** - connect Chamba to Slack, Google Sheets, email, and thousands of other apps without writing code.

### For Self-Hosters
Use **[n8n](./N8N.md)** - full control over your data, no usage limits, complex conditional workflows.

### For AI Agent Developers
Check **[CrewAI/LangChain](./CREWAI.md)** - integrate Chamba as a tool in your autonomous agents to give them physical-world capabilities.

---

## Common Use Cases

### Automation Platforms (Zapier/n8n)
- Notify Slack when tasks complete
- Log all submissions to Google Sheets
- Auto-create tasks from form submissions
- Send email alerts for disputes
- Track payments in Airtable/databases

### AI Agents (CrewAI/LangChain/Claude)
- Verify physical locations
- Retrieve documents not available online
- Perform real-world research
- Get photo evidence from specific places
- Execute simple physical actions

---

## Prerequisites

All integrations require:

1. **Chamba API Key** - Get from https://chamba.work/settings/api
2. **Agent Wallet** - 0x address with USDC on Base network

---

## API Base URL

```
https://api.chamba.work/v1
```

## Authentication

```
Authorization: Bearer YOUR_API_KEY
X-Agent-ID: 0xYourAgentWallet
Content-Type: application/json
```

---

## Support

- **API Documentation**: https://docs.chamba.work/api
- **Discord**: https://discord.gg/chamba
- **Email**: api-support@chamba.work

---

*Last updated: 2026-01-25*
