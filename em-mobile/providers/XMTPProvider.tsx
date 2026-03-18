// Must be the FIRST import — patches global.crypto before any crypto usage
import "react-native-get-random-values";
import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import Constants, { ExecutionEnvironment } from "expo-constants";

// Detect Expo Go: appOwnership === 'expo' OR executionEnvironment === 'storeClient'.
// @xmtp/react-native-sdk native module is not available in Expo Go.
const IS_EXPO_GO =
  Constants.appOwnership === "expo" ||
  Constants.executionEnvironment === ExecutionEnvironment.StoreClient;
const XMTP_NATIVE_AVAILABLE = !IS_EXPO_GO;

interface XMTPContextType {
  client: any | null;
  isConnected: boolean;
  isConnecting: boolean;
  nativeAvailable: boolean;
  signerAvailable: boolean;
  isDevMode: boolean;
  connect: () => Promise<void>;
  connectDev: () => Promise<void>;
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
  const [isDevMode, setIsDevMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    if (IS_EXPO_GO) {
      setError("XMTP no está disponible en Expo Go. Usa el Android dev client.");
      return;
    }
    if (!walletAddress) {
      setError("Conecta tu wallet primero para usar mensajería XMTP.");
      return;
    }
    if (!getSigner) {
      setError("Wallet no disponible. Reconecta tu wallet en configuración.");
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { Client } = await import("@xmtp/react-native-sdk");
      const rawSigner = await getSigner();
      const nativeSigner = buildNativeSigner(rawSigner, walletAddress);
      const dbKey = await getOrCreateEncryptionKey();

      const xmtp = await Client.create(nativeSigner, {
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
  }, [walletAddress, getSigner]);

  // DEV MODE: creates a random XMTP identity for testing messaging UI
  // without needing a real wallet connector. NOT for production use.
  const connectDev = useCallback(async () => {
    if (IS_EXPO_GO) {
      setError("XMTP no está disponible en Expo Go. Usa el Android dev client.");
      return;
    }
    setIsConnecting(true);
    setError(null);
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { Client } = await import("@xmtp/react-native-sdk");
      const { generatePrivateKey, privateKeyToAccount } = await import("viem/accounts");
      const dbKey = await getOrCreateEncryptionKey();

      // Generate a random ephemeral wallet as XMTP signer for dev testing.
      const pk = generatePrivateKey();
      const account = privateKeyToAccount(pk);
      const devSigner = {
        walletType: "EOA" as const,
        getAddress: async () => account.address,
        signMessage: async (message: string) =>
          account.signMessage({ message }),
      };

      const xmtp = await Client.create(devSigner, {
        env: "dev",
        dbEncryptionKey: dbKey,
      });
      setIsDevMode(true);
      setClient(xmtp);
    } catch (err) {
      console.error("[XMTP] Dev connect failed:", err);
      setError(err instanceof Error ? err.message : "XMTP dev connect failed");
    } finally {
      setIsConnecting(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (client?.close) client.close();
    setClient(null);
    setIsDevMode(false);
    setError(null);
  }, [client]);

  return (
    <XMTPContext.Provider
      value={{
        client,
        isConnected: !!client,
        isConnecting,
        nativeAvailable: XMTP_NATIVE_AVAILABLE,
        signerAvailable: !!getSigner,
        isDevMode,
        connect,
        connectDev,
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
 * Build an XMTP react-native-sdk v3 signer from a Dynamic.xyz wallet connector.
 *
 * react-native-sdk v3 signer interface:
 *   getAddress(): Promise<string>
 *   signMessage(message: string): Promise<string>
 *
 * Dynamic.xyz connectors expose getSigner() which may return:
 *   - A viem WalletClient (has signMessage + account.address)
 *   - An ethers Signer (has signMessage + getAddress)
 *   - The raw Dynamic wallet object (has connector.signMessage + address)
 */
function buildNativeSigner(rawSigner: any, fallbackAddress: string): {
  walletType: "EOA";
  getAddress(): Promise<string>;
  signMessage(message: string): Promise<string>;
} {
  const EOA = "EOA" as const;

  // Case 1: viem WalletClient
  if (rawSigner && typeof rawSigner.signMessage === "function" && rawSigner.account) {
    return {
      walletType: EOA,
      getAddress: async () => rawSigner.account.address ?? fallbackAddress,
      signMessage: async (message: string) =>
        rawSigner.signMessage({ message, account: rawSigner.account }),
    };
  }

  // Case 2: ethers Signer (v5 or v6)
  if (rawSigner && typeof rawSigner.signMessage === "function" && typeof rawSigner.getAddress === "function") {
    return {
      walletType: EOA,
      getAddress: async () => rawSigner.getAddress(),
      signMessage: async (message: string) => rawSigner.signMessage(message),
    };
  }

  // Case 3: Dynamic wallet with connector.signMessage
  if (rawSigner && rawSigner.connector && typeof rawSigner.connector.signMessage === "function") {
    return {
      walletType: EOA,
      getAddress: async () => rawSigner.address ?? fallbackAddress,
      signMessage: async (message: string) =>
        rawSigner.connector.signMessage({ message }),
    };
  }

  // Case 4: signMessage only
  if (rawSigner && typeof rawSigner.signMessage === "function") {
    return {
      walletType: EOA,
      getAddress: async () => fallbackAddress,
      signMessage: async (message: string) => rawSigner.signMessage(message),
    };
  }

  // Last resort
  return {
    walletType: EOA,
    getAddress: async () => fallbackAddress,
    signMessage: async () => {
      throw new Error("[XMTP] Cannot sign message: no compatible sign method found on wallet connector");
    },
  };
}

/**
 * Portable random bytes — uses react-native-get-random-values polyfill
 * which is already installed and works on Android/iOS dev clients.
 * globalThis.crypto.getRandomValues is NOT available in the RN JS engine.
 */
function getRandomBytes(size: number): Uint8Array {
  const buf = new Uint8Array(size);
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    crypto.getRandomValues(buf);
  } else {
    // last resort: Math.random (not cryptographically secure, only for dev)
    for (let i = 0; i < size; i++) buf[i] = Math.floor(Math.random() * 256);
  }
  return buf;
}

/**
 * Retrieve or generate a 32-byte AES-256 key for XMTP's local SQLite database.
 * Stored in expo-secure-store so it survives app restarts but is erased on uninstall.
 */
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
    const key = getRandomBytes(32);
    const b64 = btoa(String.fromCharCode(...key));
    await SecureStore.setItemAsync("xmtp_db_key", b64);
    return key;
  } catch {
    // Fallback: ephemeral key (won't persist across restarts)
    return getRandomBytes(32);
  }
}
