# moonpay-mcp-server

Hackathon-grade MCP server that exposes MoonPay's on-ramp surface as
agentic tools. Built for the **MoonPay NYC cinematic demo** of
Execution Market (master plan phase 4.12) and the broader fiat-onramp
roadmap (see memory `fiat-onramp-master-plan`).

> **Status**: scaffold. Wires three working tools against MoonPay's
> public REST surface. When MoonPay's `mp mcp` CLI ships GA, swap the
> dispatcher for that.

## Why a separate MCP server

MoonPay on-ramping needs UI surfaces an MCP backend cannot provide
directly (Apple Pay sheets, 3DS prompts, KYC). This server answers the
*headless* parts an agent can use programmatically:

- price quotes (decide if the rate is acceptable before opening the widget)
- signed widget URLs (HMAC-bound so wallet/amount/currency cannot be tampered)
- transaction status polling (so the agent knows when USDC has landed)

The dashboard `MoonPayFrame` component takes the signed URL from
`moonpay_sign_onramp_url` and renders the headless overlay.

## Tools

| Tool | Purpose |
|------|---------|
| `moonpay_get_quote` | Quote USD → crypto for a given amount + chain + token |
| `moonpay_sign_onramp_url` | HMAC-sign a widget URL bound to wallet + amount + currency |
| `moonpay_get_transaction` | Poll a MoonPay transaction id for status + on-chain hash |

## Run locally

```bash
cd services/moonpay-mcp-server
pnpm install                       # or npm install
cp .env.example .env               # add MOONPAY_API_KEY + MOONPAY_SECRET_KEY
pnpm start                         # stdio transport
```

Wire into Claude Desktop (`~/.config/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "moonpay": {
      "command": "tsx",
      "args": ["/abs/path/services/moonpay-mcp-server/src/server.ts"],
      "env": {
        "MOONPAY_API_KEY": "pk_test_...",
        "MOONPAY_SECRET_KEY": "sk_test_..."
      }
    }
  }
}
```

## Out of scope (intentionally)

- **Off-ramp** (sell USDC → fiat). Tracked in Phase 4 of
  `fiat-onramp-master-plan` — likely a separate `moonpay-offramp-mcp-server`.
- **KYC/KYB orchestration**. Handled by MoonPay's hosted flow.
- **Production secret management**. The scaffold reads env vars; a
  productionized version should pull from AWS Secrets Manager.
- **`mp mcp` proxy**. The `mp mcp` CLI is not GA yet. When it ships,
  replace the REST helpers with a child-process proxy to `mp mcp` so
  agents inherit MoonPay's official tool surface.

## Security notes

- API keys are read from environment variables. Never log them, never
  embed them in source, never commit a populated `.env`.
- The HMAC signing happens server-side. Clients receive a fully-signed
  URL — they cannot re-sign or modify params.
- See `CLAUDE.md` (root repo) "Skills y Codigo Externo" for the
  hardened key-handling protocol.

## License

MIT — see root repo.
