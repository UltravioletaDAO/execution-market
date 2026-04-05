# How It's Made — ETHGlobal Cannes 2026

> Copy-paste answers for the "How it's made" submission field per sponsor.

---

## World (World ID 4.0 + AgentKit)

Execution Market is a Python/FastAPI backend with a React/TypeScript dashboard. For World ID 4.0, we implemented RP signing from scratch using secp256k1 + EIP-191: the backend constructs a binary message (version || nonce || createdAt || expiresAt || action), hashes it with keccak256, and signs with a dedicated signing key. The signed request is sent to World's Cloud API v4 for proof verification. On the frontend, we use IDKit v4 with the Orb preset — the React component (`WorldIdVerification.tsx`) handles the full flow and stores the proof in a `world_id_verifications` table with a UNIQUE constraint on `nullifier_hash` to prevent sybil attacks (one person, one account). The enforcement is a shared async utility (`check_world_id_eligibility`) called by both the REST API and MCP protocol — so the $5+ bounty threshold is enforced whether a worker applies via the web dashboard or programmatically via an AI agent's MCP client. We extracted this into a single function to avoid the classic "bypass via alternate entry point" vulnerability. For AgentKit, we built a standalone Hono/TypeScript gateway server that calls `AgentBook.lookupHuman(address)` on Base via raw JSON-RPC (no web3 dependency, just httpx + eth_call ABI encoding). Verified humans get free API access; bots hit an x402 paywall at $0.001/request using our open-source Facilitator for gasless USDC settlement.

---

## Hedera (AI & Agentic Payments)

The Hedera integration is the most cross-chain piece: payments run on Base (USDC escrow via x402), while reputation, tips, and audit logging run on Hedera. We built five modules in Python. (1) ERC-8004 identity registration on Hedera testnet via our open-source Rust Facilitator (x402-rs) — we added Hedera mainnet (chain 295) and testnet (296) support in commit 66d34e6, so the Facilitator pays HBAR gas on behalf of agents. (2) Bidirectional on-chain reputation using the ERC-8004 Reputation Registry — both agent-rates-worker and worker-rates-agent flows, verified on HashScan. (3) Merit tips: a direct 0.01 HBAR transfer to workers whose reputation score exceeds a threshold, proving native HBAR payments work alongside USDC escrow. (4) The standout piece: HCS (Hedera Consensus Service) logging — this is Hedera-native, NOT EVM. We use the `hiero-sdk-python` (Hedera's official Python SDK) to create a topic and submit 6 immutable lifecycle messages (task_created, worker_applied, task_assigned, evidence_submitted, task_completed, payment_released) with consensus timestamps. All messages are publicly verifiable via Mirror Node REST API without any API key. (5) The Golden Flow test exercises all 5 modules end-to-end on production: 7/7 phases pass, with real USDC escrow on Base and real on-chain reputation + HCS messages on Hedera.

---

## ENS (Best Integration for AI Agents + Most Creative Use)

We registered `execution-market.eth` on Ethereum Mainnet with 7 ENSIP-5 text records that make our platform agent machine-discoverable: url, description, avatar, com.twitter, com.execution.market.agentId (2106), com.execution.market.role (platform), and com.execution.market.chains (base,ethereum,polygon,arbitrum,avalanche,monad,celo,optimism,skale). The backend ENS client (Python/web3.py) does forward resolution (name→address), reverse resolution (address→name), and text record queries using proper EIP-137 namehash computation. For workers, we support subname resolution (`alice.execution-market.eth`) via NameWrapper — each worker in the fleet gets a human-readable identity that resolves to their wallet. On the dashboard (React), an `ENSBadge` component auto-detects ENS names on wallet connection via a fire-and-forget reverse lookup and displays the name alongside the worker's profile. The backend exposes 5 REST endpoints: resolve name, reverse lookup, get text records, check subname availability, and claim subname. The creative angle: we're using ENS not just for human identity but as AI agent identity infrastructure — other agents can query `execution-market.eth` text records to programmatically discover our agent ID, supported chains, and role, making ENS a machine-readable directory for the agentic web.

---

*Each answer is 280+ characters and focuses on technical implementation details as requested by the submission form.*
