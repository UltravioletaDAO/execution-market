/**
 * OWS MCP Server — Open Wallet Standard for AI Agents
 *
 * Universal MCP server that exposes OWS wallet operations to any MCP client:
 * Claude Code, OpenClaw, Cursor, or any MCP-compatible AI agent.
 *
 * OWS = MetaMask for AI agents.
 * This server = the universal adapter.
 *
 * Challenges addressed:
 *   #4 — Agent identity attestation (ERC-8004 registration via OWS wallet)
 *   #5 — Agent treasury wallet (policy-gated spending)
 *   #6 — MCP wallet server (this is it)
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import * as crypto from "node:crypto";
import * as ows from "@open-wallet-standard/core";
import { OWSWalletAdapter } from "uvd-x402-sdk";
import type { OWSWallet } from "uvd-x402-sdk";
import type { EIP3009Authorization } from "uvd-x402-sdk";

// ---------------------------------------------------------------------------
// OWS → SDK Bridge
// ---------------------------------------------------------------------------

/**
 * Create an OWSWallet-compatible object from @open-wallet-standard/core.
 *
 * The SDK's OWSWalletAdapter expects an object with `accounts`, `signMessage`,
 * and `signTypedData` methods using structured params. The @open-wallet-standard/core
 * module uses a different function-call-based API. This bridge adapts between them.
 *
 * @param walletName - OWS wallet name or ID
 * @param passphrase - Optional wallet passphrase for decryption
 */
function createOWSWalletBridge(walletName: string, passphrase?: string): OWSWallet {
  const info = ows.getWallet(walletName);
  const evmAccount = info.accounts.find((a) => a.chainId.startsWith("eip155:"));

  return {
    accounts: evmAccount
      ? [{ address: evmAccount.address, chains: [evmAccount.chainId] }]
      : [],

    async signMessage(params: {
      account: { address: string };
      message: string | Uint8Array;
    }) {
      const msg =
        typeof params.message === "string"
          ? params.message
          : Buffer.from(params.message).toString("utf-8");
      const result = ows.signMessage(walletName, "evm", msg, passphrase);
      return { signature: result.signature };
    },

    async signTypedData(params: {
      account: { address: string };
      domain: Record<string, unknown>;
      types: Record<string, Array<{ name: string; type: string }>>;
      primaryType: string;
      message: Record<string, unknown>;
    }) {
      // @open-wallet-standard/core expects EIP-712 as a JSON string
      const typedDataJson = JSON.stringify({
        types: {
          EIP712Domain: [
            { name: "name", type: "string" },
            { name: "version", type: "string" },
            { name: "chainId", type: "uint256" },
            { name: "verifyingContract", type: "address" },
          ],
          ...params.types,
        },
        primaryType: params.primaryType,
        domain: params.domain,
        message: params.message,
      });
      const result = ows.signTypedData(walletName, "evm", typedDataJson, passphrase);
      return { signature: result.signature };
    },
  };
}

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------

