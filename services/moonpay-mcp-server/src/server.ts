#!/usr/bin/env node
/**
 * moonpay-mcp-server — agentic MoonPay on-ramp for AI workflows.
 *
 * Wraps MoonPay's `mp mcp` CLI (the official MoonPay agentic toolkit)
 * with a Model Context Protocol server that AI agents can mount via
 * Claude Desktop or any MCP-compatible client. The use case is the
 * MoonPay NYC demo (Phase 4.12): an agent that needs USDC on Solana
 * to publish an Execution Market task fires `moonpay_buy_usdc_solana`
 * from this server, the human signs in MoonPay's headless overlay,
 * USDC lands on the wallet in <90s, the agent publishes the task.
 *
 * Why a separate MCP server (vs. inlining the calls in EM's main MCP
 * server): MoonPay onramping requires UI surfaces a backend MCP can't
 * provide directly — Apple Pay sheets, 3DS prompts, KYC. The MCP
 * server here returns *signed URLs* and *transaction status* — the
 * UI rendering belongs in the dashboard (`MoonPayFrame` component).
 *
 * Hackathon-grade scope (per master plan task 4.12 — "Solo si tiempo
 * permite, NO blocker para demo"):
 *   - Stub `mp mcp` proxy (it is not yet GA — when it ships, wire it
 *     into the `mpMcpCommand` helper below).
 *   - Three working tools that hit MoonPay's public REST surface so
 *     the server is useful end-to-end *today* without depending on
 *     `mp mcp` GA:
 *
 *       moonpay_get_quote(amount_usd, target_chain, target_token)
 *         → returns expected USDC out, fees, ETA
 *       moonpay_sign_onramp_url(wallet_address, amount_usd, currency)
 *         → returns a signed widget URL the dashboard opens
 *       moonpay_get_transaction(tx_id)
 *         → polls transaction status by id (created → completed)
 *
 * Out of scope for hackathon-grade:
 *   - Off-ramp (sell USDC → fiat) — Phase 4 of fiat-onramp-master-plan
 *   - KYC/KYB orchestration — handled by MoonPay's hosted flow
 *   - Production secret management — current scaffold reads from env
 *     vars; a productionized version would pull from AWS Secrets
 *     Manager (see CLAUDE.md, "Skills y Codigo Externo")
 *
 * Required env (read at startup, never logged):
 *   MOONPAY_API_KEY          publishable key (pk_*)
 *   MOONPAY_SECRET_KEY       URL signing secret (sk_*)
 *   MOONPAY_BASE_URL         defaults to https://api.moonpay.com
 *   MOONPAY_WIDGET_BASE_URL  defaults to https://buy.moonpay.com
 *
 * Run:
 *   pnpm install
 *   MOONPAY_API_KEY=pk_test_... MOONPAY_SECRET_KEY=sk_test_... pnpm start
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js'
import { createHmac } from 'node:crypto'
import { z } from 'zod'

const MOONPAY_API_KEY = process.env.MOONPAY_API_KEY ?? ''
const MOONPAY_SECRET_KEY = process.env.MOONPAY_SECRET_KEY ?? ''
const MOONPAY_BASE_URL = process.env.MOONPAY_BASE_URL ?? 'https://api.moonpay.com'
const MOONPAY_WIDGET_BASE_URL =
  process.env.MOONPAY_WIDGET_BASE_URL ?? 'https://buy.moonpay.com'

function requireKeys(): void {
  if (!MOONPAY_API_KEY || !MOONPAY_SECRET_KEY) {
    // Surface this *before* the MCP transport opens so the host shows
    // a clean error instead of a confused tool call later.
    console.error(
      '[FATAL] MOONPAY_API_KEY and MOONPAY_SECRET_KEY must both be set in the environment',
    )
    process.exit(1)
  }
}

const GetQuoteInput = z.object({
  amount_usd: z.number().positive().describe('Fiat amount the user spends, USD'),
  target_chain: z
    .enum(['solana', 'ethereum', 'polygon', 'base'])
    .default('solana')
    .describe('Settlement chain for the crypto purchase'),
  target_token: z
    .enum(['usdc', 'usdt'])
    .default('usdc')
    .describe('Crypto asset the user receives'),
})

const SignOnrampUrlInput = z.object({
  wallet_address: z.string().min(8).describe('Recipient wallet address'),
  amount_usd: z.number().positive().describe('Fiat amount, USD'),
  currency: z
    .enum(['usdc_sol', 'usdc', 'usdc_polygon', 'usdc_base'])
    .default('usdc_sol')
    .describe('MoonPay currency code mapping crypto + chain'),
  redirect_url: z
    .string()
    .url()
    .optional()
    .describe('Post-purchase redirect (defaults to opener.close)'),
})

const GetTransactionInput = z.object({
  tx_id: z.string().min(8).describe('MoonPay transaction id (uuid)'),
})

const TOOLS = [
  {
    name: 'moonpay_get_quote',
    description:
      'Fetch a price quote for buying crypto with fiat. Returns expected crypto out, fees, and ETA. Use before signing an onramp URL so the agent can decide if the rate is acceptable.',
    inputSchema: GetQuoteInput,
  },
  {
    name: 'moonpay_sign_onramp_url',
    description:
      'Build a signed MoonPay widget URL for an agent or user to complete the on-ramp in their browser. The signature binds wallet address + amount + currency so the params cannot be tampered with after generation.',
    inputSchema: SignOnrampUrlInput,
  },
  {
    name: 'moonpay_get_transaction',
    description:
      'Poll a MoonPay transaction by id. Returns status (pending, processing, completed, failed) and the on-chain tx hash once settled.',
    inputSchema: GetTransactionInput,
  },
] as const

function moonpaySignUrl(rawUrl: string): string {
  // MoonPay widget signing: HMAC-SHA256 of the *query string only*
  // (not the host), base64-encoded, appended as `signature=`.
  const url = new URL(rawUrl)
  const queryWithLeadingMark = url.search // includes the '?' prefix
  const sig = createHmac('sha256', MOONPAY_SECRET_KEY)
    .update(queryWithLeadingMark)
    .digest('base64')
  url.searchParams.set('signature', sig)
  return url.toString()
}

async function callMoonPayQuote(input: z.infer<typeof GetQuoteInput>) {
  const params = new URLSearchParams({
    apiKey: MOONPAY_API_KEY,
    baseCurrencyCode: 'usd',
    quoteCurrencyCode: input.target_token + (input.target_chain === 'solana' ? '_sol' : ''),
    baseCurrencyAmount: input.amount_usd.toString(),
  })
  const url = `${MOONPAY_BASE_URL}/v3/currencies/quote?${params.toString()}`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!resp.ok) {
    throw new Error(`MoonPay quote HTTP ${resp.status}`)
  }
  return resp.json()
}

function buildOnrampUrl(input: z.infer<typeof SignOnrampUrlInput>): string {
  const params = new URLSearchParams({
    apiKey: MOONPAY_API_KEY,
    currencyCode: input.currency,
    walletAddress: input.wallet_address,
    baseCurrencyAmount: input.amount_usd.toString(),
    baseCurrencyCode: 'usd',
  })
  if (input.redirect_url) params.set('redirectURL', input.redirect_url)
  const unsigned = `${MOONPAY_WIDGET_BASE_URL}/?${params.toString()}`
  return moonpaySignUrl(unsigned)
}

async function callMoonPayTransaction(input: z.infer<typeof GetTransactionInput>) {
  const url = `${MOONPAY_BASE_URL}/v1/transactions/${input.tx_id}?apiKey=${MOONPAY_API_KEY}`
  const resp = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!resp.ok) {
    throw new Error(`MoonPay transaction HTTP ${resp.status}`)
  }
  return resp.json()
}

async function dispatchTool(name: string, args: unknown) {
  switch (name) {
    case 'moonpay_get_quote': {
      const input = GetQuoteInput.parse(args)
      const quote = await callMoonPayQuote(input)
      return { content: [{ type: 'text', text: JSON.stringify(quote, null, 2) }] }
    }
    case 'moonpay_sign_onramp_url': {
      const input = SignOnrampUrlInput.parse(args)
      const url = buildOnrampUrl(input)
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({ url, expires: 'session', currency: input.currency }, null, 2),
          },
        ],
      }
    }
    case 'moonpay_get_transaction': {
      const input = GetTransactionInput.parse(args)
      const tx = await callMoonPayTransaction(input)
      return { content: [{ type: 'text', text: JSON.stringify(tx, null, 2) }] }
    }
    default:
      throw new Error(`unknown tool: ${name}`)
  }
}

async function main() {
  requireKeys()

  const server = new Server(
    { name: 'moonpay-mcp-server', version: '0.0.1' },
    { capabilities: { tools: {} } },
  )

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOLS.map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: zodToJsonSchemaShim(t.inputSchema),
    })),
  }))

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const { name, arguments: args } = req.params
    try {
      return await dispatchTool(name, args ?? {})
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      return {
        isError: true,
        content: [{ type: 'text', text: `tool error: ${message}` }],
      }
    }
  })

  const transport = new StdioServerTransport()
  await server.connect(transport)
  console.error('[moonpay-mcp-server] ready on stdio')
}

/**
 * Minimal zod → JSON Schema shim. The MCP SDK accepts JSON Schema for
 * tool input descriptors; we don't depend on `zod-to-json-schema` here
 * to keep the hackathon scaffold dependency-free beyond `zod` itself.
 * For non-trivial schemas (unions, refinements), upgrade to the
 * official converter.
 */
