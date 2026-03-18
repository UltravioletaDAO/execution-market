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

      // Persist dev private key in SecureStore so identity survives app restarts.
      // Without this, every connectDev() call creates a new identity and prior
      // conversations become invisible.
      const SecureStore = await import("expo-secure-store");
      let pk = await SecureStore.getItemAsync("xmtp_dev_pk");
      if (!pk) {
        pk = generatePrivateKey();
        await SecureStore.setItemAsync("xmtp_dev_pk", pk);
      }
      const { PublicIdentity } = await import("@xmtp/react-native-sdk");
      const account = privateKeyToAccount(pk as `0x${string}`);
      const devSigner = {
        getIdentifier: async () => new PublicIdentity(account.address, "ETHEREUM"),
        signMessage: async (message: string) => ({
          signature: await account.signMessage({ message }),
          publicKey: undefined,
          authenticatorData: undefined,
          clientDataJson: undefined,
        }),
        getChainId: () => undefined,
        getBlockNumber: () => undefined,
        signerType: () => undefined,
      };

      const xmtp = await Client.create(devSigner, {
        env: "production",
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
// XMTP react-native-sdk v5 signer interface
// Signer.js checks: isWalletClient (type==='walletClient') OR has getIdentifier()
function buildV5Signer(address: string, sign: (msg: string) => Promise<string>) {
  return {
    getIdentifier: async () => {
      const { PublicIdentity } = await import("@xmtp/react-native-sdk");
      return new PublicIdentity(address, "ETHEREUM");
    },
    signMessage: async (message: string) => ({
      signature: await sign(message),
      publicKey: undefined,
      authenticatorData: undefined,
      clientDataJson: undefined,
    }),
    getChainId: () => undefined,
    getBlockNumber: () => undefined,
    signerType: () => undefined,
  };
}

function buildNativeSigner(rawSigner: any, fallbackAddress: string) {
  // Case 1: viem WalletClient (type === 'walletClient') — SDK handles natively
  if (rawSigner && rawSigner.type === "walletClient") {
    return rawSigner;
  }

  // Case 2: viem WalletClient without .type but has .account
  if (rawSigner && typeof rawSigner.signMessage === "function" && rawSigner.account) {
    const address = rawSigner.account.address ?? fallbackAddress;
    return buildV5Signer(address, (msg) =>
      rawSigner.signMessage({ message: msg, account: rawSigner.account })
    );
  }

  // Case 3: ethers Signer (v5 or v6)
  if (rawSigner && typeof rawSigner.signMessage === "function" && typeof rawSigner.getAddress === "function") {
    return buildV5Signer(fallbackAddress, (msg) => rawSigner.signMessage(msg));
  }

  // Case 4: Dynamic wallet with connector.signMessage
  if (rawSigner && rawSigner.connector && typeof rawSigner.connector.signMessage === "function") {
    const address = rawSigner.address ?? fallbackAddress;
    return buildV5Signer(address, (msg) => rawSigner.connector.signMessage({ message: msg }));
  }

  // Case 5: signMessage only
  if (rawSigner && typeof rawSigner.signMessage === "function") {
    return buildV5Signer(fallbackAddress, (msg) => rawSigner.signMessage(msg));
  }

  // Last resort
  return buildV5Signer(fallbackAddress, async () => {
    throw new Error("[XMTP] Cannot sign: no compatible method found on wallet connector");
  });
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
