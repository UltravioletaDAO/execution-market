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
import * as ows from "@open-wallet-standard/core";

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
      const v =
        result.recoveryId !== undefined && result.recoveryId !== null
          ? result.recoveryId
          : parseInt(sigHex.slice(128, 130), 16);

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
      // Get the EVM address from the wallet
      const info = ows.getWallet(wallet);
      const evmAccount = info.accounts.find((a) =>
        a.chainId.startsWith("eip155:")
      );
      if (!evmAccount) {
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

      // Call the Facilitator to register (gasless)
      const res = await fetch(`${FACILITATOR_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          x402Version: 1,
          network: network ?? "base",
          recipient: evmAccount.address,
          agentUri: `https://execution.market/agents/${evmAccount.address.toLowerCase()}`,
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
                wallet_address: evmAccount.address,
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
// Tool: ows_sign_eip3009 (EIP-3009 ReceiveWithAuthorization for USDC escrow)
// ---------------------------------------------------------------------------

// USDC contract addresses per chain
const USDC_CONTRACTS: Record<string, { address: string; chainId: number }> = {
  base: { address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", chainId: 8453 },
  ethereum: { address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chainId: 1 },
  polygon: { address: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", chainId: 137 },
  arbitrum: { address: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", chainId: 42161 },
  avalanche: { address: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", chainId: 43114 },
  optimism: { address: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", chainId: 10 },
  celo: { address: "0xcebA9300f2b948710d2653dD7B07f33A8B32118C", chainId: 42220 },
};

server.registerTool(
  "ows_sign_eip3009",
  {
    title: "Sign EIP-3009 USDC Authorization",
    description:
      "Sign an EIP-3009 ReceiveWithAuthorization for USDC — used for gasless escrow " +
      "deposits on Execution Market. The Facilitator executes the on-chain transfer. " +
      "Agent signs, never pays gas.",
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
        .describe("Payment network (default: base)"),
      valid_before: z
        .number()
        .optional()
        .describe("Unix timestamp when authorization expires (default: 1 hour from now)"),
      passphrase: z
        .string()
        .optional()
        .describe("Wallet passphrase if set during creation"),
    },
  },
  async ({ wallet, to, amount_usdc, network, valid_before, passphrase }) => {
    try {
      const chain = network ?? "base";
      const usdc = USDC_CONTRACTS[chain];
      if (!usdc) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Unsupported network: ${chain}. Supported: ${Object.keys(USDC_CONTRACTS).join(", ")}`,
            },
          ],
          isError: true,
        };
      }

      // Get the signer address
      const info = ows.getWallet(wallet);
      const evmAccount = info.accounts.find((a) =>
        a.chainId.startsWith("eip155:")
      );
      if (!evmAccount) {
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

      // Convert USDC amount to 6-decimal value
      const value = BigInt(Math.round(amount_usdc * 1_000_000)).toString();

      // Generate random nonce (32 bytes)
      const { randomBytes } = await import("crypto");
      const nonce = "0x" + randomBytes(32).toString("hex");

      // Expiry: default 1 hour from now
      const now = Math.floor(Date.now() / 1000);
      const validBefore = valid_before ?? now + 3600;

      // Build EIP-712 typed data
      const typedData = {
        types: {
          EIP712Domain: [
            { name: "name", type: "string" },
            { name: "version", type: "string" },
            { name: "chainId", type: "uint256" },
            { name: "verifyingContract", type: "address" },
          ],
          ReceiveWithAuthorization: [
            { name: "from", type: "address" },
            { name: "to", type: "address" },
            { name: "value", type: "uint256" },
            { name: "validAfter", type: "uint256" },
            { name: "validBefore", type: "uint256" },
            { name: "nonce", type: "bytes32" },
          ],
        },
        primaryType: "ReceiveWithAuthorization",
        domain: {
          name: "USD Coin",
          version: "2",
          chainId: usdc.chainId,
          verifyingContract: usdc.address,
        },
        message: {
          from: evmAccount.address,
          to,
          value,
          validAfter: "0",
          validBefore: validBefore.toString(),
          nonce,
        },
      };

      // Sign with OWS
      const result = ows.signTypedData(
        wallet,
        "evm",
        JSON.stringify(typedData),
        passphrase ?? undefined
      );

      // Extract v, r, s
      const sigHex = result.signature.startsWith("0x")
        ? result.signature.slice(2)
        : result.signature;
      const r = "0x" + sigHex.slice(0, 64);
      const s = "0x" + sigHex.slice(64, 128);
      const v =
        result.recoveryId !== undefined && result.recoveryId !== null
          ? result.recoveryId
          : parseInt(sigHex.slice(128, 130), 16);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                success: true,
                authorization: {
                  from: evmAccount.address,
                  to,
                  value,
                  validAfter: "0",
                  validBefore: validBefore.toString(),
                  nonce,
                  v,
                  r,
                  s,
                  signature: "0x" + sigHex,
                },
                network: chain,
                amount_usdc,
                usdc_contract: usdc.address,
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
// Boot
// ---------------------------------------------------------------------------

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[ows-mcp-server] Running on stdio — 8 tools available");
  console.error("[ows-mcp-server] Wallet vault: ~/.ows/wallets/");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
