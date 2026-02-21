import { describe, it, expect } from 'vitest';
import { ethers } from 'ethers';
import { signRequest } from '../erc8128';

// Deterministic test key (DO NOT use in production)
const TEST_PRIVATE_KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80';
const TEST_ADDRESS = '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266';

describe('ERC-8128 Signer', () => {
  it('produces Signature and Signature-Input headers', async () => {
    const headers = await signRequest({
      privateKey: TEST_PRIVATE_KEY,
      method: 'POST',
      url: 'https://api.execution.market/api/v1/tasks',
      body: '{"title":"test"}',
      nonce: 'test-nonce-123',
      chainId: 8453,
    });

    expect(headers.Signature).toMatch(/^eth=:.+:$/);
    expect(headers['Signature-Input']).toMatch(/^eth=\("@method"/);
    expect(headers['Content-Digest']).toMatch(/^sha-256=:.+:$/);
  });

  it('omits Content-Digest for bodyless GET requests', async () => {
    const headers = await signRequest({
      privateKey: TEST_PRIVATE_KEY,
      method: 'GET',
      url: 'https://api.execution.market/api/v1/tasks',
      nonce: 'nonce-456',
    });

    expect(headers.Signature).toMatch(/^eth=:.+:$/);
    expect(headers['Signature-Input']).toBeDefined();
    expect(headers['Content-Digest']).toBeUndefined();
    // Should NOT include content-digest in covered components
    expect(headers['Signature-Input']).not.toContain('content-digest');
  });

  it('includes @query when URL has query string', async () => {
    const headers = await signRequest({
      privateKey: TEST_PRIVATE_KEY,
      method: 'GET',
      url: 'https://api.execution.market/api/v1/tasks?status=published&limit=10',
      nonce: 'nonce-789',
    });

    expect(headers['Signature-Input']).toContain('"@query"');
  });

  it('uses correct keyid format', async () => {
    const headers = await signRequest({
      privateKey: TEST_PRIVATE_KEY,
      method: 'GET',
      url: 'https://api.execution.market/api/v1/health',
      chainId: 137,
    });

    const expectedAddr = TEST_ADDRESS.toLowerCase();
    expect(headers['Signature-Input']).toContain(`keyid="erc8128:137:${expectedAddr}"`);
  });

  it('signature is recoverable to the signer address', async () => {
    const body = '{"title":"verify me"}';
    const headers = await signRequest({
      privateKey: TEST_PRIVATE_KEY,
      method: 'POST',
      url: 'https://api.execution.market/api/v1/tasks',
      body,
      nonce: 'roundtrip-nonce',
      chainId: 8453,
    });

    // Extract base64 signature from header
    const sigMatch = headers.Signature.match(/^eth=:(.+):$/);
    expect(sigMatch).toBeTruthy();
    const sigB64 = sigMatch![1];
    const sigBytes = Buffer.from(sigB64, 'base64');
    const sigHex = ethers.hexlify(sigBytes);

    // Rebuild the signature base (same logic as signer)
    const url = new URL('https://api.execution.market/api/v1/tasks');
    const digest = headers['Content-Digest']!;
    const covered = ['@method', '@authority', '@path', 'content-digest'];
    const inputMatch = headers['Signature-Input'].match(/created=(\d+);expires=(\d+)/);
    const created = parseInt(inputMatch![1]);
    const expires = parseInt(inputMatch![2]);

    const compStr = covered.map((c) => `"${c}"`).join(' ');
    const keyid = `erc8128:8453:${TEST_ADDRESS.toLowerCase()}`;
    const sigParams = `(${compStr});created=${created};expires=${expires};nonce="roundtrip-nonce";keyid="${keyid}"`;

    const lines = [
      `"@method": POST`,
      `"@authority": ${url.host}`,
      `"@path": ${url.pathname}`,
      `"content-digest": ${digest}`,
      `"@signature-params": ${sigParams}`,
    ];
    const sigBase = lines.join('\n');

    // Recover address from signature
    const recovered = ethers.verifyMessage(sigBase, sigHex);
    expect(recovered.toLowerCase()).toBe(TEST_ADDRESS.toLowerCase());
  });
});
