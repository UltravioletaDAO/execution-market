import { logger } from "../utils/logger.js";

interface IdentityEntry {
  nick: string;
  walletAddress: string;
  linkedAt: Date;
}

// In-memory store -- future: persist to Supabase
const nickToWallet = new Map<string, string>();
const walletToNick = new Map<string, string>();

export function linkNickToWallet(nick: string, walletAddress: string): void {
  const normalized = nick.toLowerCase();
  const addr = walletAddress.toLowerCase();

  // Remove old mappings if nick or wallet were previously linked
  const oldWallet = nickToWallet.get(normalized);
  if (oldWallet) walletToNick.delete(oldWallet);
  const oldNick = walletToNick.get(addr);
  if (oldNick) nickToWallet.delete(oldNick);

  nickToWallet.set(normalized, addr);
  walletToNick.set(addr, normalized);

  logger.info(
    { nick, walletAddress: `${addr.slice(0, 6)}...${addr.slice(-4)}` },
    "IRC identity linked",
  );
}

export function getWalletByNick(nick: string): string | undefined {
  return nickToWallet.get(nick.toLowerCase());
}

export function getNickByWallet(walletAddress: string): string | undefined {
  return walletToNick.get(walletAddress.toLowerCase());
}

export function unlinkNick(nick: string): boolean {
  const normalized = nick.toLowerCase();
  const wallet = nickToWallet.get(normalized);
  if (!wallet) return false;
  nickToWallet.delete(normalized);
  walletToNick.delete(wallet);
  return true;
}

export function getAllLinks(): IdentityEntry[] {
  const entries: IdentityEntry[] = [];
  for (const [nick, wallet] of nickToWallet) {
    entries.push({ nick, walletAddress: wallet, linkedAt: new Date() });
  }
  return entries;
}

export function isValidEthAddress(address: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(address);
}
