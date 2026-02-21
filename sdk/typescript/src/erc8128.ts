/**
 * ERC-8128 HTTP Message Signature Signer
 *
 * Signs HTTP requests per ERC-8128 (Signed HTTP Requests with Ethereum).
 *
 * Flow:
 *   1. Fetch a fresh nonce from the server's /auth/erc8128/nonce endpoint
 *   2. Build RFC 9421 signature base from request components
 *   3. Sign with EIP-191 personal_sign
 *   4. Produce Signature + Signature-Input headers
 *
 * @example
 * ```typescript
 * import { signRequest, fetchNonce } from '@execution-market/sdk/erc8128';
 *
 * const nonce = await fetchNonce('https://api.execution.market');
 * const headers = await signRequest({
 *   privateKey: '0x...',
 *   method: 'POST',
 *   url: 'https://api.execution.market/api/v1/tasks',
 *   body: '{"title": "test"}',
 *   nonce,
 *   chainId: 8453,
 * });
 * // headers = { Signature: '...', 'Signature-Input': '...', 'Content-Digest': '...' }
 * ```
 *
 * Reference:
 *   - ERC-8128: https://eip.tools/eip/8128
 *   - RFC 9421: https://www.rfc-editor.org/rfc/rfc9421
 *   - ERC-191: https://eips.ethereum.org/EIPS/eip-191
 */

import { ethers } from 'ethers';

/** Default label for ERC-8128 signatures */
const DEFAULT_LABEL = 'eth';

/** Default validity window (seconds) */
const DEFAULT_VALIDITY_SEC = 300;

export interface SignRequestOptions {
  /** Hex-encoded private key (with or without 0x prefix) */
  privateKey: string;
  /** HTTP method (GET, POST, etc.) */
  method: string;
  /** Full URL of the request */
  url: string;
  /** Request body (for POST/PUT/PATCH). Omit for bodyless requests. */
  body?: string;
  /** Single-use nonce from the server. Required by most servers. */
  nonce?: string;
  /** EVM chain ID for the keyid (default: 8453 = Base) */
  chainId?: number;
  /** Signature label (default: "eth") */
  label?: string;
  /** Signature validity window in seconds (default: 300) */
  validitySec?: number;
}

export interface SignatureHeaders {
  Signature: string;
  'Signature-Input': string;
  'Content-Digest'?: string;
}

/**
 * Sign an HTTP request per ERC-8128.
 *
 * @returns Headers to merge into the request (Signature, Signature-Input, Content-Digest).
 */
export async function signRequest(options: SignRequestOptions): Promise<SignatureHeaders> {
  const {
    privateKey,
    method,
    url,
    body,
    nonce,
    chainId = 8453,
    label = DEFAULT_LABEL,
    validitySec = DEFAULT_VALIDITY_SEC,
  } = options;

  const wallet = new ethers.Wallet(privateKey);
  const address = wallet.address.toLowerCase();

  const parsed = new URL(url);
  const authority = parsed.host;
  const path = parsed.pathname || '/';
  const query = parsed.search || undefined; // includes '?' prefix

  const now = Math.floor(Date.now() / 1000);
  const created = now;
  const expires = now + validitySec;

  const keyid = `erc8128:${chainId}:${address}`;

  // Determine covered components
  const covered: string[] = ['@method', '@authority', '@path'];
  if (query) {
    covered.push('@query');
  }

  const headers: SignatureHeaders = {
    Signature: '',
    'Signature-Input': '',
  };

  if (body !== undefined) {
    const digest = computeContentDigest(body);
    headers['Content-Digest'] = digest;
    covered.push('content-digest');
  }

  // Build signature base
  const sigBase = buildSignatureBase({
    method,
    authority,
    path,
    query,
    contentDigest: headers['Content-Digest'],
    covered,
    created,
    expires,
    nonce,
    keyid,
  });

  // EIP-191 personal_sign
  const sigBytes = await wallet.signMessage(sigBase);

  // Convert hex signature to base64 (RFC 8941 byte sequence)
  const sigBuffer = ethers.getBytes(sigBytes);
  const sigB64 = Buffer.from(sigBuffer).toString('base64');

  // Build headers
  const sigParams = buildSignatureParams({ covered, created, expires, nonce, keyid });

  headers.Signature = `${label}=:${sigB64}:`;
  headers['Signature-Input'] = `${label}=${sigParams}`;

  return headers;
}

