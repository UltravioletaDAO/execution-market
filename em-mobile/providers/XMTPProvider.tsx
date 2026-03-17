import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";

interface XMTPContextType {
  client: any | null;
  isConnected: boolean;
  isConnecting: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  walletAddress: string | null;
}

const XMTPContext = createContext<XMTPContextType | null>(null);

interface Props {
  children: ReactNode;
  walletAddress: string | null;
  getSigner: (() => Promise<any>) | null;
}

export function XMTPProvider({ children, walletAddress, getSigner }: Props) {
  const [client, setClient] = useState<any | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  const connect = useCallback(async () => {
    if (!walletAddress || !getSigner) return;
    setIsConnecting(true);
    try {
      const { Client } = await import("@xmtp/react-native-sdk");
      const signer = await getSigner();
      const dbKey = await getOrCreateEncryptionKey();
      const xmtp = await Client.create(signer, {
        env: "production",
        dbEncryptionKey: dbKey,
      });
      setClient(xmtp);
    } catch (err) {
      console.error("[XMTP] Connection failed:", err);
    } finally {
      setIsConnecting(false);
    }
  }, [walletAddress, getSigner]);

  const disconnect = useCallback(() => {
    setClient(null);
  }, []);

  return (
    <XMTPContext.Provider value={{
      client,
      isConnected: !!client,
      isConnecting,
      connect,
      disconnect,
      walletAddress,
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

async function getOrCreateEncryptionKey(): Promise<Uint8Array> {
  try {
    const SecureStore = await import("expo-secure-store");
    const stored = await SecureStore.getItemAsync("xmtp_db_key");
    if (stored) {
      const bytes = atob(stored);
      const arr = new Uint8Array(bytes.length);
      for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
      return arr;
    }
    const key = new Uint8Array(32);
    globalThis.crypto.getRandomValues(key);
    const b64 = btoa(String.fromCharCode(...key));
    await SecureStore.setItemAsync("xmtp_db_key", b64);
    return key;
  } catch {
    // Fallback: generate ephemeral key
    const key = new Uint8Array(32);
    globalThis.crypto.getRandomValues(key);
    return key;
  }
}
