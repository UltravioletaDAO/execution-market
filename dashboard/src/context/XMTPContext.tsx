import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import type { Client as XMTPClient, XMTPSigner } from "@xmtp/browser-sdk";
import { hexToBytes } from "viem";

/** Minimal wallet signer interface — compatible with Dynamic.xyz + viem wallets */
interface WalletSigner {
  getWalletClient?: () => Promise<{
    signMessage(params: { message: string; account: unknown }): Promise<`0x${string}`>;
    account: unknown;
  }>;
  getAddress?: () => string | Promise<string>;
  /** Dynamic.xyz signMessage may return undefined on cancellation */
  signMessage?: (message: string) => Promise<string | undefined>;
}

interface XMTPContextType {
  client: XMTPClient | null;
  isConnected: boolean;
  isConnecting: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  error: string | null;
  walletAddress: string | null;
  /** Current user's XMTP inbox id (v5 canonical identifier). Null until connected. */
  inboxId: string | null;
}

const XMTPContext = createContext<XMTPContextType | null>(null);

export function XMTPProvider({ children, walletAddress, signer }: {
  children: ReactNode;
  walletAddress: string | null;
  signer: WalletSigner | null;
}) {
  const [client, setClient] = useState<XMTPClient | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    if (!signer || !walletAddress) return;
    setIsConnecting(true);
    setError(null);
    try {
      const { Client, IdentifierKind } = await import("@xmtp/browser-sdk");

      const address = walletAddress.toLowerCase();
      const toSignatureBytes = (sig: string): Uint8Array =>
        hexToBytes(sig.startsWith("0x") ? (sig as `0x${string}`) : (`0x${sig}` as `0x${string}`));

      // XMTP browser-sdk v5+ requires: { type, getIdentifier, signMessage → Uint8Array }
      let xmtpSigner: XMTPSigner;
      if (typeof signer.getWalletClient === "function") {
        const walletClient = await signer.getWalletClient();
        xmtpSigner = {
          type: "EOA",
          getIdentifier: () => ({ identifier: address, identifierKind: IdentifierKind.Ethereum }),
          signMessage: async (message: string) => {
            const sig = await walletClient.signMessage({ message, account: walletClient.account });
            return toSignatureBytes(sig);
          },
        };
      } else {
        xmtpSigner = {
          type: "EOA",
          getIdentifier: () => ({ identifier: address, identifierKind: IdentifierKind.Ethereum }),
          signMessage: async (message: string) => {
            const sig = await signer.signMessage?.(message);
            if (!sig) throw new Error("Signature cancelled by user");
            return toSignatureBytes(sig);
          },
        };
      }

      const xmtp = await Client.create(xmtpSigner, { env: "production" });
      setClient(xmtp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error connecting to XMTP");
    } finally {
      setIsConnecting(false);
    }
  }, [signer, walletAddress]);

  const disconnect = useCallback(() => {
    if (client?.close) client.close();
    setClient(null);
  }, [client]);

  useEffect(() => {
    return () => {
      if (client?.close) client.close();
    };
  }, [client]);

  return (
    <XMTPContext.Provider value={{
      client,
      isConnected: !!client,
      isConnecting,
      connect,
      disconnect,
      error,
      walletAddress,
      inboxId: client?.inboxId ?? null,
    }}>
      {children}
    </XMTPContext.Provider>
  );
}

export function useXMTP() {
  const ctx = useContext(XMTPContext);
  if (!ctx) throw new Error("useXMTP must be used within XMTPProvider");
  return ctx;
}
