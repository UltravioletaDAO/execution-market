/**
 * Persistent identity store backed by Supabase `irc_identities` table.
 * In-memory LRU cache (5-min TTL) for hot path reads.
 * Source of truth: Supabase.
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { config } from "../config.js";
import { logger } from "../utils/logger.js";

export enum TrustLevel {
  ANONYMOUS = 0,
  LINKED = 1,
  VERIFIED = 2,
  REGISTERED = 3,
}

export interface IrcIdentity {
  id: string;
  irc_nick: string;
  wallet_address: string;
  trust_level: TrustLevel;
  nickserv_account: string | null;
  agent_id: number | null;
  challenge_nonce: string | null;
  challenge_expires_at: string | null;
  verified_at: string | null;
  last_seen_at: string | null;
  preferred_channel: "irc" | "xmtp" | "both";
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface CacheEntry {
  value: string;
  expiresAt: number;
}

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const MAX_CACHE_SIZE = 500;

class IdentityStore {
  private supabase: SupabaseClient | null = null;
  private nickToWallet = new Map<string, CacheEntry>();
  private walletToNick = new Map<string, CacheEntry>();

  init(): void {
    if (!config.supabase.url || !config.supabase.serviceKey) {
      logger.warn("Supabase not configured — identity store in memory-only mode");
      return;
    }
    this.supabase = createClient(config.supabase.url, config.supabase.serviceKey);
    logger.info("Identity store initialized with Supabase persistence");
  }

  private setCached(map: Map<string, CacheEntry>, key: string, value: string): void {
    if (map.size >= MAX_CACHE_SIZE) {
      const firstKey = map.keys().next().value;
      if (firstKey) map.delete(firstKey);
    }
    map.set(key, { value, expiresAt: Date.now() + CACHE_TTL_MS });
  }

  private getCached(map: Map<string, CacheEntry>, key: string): string | null {
    const entry = map.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiresAt) {
      map.delete(key);
      return null;
    }
    return entry.value;
  }

  async linkNickToWallet(nick: string, wallet: string): Promise<TrustLevel> {
    const normalizedNick = nick.toLowerCase();
    const normalizedWallet = wallet.toLowerCase();

    if (this.supabase) {
      const { error } = await this.supabase.from("irc_identities").upsert(
        {
          irc_nick: normalizedNick,
          wallet_address: normalizedWallet,
          trust_level: TrustLevel.LINKED,
          last_seen_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        { onConflict: "irc_nick" },
      );
      if (error) {
        logger.error({ error, nick, wallet: normalizedWallet.slice(0, 10) }, "Failed to persist identity link");
      }
    }

    this.setCached(this.nickToWallet, normalizedNick, normalizedWallet);
    this.setCached(this.walletToNick, normalizedWallet, normalizedNick);

    logger.info(
      { nick, wallet: `${normalizedWallet.slice(0, 6)}...${normalizedWallet.slice(-4)}` },
      "Identity linked (persistent)",
    );
    return TrustLevel.LINKED;
  }

  async getWalletByNick(nick: string): Promise<string | null> {
    const normalized = nick.toLowerCase();

    const cached = this.getCached(this.nickToWallet, normalized);
    if (cached) return cached;

    if (this.supabase) {
      const { data } = await this.supabase
        .from("irc_identities")
        .select("wallet_address")
        .eq("irc_nick", normalized)
        .single();
      if (data?.wallet_address) {
        this.setCached(this.nickToWallet, normalized, data.wallet_address);
        return data.wallet_address;
      }
    }

    return null;
  }

  async getNickByWallet(wallet: string): Promise<string | null> {
    const normalized = wallet.toLowerCase();

    const cached = this.getCached(this.walletToNick, normalized);
    if (cached) return cached;

    if (this.supabase) {
      const { data } = await this.supabase
        .from("irc_identities")
        .select("irc_nick")
        .eq("wallet_address", normalized)
        .single();
      if (data?.irc_nick) {
        this.setCached(this.walletToNick, normalized, data.irc_nick);
        return data.irc_nick;
      }
    }

    return null;
  }

  async getTrustLevel(nick: string): Promise<TrustLevel> {
    if (!this.supabase) return TrustLevel.ANONYMOUS;

    const { data } = await this.supabase
      .from("irc_identities")
      .select("trust_level")
      .eq("irc_nick", nick.toLowerCase())
      .single();

    return (data?.trust_level as TrustLevel) ?? TrustLevel.ANONYMOUS;
  }

  async setTrustLevel(nick: string, level: TrustLevel): Promise<void> {
    if (!this.supabase) return;

    const updates: Record<string, unknown> = {
      trust_level: level,
      updated_at: new Date().toISOString(),
    };
    if (level === TrustLevel.VERIFIED) {
      updates.verified_at = new Date().toISOString();
    }

    const { error } = await this.supabase
      .from("irc_identities")
      .update(updates)
      .eq("irc_nick", nick.toLowerCase());

    if (error) {
      logger.error({ error, nick, level }, "Failed to update trust level");
    }
  }

  async setAgentId(nick: string, agentId: number): Promise<void> {
    if (!this.supabase) return;

    const { error } = await this.supabase
      .from("irc_identities")
      .update({
        agent_id: agentId,
        trust_level: TrustLevel.REGISTERED,
        updated_at: new Date().toISOString(),
      })
      .eq("irc_nick", nick.toLowerCase());

    if (error) {
      logger.error({ error, nick, agentId }, "Failed to set agent ID");
    }
  }

  async storeChallenge(nick: string, nonce: string, ttlMinutes: number = 5): Promise<void> {
    if (!this.supabase) return;

    const expiresAt = new Date(Date.now() + ttlMinutes * 60 * 1000).toISOString();
    const { error } = await this.supabase
      .from("irc_identities")
      .update({
        challenge_nonce: nonce,
        challenge_expires_at: expiresAt,
        updated_at: new Date().toISOString(),
      })
      .eq("irc_nick", nick.toLowerCase());

    if (error) {
      logger.error({ error, nick }, "Failed to store challenge nonce");
    }
  }

  async getChallenge(nick: string): Promise<{ nonce: string; expiresAt: string; wallet: string } | null> {
    if (!this.supabase) return null;

    const { data } = await this.supabase
      .from("irc_identities")
      .select("challenge_nonce, challenge_expires_at, wallet_address")
      .eq("irc_nick", nick.toLowerCase())
      .single();

    if (!data?.challenge_nonce || !data?.challenge_expires_at) return null;

    return {
      nonce: data.challenge_nonce,
      expiresAt: data.challenge_expires_at,
      wallet: data.wallet_address,
    };
  }

  async clearChallenge(nick: string): Promise<void> {
    if (!this.supabase) return;

    await this.supabase
      .from("irc_identities")
      .update({
        challenge_nonce: null,
        challenge_expires_at: null,
        updated_at: new Date().toISOString(),
      })
      .eq("irc_nick", nick.toLowerCase());
  }

  async getIdentity(nick: string): Promise<IrcIdentity | null> {
    if (!this.supabase) return null;

    const { data } = await this.supabase
      .from("irc_identities")
      .select("*")
      .eq("irc_nick", nick.toLowerCase())
      .single();

    return data as IrcIdentity | null;
  }

  async getIdentityByWallet(wallet: string): Promise<IrcIdentity | null> {
    if (!this.supabase) return null;

    const { data } = await this.supabase
      .from("irc_identities")
      .select("*")
      .eq("wallet_address", wallet.toLowerCase())
      .single();

    return data as IrcIdentity | null;
  }

  async touchLastSeen(nick: string): Promise<void> {
    if (!this.supabase) return;

    await this.supabase
      .from("irc_identities")
      .update({ last_seen_at: new Date().toISOString() })
      .eq("irc_nick", nick.toLowerCase());
  }

  /**
   * Synchronous nick lookup from cache only (no DB hit).
   * Used by xmtp-to-irc bridge where async is impractical.
   */
  getNickByWalletSync(wallet: string): string | null {
    const entry = this.walletToNick.get(wallet.toLowerCase());
    if (!entry) return null;
    if (Date.now() > entry.expiresAt) {
      this.walletToNick.delete(wallet.toLowerCase());
      return null;
    }
    return entry.value;
  }

  /**
   * Set preferred notification channel for a user.
   */
  async setPreferredChannel(nick: string, channel: "irc" | "xmtp" | "both"): Promise<void> {
    if (!this.supabase) return;

    await this.supabase
      .from("irc_identities")
      .update({ metadata: { preferred_channel: channel } })
      .eq("irc_nick", nick.toLowerCase());
  }

  async loadAllToCache(): Promise<number> {
    if (!this.supabase) return 0;

    const { data, error } = await this.supabase
      .from("irc_identities")
      .select("irc_nick, wallet_address")
      .order("last_seen_at", { ascending: false })
      .limit(MAX_CACHE_SIZE);

    if (error || !data) {
      logger.error({ error }, "Failed to load identities into cache");
      return 0;
    }

    for (const row of data) {
      this.setCached(this.nickToWallet, row.irc_nick, row.wallet_address);
      this.setCached(this.walletToNick, row.wallet_address, row.irc_nick);
    }

    logger.info({ count: data.length }, "Loaded identities into cache");
    return data.length;
  }
}

export const identityStore = new IdentityStore();
