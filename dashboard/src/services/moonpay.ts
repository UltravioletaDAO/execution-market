/**
 * MoonPay Headless Onramp client.
 *
 * Talks to the EM backend at `/api/v1/moonpay/*` — never to api.moonpay.com
 * directly. The backend holds sk_test_* / sk_live_* and HMAC-signs the
 * Widget URL the frontend overlay hands to `widget.show()`.
 *
 * Phase 4.8: the canonical surface is `requestMoonPaySignedUrl` (URL-signing).
 * `createMoonPaySession` remains for the existing `/spike/moonpay` smoke page
 * until the `/session` route is retired.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

/**
 * 402 INSUFFICIENT_FUNDS onramp payload returned by the backend when an
 * agent's Solana USDC balance is below `bounty + fee`. Same shape lives in
 * `mcp_server/integrations/moonpay/onramp.py::build_insufficient_funds_onramp`.
 *
 * `qty_needed` is a string because the backend serializes Decimal to avoid
 * float precision loss. `signature` is the HMAC fragment also embedded in
 * `url`; the JS SDK accepts it via `widget.updateSignature(signature)` so
 * the overlay can verify against MoonPay's server.
 */
export interface OnrampPayload {
  url: string
  signature: string
  qty_needed: string
  currency: string
}

export interface SignUrlParams {
  walletAddress: string
  baseCurrencyAmount: number
  currencyCode?: string
  baseCurrencyCode?: string
  externalCustomerId?: string
  redirectUrl?: string
  colorCode?: string
  theme?: 'light' | 'dark'
}

export interface MoonPaySession {
  session_token: string
  public_key: string
  expires_in_seconds: number
}

export interface MoonPayHealth {
  enabled: boolean
  secret_key_configured: boolean
  public_key_configured: boolean
  webhook_secret_configured: boolean
  api_base_url: string
}

export class MoonPayError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
    this.name = 'MoonPayError'
  }
}

/**
 * Ask the backend to HMAC-sign a MoonPay Widget URL. The returned `url`
 * is bearer-like: every query param is in the signed payload, so anyone
 * with the URL can initiate a buy that debits our MoonPay account. Never
 * log it; hand it straight to `<MoonPayFrame>` or `widget.show()`.
 */
export async function requestMoonPaySignedUrl(
  params: SignUrlParams,
): Promise<OnrampPayload> {
  const resp = await fetch(`${API_BASE}/api/v1/moonpay/sign-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      wallet_address: params.walletAddress,
      base_currency_amount: params.baseCurrencyAmount,
      currency_code: params.currencyCode ?? 'usdc_sol',
      base_currency_code: params.baseCurrencyCode ?? 'usd',
      external_customer_id: params.externalCustomerId,
      redirect_url: params.redirectUrl,
      color_code: params.colorCode,
      theme: params.theme,
    }),
  })

  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }))
    throw new MoonPayError(data.detail || `HTTP ${resp.status}`, resp.status)
  }

  const body = (await resp.json()) as {
    url: string
    currency_code: string
    wallet_address: string
  }

  // The /sign-url endpoint returns only the signed URL; pull the
  // signature back out of the query string so the frontend can call
  // widget.updateSignature() independently if it wants to.
  const signature = new URL(body.url).searchParams.get('signature') ?? ''

  return {
    url: body.url,
    signature,
    qty_needed: String(params.baseCurrencyAmount),
    currency: body.currency_code,
  }
}

/**
 * Legacy session-based init (Phase 1D `/spike/moonpay`). Kept around until
 * the backend `/session` route is retired.
 */
export async function createMoonPaySession(
  externalCustomerId: string,
  deviceIp?: string,
): Promise<MoonPaySession> {
  const resp = await fetch(`${API_BASE}/api/v1/moonpay/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      external_customer_id: externalCustomerId,
      device_ip: deviceIp ?? null,
    }),
  })

  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }))
    throw new MoonPayError(data.detail || `HTTP ${resp.status}`, resp.status)
  }
  return resp.json()
}

/**
 * Probe `/api/v1/moonpay/health`. Returns null if the endpoint is 404
 * (master switch OFF on the backend) — same shape as VeryAI/ClawKey health.
 */
export async function getMoonPayHealth(): Promise<MoonPayHealth | null> {
  const resp = await fetch(`${API_BASE}/api/v1/moonpay/health`)
  if (resp.status === 404) return null
  if (!resp.ok) {
    throw new MoonPayError(`HTTP ${resp.status}`, resp.status)
  }
  return resp.json()
}
