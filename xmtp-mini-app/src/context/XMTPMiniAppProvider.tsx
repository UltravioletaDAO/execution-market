import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

interface MiniAppContext {
  isReady: boolean;
  walletAddress: string | null;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
}

const Context = createContext<MiniAppContext | null>(null);

export function XMTPMiniAppProvider({ children }: { children: ReactNode }) {
  const [isReady, setIsReady] = useState(false);
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initMiniApp();
  }, []);

  async function initMiniApp() {
    try {
      // Try to initialize the XMTP Mini App SDK
      // The SDK provides the wallet address from the host app (Converse/World App)
      const { default: sdk } = await import("@xmtp/mini-app-sdk");
      const context = await sdk.getContext();

      if (context?.walletAddress) {
        setWalletAddress(context.walletAddress);
      }
      setIsReady(true);
    } catch (err) {
      // Fallback: running outside of XMTP client (dev mode)
      console.warn("[MiniApp] Not in XMTP context, running in standalone mode");
      setIsReady(true);
    }
  }

  async function sendMessage(text: string) {
    try {
      const { default: sdk } = await import("@xmtp/mini-app-sdk");
      await sdk.sendMessage(text);
    } catch {
      console.warn("[MiniApp] sendMessage not available outside XMTP client");
    }
  }

  return (
    <Context.Provider value={{ isReady, walletAddress, error, sendMessage }}>
      {children}
    </Context.Provider>
  );
}

export function useXMTPMiniApp() {
  const ctx = useContext(Context);
  if (!ctx) throw new Error("useXMTPMiniApp must be used within XMTPMiniAppProvider");
  return ctx;
}