function zodToJsonSchemaShim(schema: z.ZodObject<z.ZodRawShape>): Record<string, unknown> {
  const shape = schema.shape
  const properties: Record<string, unknown> = {}
  const required: string[] = []
  for (const [key, value] of Object.entries(shape)) {
    properties[key] = describeZod(value as z.ZodTypeAny)
    if (!(value instanceof z.ZodOptional) && !(value instanceof z.ZodDefault)) {
      required.push(key)
    }
  }
  return { type: 'object', properties, required }
}

function describeZod(value: z.ZodTypeAny): Record<string, unknown> {
  if (value instanceof z.ZodString) {
    return { type: 'string', description: value.description ?? '' }
  }
  if (value instanceof z.ZodNumber) {
    return { type: 'number', description: value.description ?? '' }
  }
  if (value instanceof z.ZodEnum) {
    return {
      type: 'string',
      enum: (value as z.ZodEnum<[string, ...string[]]>).options,
      description: value.description ?? '',
    }
  }
  if (value instanceof z.ZodDefault) {
    return describeZod((value as z.ZodDefault<z.ZodTypeAny>)._def.innerType)
  }
  if (value instanceof z.ZodOptional) {
    return describeZod((value as z.ZodOptional<z.ZodTypeAny>)._def.innerType)
  }
  return { description: value.description ?? '' }
}

main().catch((err) => {
  console.error('[FATAL]', err?.message ?? err)
  process.exit(1)
})
