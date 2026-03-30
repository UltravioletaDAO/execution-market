import { privateKeyToAccount } from "viem/accounts";

const PRIVATE_KEY = "PRIVATE_KEY_REMOVED_INC_2026_03_30";
const WALLET_ADDRESS = "0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15";
const CHAIN_ID = 8453; // Base
const TASK_ID = "9eba6a3c-71cf-4c2c-85d2-d675878db14e";
const BASE_URL = "https://api.execution.market";
const METHOD = "GET";
const PATH = `/api/v1/tasks/${TASK_ID}/submissions`;

// Use ERC-8128 specific nonce endpoint
const nonceRes = await fetch(`${BASE_URL}/api/v1/auth/erc8128/nonce`);
const nonceData = await nonceRes.json();
const nonce = nonceData.nonce;
console.error("Nonce:", nonce);

const account = privateKeyToAccount(PRIVATE_KEY);
const created = Math.floor(Date.now() / 1000);
const expires = created + 300;

// keyid format: erc8128:{chain_id}:{address}
const keyid = `erc8128:${CHAIN_ID}:${WALLET_ADDRESS}`;
// label is "eth" per info endpoint
const signatureInput = `eth=("@method" "@authority" "@path");created=${created};expires=${expires};nonce="${nonce}";keyid="${keyid}"`;
const sigBase = [
  `"@method": ${METHOD}`,
  `"@authority": api.execution.market`,
  `"@path": ${PATH}`,
  `"@signature-params": ${signatureInput}`
].join("\n");

console.error("SigBase:", sigBase);

const signature = await account.signMessage({ message: sigBase });
const sigB64 = Buffer.from(signature.slice(2), "hex").toString("base64");

const headers = {
  "Signature-Input": signatureInput,
  "Signature": `eth=:${sigB64}:`,
};

console.error("Headers:", JSON.stringify(headers, null, 2));

const res = await fetch(`${BASE_URL}${PATH}`, { method: METHOD, headers });
const body = await res.text();
console.log(JSON.stringify({ status: res.status, body: JSON.parse(body) }, null, 2));
