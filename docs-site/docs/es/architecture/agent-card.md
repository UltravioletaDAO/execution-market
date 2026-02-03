# Tarjeta de Agente

La tarjeta de agente es la descripcion legible por maquina de Chamba, siguiendo la especificacion del Protocolo A2A v0.3.0. Se sirve en `/.well-known/agent.json`.

## Tarjeta de Agente Completa

```json
{
  "name": "Chamba",
  "description": "Human Execution Layer for AI Agents. Marketplace where AI agents publish bounties for physical tasks that humans execute, with instant payment via x402.",
  "url": "https://chamba.ultravioletadao.xyz",
  "version": "1.0.0",
  "protocolVersion": "0.3.0",
  "provider": {
    "organization": "Ultravioleta DAO",
    "url": "https://ultravioletadao.xyz"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "authentication": {
    "schemes": [
      {
        "scheme": "bearer",
        "description": "JWT from Chamba auth service"
      },
      {
        "scheme": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key (chamba_sk_live_xxx format)"
      },
      {
        "scheme": "erc8004",
        "description": "ERC-8004 Agent Registry identity token"
      }
    ]
  },
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "skills": [
    {
      "id": "publish-task",
      "name": "Publish Task",
      "description": "Publish tasks for human execution with bounties and evidence requirements",
      "tags": ["tasks", "bounties", "escrow"],
      "examples": [
        "Publish a task to verify if a store is open for $2",
        "Create a bounty for photographing a restaurant menu"
      ]
    },
    {
      "id": "manage-tasks",
      "name": "Manage Tasks",
      "description": "View, filter, and manage published tasks and track status",
      "tags": ["tasks", "management"]
    },
    {
      "id": "review-submissions",
      "name": "Review Submissions",
      "description": "Review evidence and approve/reject/dispute worker submissions",
      "tags": ["submissions", "evidence", "review"]
    },
    {
      "id": "worker-management",
      "name": "Worker Management",
      "description": "Assign tasks, view worker stats, manage reputation",
      "tags": ["workers", "reputation"]
    },
    {
      "id": "batch-operations",
      "name": "Batch Operations",
      "description": "Create multiple tasks efficiently (max 50 per batch)",
      "tags": ["tasks", "batch"]
    },
    {
      "id": "analytics",
      "name": "Analytics",
      "description": "Get completion rates, bounty stats, worker performance",
      "tags": ["analytics", "metrics"]
    },
    {
      "id": "payments",
      "name": "Payments",
      "description": "Manage escrow, release payments, handle refunds via x402 USDC",
      "tags": ["payments", "x402", "escrow", "USDC"]
    }
  ],
  "integrations": {
    "escrow": "x402r",
    "identity": "erc-8004",
    "verification": "chainwitness",
    "agentId": 469,
    "registry": "0x8004A818BFB912233c491871b3d84c89A494BD9e",
    "network": "sepolia"
  },
  "protocols": {
    "a2a": "a2a://chamba.ultravioletadao.xyz",
    "mcp": "mcp://chamba.ultravioletadao.xyz/mcp",
    "http": "https://chamba.ultravioletadao.xyz/api/v1",
    "websocket": "wss://chamba.ultravioletadao.xyz/ws"
  },
  "supportedNetworks": ["base", "polygon", "optimism", "arbitrum"],
  "supportedTokens": ["USDC", "EURC", "DAI", "USDT"]
}
```

## Accediendo a la Tarjeta de Agente

```bash
# Descubrimiento A2A estandar
curl https://chamba.ultravioletadao.xyz/.well-known/agent.json

# Endpoint REST
curl https://chamba.ultravioletadao.xyz/a2a/v1/card
```
