import { config } from "../config.js";
import { logger } from "../utils/logger.js";

const BASE = () => config.meshrelay.apiUrl;

interface IdentityResponse {
  nick: string;
  wallet_address: string;
  verified: number;
  linked_at: string;
  last_seen: string;
}

// ─── Look up wallet by IRC nick via MeshRelay API ───────────────────
export async function getWalletByNick(nick: string): Promise<string | undefined> {
  try {
    const res = await fetch(`${BASE()}/identity/by-nick/${encodeURIComponent(nick)}`);
    if (res.status === 404) return undefined;
    if (!res.ok) {
      logger.warn({ status: res.status, nick }, "MeshRelay identity lookup failed");
      return undefined;
    }
    const data = (await res.json()) as IdentityResponse;
    return data.wallet_address;
  } catch (err) {
    logger.error({ err, nick }, "MeshRelay identity lookup error");
    return undefined;
  }
}

// ─── Look up nick by wallet via MeshRelay API ───────────────────────
export async function getNickByWallet(walletAddress: string): Promise<string | undefined> {
  try {
    const res = await fetch(`${BASE()}/identity/by-wallet/${encodeURIComponent(walletAddress)}`);
    if (res.status === 404) return undefined;
    if (!res.ok) return undefined;
    const data = (await res.json()) as IdentityResponse;
    return data.nick;
  } catch (err) {
    logger.error({ err, walletAddress: walletAddress.slice(0, 10) }, "MeshRelay wallet lookup error");
    return undefined;
  }
}

// ─── Link nick to wallet via MeshRelay API ──────────────────────────
export async function linkNickToWallet(nick: string, walletAddress: string): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch(`${BASE()}/identity/link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nick, wallet_address: walletAddress }),
    });

    if (res.ok) {
      logger.info(
        { nick, walletAddress: `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}` },
        "IRC identity linked via MeshRelay",
      );
      return { ok: true };
    }

    if (res.status === 409) {
      const data = await res.json();
      return { ok: false, error: `Already linked: ${data.nick ?? data.wallet_address ?? "conflict"}` };
    }

    if (res.status === 400) {
      const data = await res.json();
      return { ok: false, error: data.detail ?? "Invalid input" };
    }

    return { ok: false, error: `API error (${res.status})` };
  } catch (err) {
    logger.error({ err, nick }, "MeshRelay link error");
    return { ok: false, error: "Network error" };
  }
}

// ─── Unlink nick via MeshRelay API ──────────────────────────────────
export async function unlinkNick(nick: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE()}/identity/link/${encodeURIComponent(nick)}`, {
      method: "DELETE",
    });
    return res.ok;
  } catch (err) {
    logger.error({ err, nick }, "MeshRelay unlink error");
    return false;
  }
}

// ─── Validate Ethereum address format ───────────────────────────────
export function isValidEthAddress(address: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(address);
}
