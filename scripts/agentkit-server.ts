/**
 * AgentKit x402 Server — World Hackathon Track 1
 *
 * Standalone Hono server that uses @worldcoin/agentkit to gate access
 * to Execution Market task data. Verified humans (via World ID + AgentBook)
 * get free access; unverified bots must pay via x402 micropayments.
 *
 * Usage:
 *   npx tsx agentkit-server.ts
 *
 * Env vars:
 *   SETTLEMENT_ADDRESS  — wallet that receives x402 payments (required)
 *   X402_FACILITATOR_URL — facilitator URL (default: World's hosted)
 *   EM_API_URL          — Execution Market API (default: https://api.execution.market)
 *   PORT                — server port (default: 4021)
 */

import { config } from "dotenv";
import { resolve } from "path";

// Load .env.local from project root
config({ path: resolve(new URL(".", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1"), "../.env.local") });

import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { HTTPFacilitatorClient } from "@x402/core/http";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import {
  paymentMiddlewareFromHTTPServer,
  x402HTTPResourceServer,
  x402ResourceServer,
} from "@x402/hono";
import {
  agentkitResourceServerExtension,
  createAgentBookVerifier,
  createAgentkitHooks,
  declareAgentkitExtension,
  InMemoryAgentKitStorage,
} from "@worldcoin/agentkit";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const PORT = parseInt(process.env.PORT || "4021", 10);
const BASE_NETWORK = "eip155:8453"; // Base mainnet

// Facilitator EOA (same wallet used across all EM chains)
const SETTLEMENT_ADDRESS = process.env.SETTLEMENT_ADDRESS
  || process.env.EM_TREASURY_ADDRESS
  || "0x103040545AC5031A11E8C03dd11324C7333a13C7";

const FACILITATOR_URL =
  process.env.X402_FACILITATOR_URL ||
  "https://x402-worldchain.vercel.app/facilitator";

const EM_API_URL =
  process.env.EM_API_URL || "https://api.execution.market";

// ---------------------------------------------------------------------------
// x402 + AgentKit setup
// ---------------------------------------------------------------------------

// x402 facilitator client
const facilitatorClient = new HTTPFacilitatorClient({
  url: FACILITATOR_URL,
});

// EVM payment scheme (Base mainnet, USDC)
const evmScheme = new ExactEvmScheme();

// AgentBook verifier — reads the AgentBook contract on Base
// Contract: 0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4
const agentBook = createAgentBookVerifier();

// In-memory storage for tracking per-human usage
const storage = new InMemoryAgentKitStorage();

// AgentKit hooks: verified humans get 10 free requests, then pay
const hooks = createAgentkitHooks({
  agentBook,
  storage,
  mode: { type: "free-trial", uses: 10 },
});

// Resource server with AgentKit extension
const resourceServer = new x402ResourceServer(facilitatorClient)
  .register(BASE_NETWORK, evmScheme)
  .registerExtension(agentkitResourceServerExtension);

// Protected routes — x402 + AgentKit gating
const routes = {
  "GET /api/v1/verified-tasks": {
    accepts: [
      {
        scheme: "exact" as const,
        price: "$0.001",
        network: BASE_NETWORK,
        payTo: SETTLEMENT_ADDRESS,
      },
    ],
    extensions: declareAgentkitExtension({
      statement:
        "Verify your agent is backed by a real human to access Execution Market tasks for free",
      mode: { type: "free-trial" as const, uses: 10 },
    }),
  },
  "GET /api/v1/verified-worker/:wallet": {
    accepts: [
      {
        scheme: "exact" as const,
        price: "$0.001",
        network: BASE_NETWORK,
        payTo: SETTLEMENT_ADDRESS,
      },
    ],
    extensions: declareAgentkitExtension({
      statement:
        "Verify your agent is human-backed to check worker verification status",
      mode: { type: "free" as const },
    }),
  },
};

const httpServer = new x402HTTPResourceServer(resourceServer, routes)
  .onProtectedRequest(hooks.requestHook);

// ---------------------------------------------------------------------------
// Hono app
// ---------------------------------------------------------------------------

const app = new Hono();

// Apply x402 + AgentKit payment middleware
app.use(paymentMiddlewareFromHTTPServer(httpServer));

// Health check (unprotected)
app.get("/health", (c) =>
  c.json({
    status: "ok",
    service: "execution-market-agentkit",
    agentkit: true,
    agentbook_contract: "0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4",
    network: "base",
    facilitator: FACILITATOR_URL,
  })
);

// Protected: Browse verified tasks
// Humans verified via World ID get free access; bots pay $0.001 per request
app.get("/api/v1/verified-tasks", async (c) => {
  try {
    // Proxy to the real EM API
    const resp = await fetch(`${EM_API_URL}/api/v1/tasks?status=published&limit=20`);
    if (resp.ok) {
      const data = await resp.json();
      return c.json({
        ...data,
        _agentkit: {
          message: "Access granted via World AgentKit + x402",
          human_verified: true,
        },
      });
    }
    // Fallback if EM API is unreachable
    return c.json({
      tasks: [],
      message: "Execution Market API unreachable — showing empty results",
      _agentkit: { human_verified: true },
    });
  } catch {
    return c.json({
      tasks: [],
      message: "Proxy error",
      _agentkit: { human_verified: true },
    });
  }
});

// Protected: Check if a worker is a verified human
// Free for human-backed agents (no payment needed)
app.get("/api/v1/verified-worker/:wallet", async (c) => {
  const wallet = c.req.param("wallet");
  try {
    const resp = await fetch(
      `${EM_API_URL}/api/v1/workers/world-status?wallet=${wallet}`
    );
    if (resp.ok) {
      const data = await resp.json();
      return c.json({
        ...data,
        _agentkit: {
          message: "Worker verification via AgentKit + AgentBook",
          agentbook_contract: "0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4",
        },
      });
    }
    return c.json({ error: "Worker status unavailable" }, 502);
  } catch {
    return c.json({ error: "Proxy error" }, 502);
  }
});

// Info endpoint (unprotected)
app.get("/", (c) =>
  c.json({
    name: "Execution Market — AgentKit Gateway",
    description:
      "x402 + World AgentKit gateway for Execution Market. " +
      "Verified humans (World ID) get free access to task data. " +
      "Unverified bots pay $0.001/request via x402 micropayments on Base.",
    endpoints: {
      "GET /health": "Health check (free)",
      "GET /api/v1/verified-tasks":
        "Browse published tasks (free for verified humans, $0.001 for bots)",
      "GET /api/v1/verified-worker/:wallet":
        "Check worker World ID status (free for verified humans)",
    },
    contracts: {
      agentbook: "0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4",
      erc8004_identity: "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
    },
    register:
      "npx @worldcoin/agentkit-cli register <YOUR_WALLET> — register as verified human",
  })
);

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------

serve({ fetch: app.fetch, port: PORT }, (info) => {
  console.log(`
  ╔══════════════════════════════════════════════════════════╗
  ║  Execution Market — AgentKit x402 Gateway               ║
  ║  Port: ${String(info.port).padEnd(49)}║
  ║  Facilitator: ${FACILITATOR_URL.substring(0, 42).padEnd(42)}║
  ║  AgentBook: 0xE1D1...61a4 (Base)                        ║
  ║                                                          ║
  ║  Verified humans: FREE access (10 requests/trial)        ║
  ║  Unverified bots: $0.001/request via x402                ║
  ╚══════════════════════════════════════════════════════════╝
  `);
});
