import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

interface XMTPContextType {
  client: any | null;
  isConnected: boolean;
  isConnecting: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  error: string | null;
  walletAddress: string | null;
}

const XMTPContext = createContext<XMTPContextType | null>(null);

export function XMTPProvider({ children, walletAddress, signer }: {
  children: ReactNode;
  walletAddress: string | null;
  signer: any | null;
}) {
  const [client, setClient] = useState<any | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    if (!signer || !walletAddress) return;
    setIsConnecting(true);
    setError(null);
    try {
      // Dynamic import to avoid bundling XMTP when not used
      const { Client } = await import("@xmtp/browser-sdk");
      const xmtp = await Client.create(signer, { env: "production" });
      setClient(xmtp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al conectar XMTP");
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