const server = new McpServer(
  {
    name: "ows-mcp-server",
    version: "0.1.0",
  },
  {
    instructions: [
      "This server manages wallets via the Open Wallet Standard (OWS).",
      "OWS is like MetaMask for AI agents — secure, local, multi-chain.",
      "",
      "Typical onboarding flow for Execution Market:",
      "  1. ows_create_wallet  — create a new multi-chain wallet",
      "  2. ows_register_identity — register ERC-8004 on-chain identity (gasless)",
      "  3. Use wallet address for task creation / escrow signing on execution.market",
      "",
      "All private keys are encrypted locally (AES-256-GCM) and never leave the vault.",
      "Signing operations decrypt the key in memory, sign, then immediately wipe.",
    ].join("\n"),
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_create_wallet
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_create_wallet",
  {
    title: "Create Wallet",
    description:
      "Create a new multi-chain wallet. Generates addresses for EVM, Solana, Bitcoin, " +
      "Cosmos, Tron, TON, Filecoin, and Sui. Private key is encrypted locally.",
    inputSchema: {
      name: z.string().describe("Wallet name, e.g. 'my-agent' or 'treasury'"),
      passphrase: z
        .string()
        .optional()
        .describe("Optional passphrase for extra encryption"),
    },
  },
  async ({ name, passphrase }) => {
    try {
      const wallet = ows.createWallet(name, passphrase ?? undefined);
      const accounts = wallet.accounts.map((a) => ({
        chain: a.chainId,
        address: a.address,
      }));

      // Find the EVM address specifically (most common for EM)
      const evmAccount = wallet.accounts.find((a) =>
        a.chainId.startsWith("eip155:")
      );

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                success: true,
                wallet_id: wallet.id,
                wallet_name: wallet.name,
                evm_address: evmAccount?.address ?? null,
                accounts,
                next_step:
                  "Use ows_register_identity to register your ERC-8004 on-chain identity (gasless).",
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Failed to create wallet: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_list_wallets
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_list_wallets",
  {
    title: "List Wallets",
    description: "List all OWS wallets stored locally.",
    inputSchema: {},
  },
  async () => {
    try {
      const wallets = ows.listWallets();
      const summary = wallets.map((w) => {
        const evmAccount = w.accounts.find((a) =>
          a.chainId.startsWith("eip155:")
        );
        return {
          id: w.id,
          name: w.name,
          evm_address: evmAccount?.address ?? null,
          chains: w.accounts.length,
        };
      });

      return {
        content: [
          {
            type: "text" as const,
            text:
              wallets.length === 0
                ? "No wallets found. Use ows_create_wallet to create one."
                : JSON.stringify(summary, null, 2),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Failed to list wallets: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_get_wallet
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_get_wallet",
  {
    title: "Get Wallet",
    description:
      "Get details of a specific wallet by name or ID, including all chain addresses.",
    inputSchema: {
      wallet: z.string().describe("Wallet name or ID"),
    },
  },
  async ({ wallet }) => {
    try {
      const info = ows.getWallet(wallet);
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                id: info.id,
                name: info.name,
                created_at: info.createdAt,
                accounts: info.accounts.map((a) => ({
                  chain: a.chainId,
                  address: a.address,
                  derivation_path: a.derivationPath,
                })),
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Wallet not found: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_sign_message
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_sign_message",
  {
    title: "Sign Message",
    description:
      "Sign a message using a wallet. Supports EVM, Solana, and other chains.",
    inputSchema: {
      wallet: z.string().describe("Wallet name or ID"),
      chain: z
        .enum(["evm", "solana", "bitcoin", "cosmos", "tron", "ton", "sui", "filecoin"])
        .describe("Chain to sign for"),
      message: z.string().describe("Message to sign"),
      passphrase: z
        .string()
        .optional()
        .describe("Wallet passphrase if set during creation"),
    },
  },
  async ({ wallet, chain, message, passphrase }) => {
    try {
      const result = ows.signMessage(
        wallet,
        chain,
        message,
        passphrase ?? undefined
      );

      // Normalize v byte: OWS returns recoveryId 0/1, EVM expects 27/28
      const v =
        result.recoveryId !== undefined &&
        result.recoveryId !== null &&
        result.recoveryId < 27
          ? result.recoveryId + 27
          : result.recoveryId ?? 27;

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                signature: result.signature,
                v,
                recovery_id: result.recoveryId ?? null,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Signing failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_sign_typed_data (EIP-712)
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_sign_typed_data",
  {
    title: "Sign EIP-712 Typed Data",
    description:
      "Sign EIP-712 typed structured data (EVM only). Used for gasless operations " +
      "like EIP-3009 ReceiveWithAuthorization (USDC transfers), permits, and more.",
    inputSchema: {
      wallet: z.string().describe("Wallet name or ID"),
      typed_data: z
        .string()
        .describe(
          "EIP-712 typed data as JSON string. Must include types, primaryType, domain, and message."
        ),
      passphrase: z
        .string()
        .optional()
        .describe("Wallet passphrase if set during creation"),
    },
  },
  async ({ wallet, typed_data, passphrase }) => {
    try {
      const result = ows.signTypedData(
        wallet,
        "evm",
        typed_data,
        passphrase ?? undefined
      );

      // Extract v, r, s from the 65-byte signature
      const sigHex = result.signature.startsWith("0x")
        ? result.signature.slice(2)
        : result.signature;
      const r = "0x" + sigHex.slice(0, 64);
      const s = "0x" + sigHex.slice(64, 128);
      // v is either in the last byte or from recoveryId
      // Normalize: OWS returns recoveryId 0/1, EVM expects 27/28
      const rawV =
        result.recoveryId !== undefined && result.recoveryId !== null
          ? result.recoveryId
          : parseInt(sigHex.slice(128, 130), 16);
      const v = rawV < 27 ? rawV + 27 : rawV;

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                signature: "0x" + sigHex,
                v,
                r,
                s,
                recovery_id: result.recoveryId ?? null,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `EIP-712 signing failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_sign_eip191 (EIP-191 Personal Sign — required for ERC-8128 auth)
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_sign_eip191",
  {
    title: "Sign Message (EIP-191 Personal Sign)",
    description:
      "Sign a message with EIP-191 prefix (\\x19Ethereum Signed Message). " +
      "Required for ERC-8128 HTTP auth. Regular ows_sign_message does NOT add this prefix, " +
      "which causes signature verification to fail (401) on servers that use personal_sign recovery.",
    inputSchema: {
      wallet: z.string().describe("OWS wallet name or ID"),
      message: z.string().describe("Message to sign (EIP-191 prefix added automatically)"),
      passphrase: z
        .string()
        .optional()
        .describe("Wallet passphrase if set"),
    },
  },
  async ({ wallet, message, passphrase }) => {
    try {
      // Delegate to shared helper (defined below, hoisted at runtime)
      const { signature, v, r, s } = signEip191WithOws(
        wallet,
        message,
        passphrase ?? undefined,
      );

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                signature,
                v,
                r,
                s,
                message_signed: message,
                prefix_applied: true,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `EIP-191 signing failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_sign_transaction
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_sign_transaction",
  {
    title: "Sign Transaction",
    description: "Sign a raw transaction. Returns the signed transaction hex.",
    inputSchema: {
      wallet: z.string().describe("Wallet name or ID"),
      chain: z
        .enum(["evm", "solana", "bitcoin", "cosmos", "tron", "ton", "sui", "filecoin"])
        .describe("Chain to sign for"),
      tx_hex: z.string().describe("Raw transaction as hex string"),
      passphrase: z
        .string()
        .optional()
        .describe("Wallet passphrase if set during creation"),
    },
  },
  async ({ wallet, chain, tx_hex, passphrase }) => {
    try {
      const result = ows.signTransaction(
        wallet,
        chain,
        tx_hex,
        passphrase ?? undefined
      );
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                signature: result.signature,
                recovery_id: result.recoveryId ?? null,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Transaction signing failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_register_identity (ERC-8004 via Execution Market Facilitator)
// ---------------------------------------------------------------------------

const FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz";

server.registerTool(
  "ows_register_identity",
  {
    title: "Register On-Chain Identity",
    description:
      "Register an ERC-8004 on-chain identity for your wallet — completely gasless. " +
      "The Ultravioleta Facilitator pays the gas. Returns your Agent ID (e.g. Agent #2201). " +
      "Required before publishing tasks on Execution Market.",
    inputSchema: {
      wallet: z.string().describe("OWS wallet name or ID"),
      agent_name: z
        .string()
        .describe("Display name for your agent (e.g. 'MyBot', 'ResearchAgent')"),
      network: z
        .string()
        .optional()
        .default("base")
        .describe("Network to register on (default: base)"),
    },
  },
  async ({ wallet, agent_name, network }) => {
    try {
      // Create OWSWalletAdapter via the SDK bridge for address resolution
      const owsBridge = createOWSWalletBridge(wallet);
      let adapter: OWSWalletAdapter;
      try {
        adapter = new OWSWalletAdapter(owsBridge);
      } catch {
        return {
          content: [
            {
              type: "text" as const,
              text: "No EVM account found in wallet. ERC-8004 requires an EVM address.",
            },
          ],
          isError: true,
        };
      }

      const evmAddress = adapter.getAddress();

      // Call the Facilitator to register (gasless)
      // Note: SDK doesn't wrap /register yet, so we keep the direct fetch
      const res = await fetch(`${FACILITATOR_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          x402Version: 1,
          network: network ?? "base",
          recipient: evmAddress,
          agentUri: `https://execution.market/agents/${evmAddress.toLowerCase()}`,
          name: agent_name,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Registration failed (${res.status}): ${JSON.stringify(data)}`,
            },
          ],
          isError: true,
        };
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                success: true,
                agent_id: data.agent_id ?? data.tokenId ?? null,
                wallet_address: evmAddress,
                network: network ?? "base",
                message:
                  "Identity registered on-chain (gasless). You can now publish tasks on Execution Market.",
                next_step:
                  "Create a task at https://api.execution.market/api/v1/tasks",
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Registration failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_sign_eip3009 (EIP-3009 via uvd-x402-sdk OWSWalletAdapter)
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_sign_eip3009",
  {
    title: "Sign EIP-3009 USDC Authorization",
    description:
      "Sign an EIP-3009 ReceiveWithAuthorization for USDC — used for gasless escrow " +
      "deposits on Execution Market. The Facilitator executes the on-chain transfer. " +
      "Agent signs, never pays gas. " +
      "Powered by uvd-x402-sdk (chain registry, USDC addresses, nonce generation handled automatically).",
    inputSchema: {
      wallet: z.string().describe("OWS wallet name or ID"),
      to: z.string().describe("Recipient address (escrow contract or worker wallet)"),
      amount_usdc: z
        .number()
        .positive()
        .describe("Amount in USDC (e.g. 0.10 for ten cents)"),
      network: z
        .string()
        .optional()
        .default("base")
        .describe("Payment network (default: base). Supports all SDK chains."),
      valid_before: z
        .number()
        .optional()
        .describe("Unix timestamp when authorization expires (default: 5 minutes from now per SDK)"),
      passphrase: z
        .string()
        .optional()
        .describe("Wallet passphrase if set during creation"),
    },
  },
  async ({ wallet, to, amount_usdc, network, valid_before, passphrase }) => {
    try {
      const chain = network ?? "base";

      // Create the SDK adapter via the OWS bridge
      const owsBridge = createOWSWalletBridge(wallet, passphrase ?? undefined);
      let adapter: OWSWalletAdapter;
      try {
        adapter = new OWSWalletAdapter(owsBridge);
      } catch {
        return {
          content: [
            {
              type: "text" as const,
              text: "No EVM account in wallet.",
            },
          ],
          isError: true,
        };
      }

      // Delegate all EIP-3009 logic to the SDK:
      // - Chain registry lookup (USDC address, chainId, decimals)
      // - EIP-712 typed data construction
      // - Nonce generation
      // - Signing via OWS
      // - v/r/s extraction
      const auth: EIP3009Authorization = await adapter.signEIP3009({
        to,
        amountUsdc: amount_usdc,
        network: chain,
        ...(valid_before !== undefined ? { validBefore: valid_before } : {}),
      });

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                success: true,
                authorization: {
                  from: auth.from,
                  to: auth.to,
                  value: auth.value,
                  validAfter: auth.validAfter,
                  validBefore: auth.validBefore,
                  nonce: auth.nonce,
                  v: auth.v,
                  r: auth.r,
                  s: auth.s,
                  signature: auth.signature,
                },
                network: chain,
                amount_usdc,
                note: "Send this authorization to the Facilitator or include as X-Payment-Auth header.",
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `EIP-3009 signing failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Tool: ows_import_wallet (import existing private key)
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_import_wallet",
  {
    title: "Import Wallet from Private Key",
    description:
      "Import an existing private key into OWS. The key is encrypted and stored locally. " +
      "Supports EVM and Solana keys.",
    inputSchema: {
      name: z.string().describe("Name for the imported wallet"),
      private_key: z
        .string()
        .describe("Hex-encoded private key (with or without 0x prefix)"),
      chain: z
        .enum(["evm", "solana"])
        .optional()
        .default("evm")
        .describe("Source chain of the key (default: evm)"),
      passphrase: z
        .string()
        .optional()
        .describe("Optional passphrase for encryption"),
    },
  },
  async ({ name, private_key, chain, passphrase }) => {
    try {
      const key = private_key.startsWith("0x")
        ? private_key.slice(2)
        : private_key;

      const wallet = ows.importWalletPrivateKey(
        name,
        key,
        passphrase ?? undefined,
        undefined,
        chain ?? "evm"
      );

      const evmAccount = wallet.accounts.find((a) =>
        a.chainId.startsWith("eip155:")
      );

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                success: true,
                wallet_id: wallet.id,
                wallet_name: wallet.name,
                evm_address: evmAccount?.address ?? null,
                chains: wallet.accounts.length,
                note: "Key is now encrypted in OWS vault. You can delete the original.",
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Import failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Helper: EIP-191 sign via OWS (shared by ows_sign_eip191 and ows_sign_erc8128_request)
// ---------------------------------------------------------------------------

function signEip191WithOws(
  walletName: string,
  message: string,
  passphrase?: string
): { signature: string; v: number; r: string; s: string } {
  const messageBytes = Buffer.from(message, "utf-8");
  const prefix = `\x19Ethereum Signed Message:\n${messageBytes.length}`;
  const prefixedMessage = Buffer.concat([
    Buffer.from(prefix, "utf-8"),
    messageBytes,
  ]);
  const prefixedHex = prefixedMessage.toString("hex");

  const result = ows.signMessage(
    walletName,
    "evm",
    prefixedHex,
    passphrase,
    "hex",
  );

  const sigHex = result.signature.startsWith("0x")
    ? result.signature.slice(2)
    : result.signature;
  const r = "0x" + sigHex.slice(0, 64);
  const s = "0x" + sigHex.slice(64, 128);
  const rawV =
    result.recoveryId !== undefined && result.recoveryId !== null
      ? result.recoveryId
      : parseInt(sigHex.slice(128, 130), 16);
  const v = rawV < 27 ? rawV + 27 : rawV;

  // Reconstruct the full 65-byte signature with correct v
  const fullSig = "0x" + sigHex.slice(0, 128) + v.toString(16);

  return { signature: fullSig, v, r, s };
}

// ---------------------------------------------------------------------------
// Helper: Build RFC 9421 signature base (matches Python EM8128Client exactly)
// ---------------------------------------------------------------------------

function buildRfc9421SignatureBase(
  method: string,
  url: string,
  body: string | undefined,
  nonce: string,
  chainId: number,
  walletAddress: string,
): {
  signatureBase: string;
  signatureParams: string;
  contentDigest: string | null;
} {
  const parsed = new URL(url);
  const created = Math.floor(Date.now() / 1000);
  const expires = created + 300;

  const covered: string[] = ["@method", "@authority", "@path"];

  let contentDigest: string | null = null;

  if (parsed.search && parsed.search.length > 1) {
    covered.push("@query");
  }

  if (body) {
    const bodyBytes = Buffer.from(body, "utf-8");
    const sha256 = crypto.createHash("sha256").update(bodyBytes).digest("base64");
    contentDigest = `sha-256=:${sha256}:`;
    covered.push("content-digest");
  }

  const params: Record<string, string | number> = {
    created,
    expires,
    nonce,
    keyid: `erc8128:${chainId}:${walletAddress}`,
    alg: "eip191",
  };

  // Build @signature-params string (matches Python _build_sig_params exactly)
  const compStr = covered.map((c) => `"${c}"`).join(" ");
  const parts: string[] = [`(${compStr})`];
  // Ordered keys first: created, expires, nonce, keyid
  for (const key of ["created", "expires", "nonce", "keyid"]) {
    if (key in params) {
      const val = params[key];
      parts.push(typeof val === "number" ? `${key}=${val}` : `${key}="${val}"`);
    }
  }
  // Then remaining keys sorted
  for (const key of Object.keys(params).sort()) {
    if (!["created", "expires", "nonce", "keyid"].includes(key)) {
      const val = params[key];
      parts.push(typeof val === "number" ? `${key}=${val}` : `${key}="${val}"`);
    }
  }
  const signatureParams = parts.join(";");

  // Build the signature base lines
  const lines: string[] = [];
  for (const comp of covered) {
    switch (comp) {
      case "@method":
        lines.push(`"@method": ${method.toUpperCase()}`);
        break;
      case "@authority":
        lines.push(`"@authority": ${parsed.host}`);
        break;
      case "@path":
        lines.push(`"@path": ${parsed.pathname}`);
        break;
      case "@query":
        lines.push(`"@query": ?${parsed.search.slice(1)}`);
        break;
      case "content-digest":
        lines.push(`"content-digest": ${contentDigest}`);
        break;
    }
  }
  lines.push(`"@signature-params": ${signatureParams}`);

  return {
    signatureBase: lines.join("\n"),
    signatureParams,
    contentDigest,
  };
}

// ---------------------------------------------------------------------------
// Tool: ows_sign_erc8128_request (complete ERC-8128 auth flow)
// ---------------------------------------------------------------------------

server.registerTool(
  "ows_sign_erc8128_request",
  {
    title: "Sign ERC-8128 HTTP Request",
    description:
      "Sign an HTTP request with ERC-8128 wallet authentication. Returns ready-to-use " +
      "Signature + Signature-Input + Content-Digest headers. Fetches nonce automatically. " +
      "This is the one-call-does-everything tool for authenticated API requests to Execution Market.",
    inputSchema: {
      wallet: z.string().describe("OWS wallet name"),
      method: z
        .enum(["GET", "POST", "PUT", "DELETE"])
        .describe("HTTP method"),
      url: z
        .string()
        .describe("Full URL (e.g. https://api.execution.market/api/v1/tasks)"),
      body: z
        .string()
        .optional()
        .describe("Request body JSON string (for POST/PUT)"),
      chain_id: z
        .number()
        .optional()
        .default(8453)
        .describe("Chain ID (default: 8453 = Base)"),
      passphrase: z
        .string()
        .optional()
        .describe("Wallet passphrase if set"),
    },
  },
  async ({ wallet, method, url, body, chain_id, passphrase }) => {
    try {
      // 1. Get wallet address from OWS
      const info = ows.getWallet(wallet);
      const evmAccount = info.accounts.find((a) =>
        a.chainId.startsWith("eip155:")
      );
      if (!evmAccount) {
        return {
          content: [
            {
              type: "text" as const,
              text: "No EVM account found in wallet. ERC-8128 requires an EVM address.",
            },
          ],
          isError: true,
        };
      }
      const walletAddress = evmAccount.address;

      // 2. Determine the API base URL from the request URL
      const parsed = new URL(url);
      const apiBase = `${parsed.protocol}//${parsed.host}`;

      // 3. Fetch nonce from the ERC-8128 nonce endpoint
      const nonceRes = await fetch(
        `${apiBase}/api/v1/auth/erc8128/nonce`
      );
      if (!nonceRes.ok) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Failed to fetch nonce (${nonceRes.status}): ${await nonceRes.text()}`,
            },
          ],
          isError: true,
        };
      }
      const nonceData = await nonceRes.json() as { nonce: string };
      const nonce = nonceData.nonce;

      // 4. Build RFC 9421 signature base
      const chainId = chain_id ?? 8453;
      const { signatureBase, signatureParams, contentDigest } =
        buildRfc9421SignatureBase(
          method,
          url,
          body ?? undefined,
          nonce,
          chainId,
          walletAddress,
        );

      // 5. Sign with EIP-191 (same as EM8128Client: encode_defunct + sign)
      const { signature } = signEip191WithOws(
        wallet,
        signatureBase,
        passphrase ?? undefined,
      );

      // 6. Base64-encode the raw signature bytes (65 bytes: r + s + v)
      const sigHex = signature.startsWith("0x")
        ? signature.slice(2)
        : signature;
      const sigBytes = Buffer.from(sigHex, "hex");
      const sigB64 = sigBytes.toString("base64");

      // 7. Build the headers
      const headers: Record<string, string> = {
        Signature: `eth=:${sigB64}:`,
        "Signature-Input": `eth=${signatureParams}`,
      };
      if (contentDigest) {
        headers["Content-Digest"] = contentDigest;
      }

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                success: true,
                headers,
                wallet_address: walletAddress,
                chain_id: chainId,
                note:
                  "Add these headers to your HTTP request. " +
                  "For POST/PUT, also include Content-Type: application/json.",
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `ERC-8128 signing failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[ows-mcp-server] Running on stdio — 10 tools available");
  console.error("[ows-mcp-server] Wallet vault: ~/.ows/wallets/");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