/**
 * Fetch a fresh single-use nonce from the server.
 */
export async function fetchNonce(apiBase: string, timeoutMs = 10000): Promise<string> {
  const url = `${apiBase.replace(/\/$/, '')}/api/v1/auth/erc8128/nonce`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const resp = await fetch(url, { signal: controller.signal });
    if (!resp.ok) {
      throw new Error(`Failed to fetch nonce: ${resp.status} ${resp.statusText}`);
    }
    const data = await resp.json();
    return data.nonce;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Create a fetch wrapper that auto-signs requests with ERC-8128.
 *
 * @example
 * ```typescript
 * const signedFetch = createSignedFetch({
 *   privateKey: '0x...',
 *   apiBase: 'https://api.execution.market',
 *   chainId: 8453,
 * });
 *
 * const resp = await signedFetch('/api/v1/tasks', {
 *   method: 'POST',
 *   body: JSON.stringify({ title: 'test' }),
 * });
 * ```
 */
export function createSignedFetch(config: {
  privateKey: string;
  apiBase: string;
  chainId?: number;
}) {
  return async (path: string, init?: RequestInit): Promise<Response> => {
    const url = `${config.apiBase.replace(/\/$/, '')}${path}`;
    const method = (init?.method || 'GET').toUpperCase();
    const body = init?.body ? String(init.body) : undefined;

    // Fetch nonce
    const nonce = await fetchNonce(config.apiBase);

    // Sign request
    const sigHeaders = await signRequest({
      privateKey: config.privateKey,
      method,
      url,
      body,
      nonce,
      chainId: config.chainId,
    });

    // Merge headers
    const headers = new Headers(init?.headers);
    headers.set('Signature', sigHeaders.Signature);
    headers.set('Signature-Input', sigHeaders['Signature-Input']);
    if (sigHeaders['Content-Digest']) {
      headers.set('Content-Digest', sigHeaders['Content-Digest']);
    }
    if (body) {
      headers.set('Content-Type', headers.get('Content-Type') || 'application/json');
    }

    return fetch(url, { ...init, headers, method });
  };
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function computeContentDigest(body: string): string {
  const hash = ethers.sha256(ethers.toUtf8Bytes(body));
  // hash is 0x-prefixed hex, convert to raw bytes then base64
  const hashBytes = ethers.getBytes(hash);
  const b64 = Buffer.from(hashBytes).toString('base64');
  return `sha-256=:${b64}:`;
}

interface SignatureBaseParams {
  method: string;
  authority: string;
  path: string;
  query?: string;
  contentDigest?: string;
  covered: string[];
  created: number;
  expires: number;
  nonce?: string;
  keyid: string;
}

function buildSignatureBase(params: SignatureBaseParams): string {
  const lines: string[] = [];

  for (const component of params.covered) {
    switch (component) {
      case '@method':
        lines.push(`"@method": ${params.method.toUpperCase()}`);
        break;
      case '@authority':
        lines.push(`"@authority": ${params.authority}`);
        break;
      case '@path':
        lines.push(`"@path": ${params.path}`);
        break;
      case '@query':
        lines.push(`"@query": ${params.query || '?'}`);
        break;
      case 'content-digest':
        lines.push(`"content-digest": ${params.contentDigest || ''}`);
        break;
    }
  }

  const sigParams = buildSignatureParams({
    covered: params.covered,
    created: params.created,
    expires: params.expires,
    nonce: params.nonce,
    keyid: params.keyid,
  });
  lines.push(`"@signature-params": ${sigParams}`);

  return lines.join('\n');
}

interface SignatureParamsInput {
  covered: string[];
  created: number;
  expires: number;
  nonce?: string;
  keyid: string;
}

function buildSignatureParams(params: SignatureParamsInput): string {
  const compStr = params.covered.map((c) => `"${c}"`).join(' ');
  const parts: string[] = [`(${compStr})`];
  parts.push(`created=${params.created}`);
  parts.push(`expires=${params.expires}`);
  if (params.nonce) {
    parts.push(`nonce="${params.nonce}"`);
  }
  parts.push(`keyid="${params.keyid}"`);
  return parts.join(';');
}
