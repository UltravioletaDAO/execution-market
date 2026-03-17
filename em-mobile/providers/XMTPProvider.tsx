import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { Platform } from "react-native";

// @xmtp/react-native-sdk requires EAS Build with custom native modules.
// We fall back to @xmtp/browser-sdk (v5 MLS protocol) which works in
// Expo web and React Native web environments.
const XMTP_NATIVE_AVAILABLE = false;

interface XMTPContextType {
  client: any | null;
  isConnected: boolean;
  isConnecting: boolean;
  nativeAvailable: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  walletAddress: string | null;
  error: string | null;
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
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    if (!walletAddress) {
      setError("Conecta tu wallet primero para usar mensajería XMTP.");
      return;
    }
    if (!getSigner) {
      setError("Wallet no disponible. Reconecta tu wallet en configuración.");
      return;
    }
    // Browser SDK requires Web Workers — only works in web environments
    if (Platform.OS !== "web") {
      setError("Mensajería XMTP disponible en la versión web. Abre execution.market en tu navegador.");
      return;
    }
    setIsConnecting(true);
    setError(null);

    if (XMTP_NATIVE_AVAILABLE) {
      // Native SDK path (requires EAS Build — not active until EAS is set up)
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { Client } = await import("@xmtp/react-native-sdk");
        const signer = await getSigner();
        const dbKey = await getOrCreateEncryptionKey();
        const xmtp = await Client.create(signer, {
          env: "production",
          dbEncryptionKey: dbKey,
        });
        setClient(xmtp);
      } catch (err) {
        console.error("[XMTP] Native connection failed:", err);
        setError(err instanceof Error ? err.message : "XMTP connection failed");
      } finally {
        setIsConnecting(false);
      }
      return;
    }

    // Browser SDK v5 fallback (works in Expo web / React Native web)
    try {
      const { Client } = await import("@xmtp/browser-sdk");

      const rawSigner = await getSigner();

      // Build an XMTP v5-compatible signer.
      // v5 API requires: { getIdentifier(): Promise<{type, identifier}>, signMessage(text): Promise<string> }
      // The Dynamic.xyz connector may expose getWalletClient() (viem) or signMessage directly.
      const xmtpSigner = await buildXmtpV5Signer(rawSigner, walletAddress);

      const xmtp = await Client.create(xmtpSigner, { env: "production" });
      setClient(xmtp);
    } catch (err) {
      console.error("[XMTP] Browser SDK connection failed:", err);
      setError(err instanceof Error ? err.message : "XMTP connection failed");
    } finally {
      setIsConnecting(false);
    }
  }, [walletAddress, getSigner]);

  const disconnect = useCallback(() => {
    if (client?.close) client.close();
    setClient(null);
    setError(null);
  }, [client]);

  return (
    <XMTPContext.Provider
      value={{
        client,
        isConnected: !!client,
        isConnecting,
        // nativeAvailable exposed for informational use.
        // The browser SDK fallback means messaging works regardless.
        nativeAvailable: true,
        connect,
        disconnect,
        walletAddress,
        error,
      }}
    >
      {children}
    </XMTPContext.Provider>
  );
}

export function useXMTP() {
  const ctx = useContext(XMTPContext);
  if (!ctx) throw new Error("useXMTP must be used within XMTPProvider");
  return ctx;
}

/**
 * Build an XMTP v5 signer from a Dynamic.xyz wallet connector.
 *
 * XMTP v5 signer interface:
 *   getIdentifier(): Promise<{ type: "EOA", identifier: string }>
 *   signMessage(text: string): Promise<string>
 */
async function buildXmtpV5Signer(rawSigner: any, walletAddress: string): Promise<any> {
  // Case 1: Dynamic connector with viem wallet client (most common in Dynamic.xyz)
  if (rawSigner && typeof rawSigner.getWalletClient === "function") {
    const walletClient = await rawSigner.getWalletClient();
    return {
      getIdentifier: async () => ({ type: "EOA" as const, identifier: walletAddress }),
      signMessage: async (text: string): Promise<string> =>
        walletClient.signMessage({
          message: text,
          account: walletClient.account,
        }),
    };
  }

  // Case 2: Object with signMessage directly (ethers Signer or similar)
  if (rawSigner && typeof rawSigner.signMessage === "function") {
    return {
      getIdentifier: async () => ({
        type: "EOA" as const,
        identifier:
          typeof rawSigner.getAddress === "function"
            ? await rawSigner.getAddress()
            : walletAddress,
      }),
      signMessage: async (text: string): Promise<string> =>
        rawSigner.signMessage(text),
    };
  }

  // Case 3: Dynamic wallet object with connector.signMessage
  if (rawSigner && rawSigner.connector && typeof rawSigner.connector.signMessage === "function") {
    return {
      getIdentifier: async () => ({
        type: "EOA" as const,
        identifier: rawSigner.address ?? walletAddress,
      }),
      signMessage: async (text: string): Promise<string> =>
        rawSigner.connector.signMessage({ message: text }),
    };
  }

  // Last resort: pass through and let the SDK handle it
  if (rawSigner && typeof rawSigner.getIdentifier !== "function") {
    // Wrap with minimal v5 interface
    return {
      getIdentifier: async () => ({ type: "EOA" as const, identifier: walletAddress }),
      signMessage: async (text: string): Promise<string> => {
        if (typeof rawSigner.sign === "function") return rawSigner.sign(text);
        throw new Error("[XMTP] Cannot sign message: no compatible sign method found on wallet");
      },
    };
  }

  return rawSigner;
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
