// Must be the FIRST import — patches global.crypto before any crypto usage
import "react-native-get-random-values";
import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from "react";
import Constants, { ExecutionEnvironment } from "expo-constants";
// Use @noble libs directly — viem/accounts subpath doesn't resolve in Metro
import { secp256k1 } from "@noble/curves/secp256k1";
import { keccak_256 } from "@noble/hashes/sha3";

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
  const clientRef = useRef<any>(null);

  // Close client on unmount to prevent IDBDatabase "connection is closing" errors
  useEffect(() => {
    return () => {
      try {
        clientRef.current?.close();
      } catch {
        // Ignore close errors during teardown
      }
      clientRef.current = null;
    };
  }, []);

  // Helper: safely close previous client before setting a new one
  const setClientSafe = useCallback((newClient: any) => {
    const prev = clientRef.current;
    if (prev && prev !== newClient) {
      try {
        prev.close();
      } catch {
        // Ignore close errors
      }
    }
    clientRef.current = newClient;
    setClient(newClient);
  }, []);

  // Internal: create XMTP client with a generated identity (no real wallet needed)
  const connectWithGeneratedIdentity = useCallback(async () => {
    const { Client, PublicIdentity } = await import("@xmtp/react-native-sdk");
    const dbKey = await getOrCreateEncryptionKey();

    const SecureStore = await import("expo-secure-store");
    let pkHex = await SecureStore.getItemAsync("xmtp_dev_pk");
    if (!pkHex) {
      // Generate random 32-byte private key
      const pkBytes = secp256k1.utils.randomPrivateKey();
      pkHex = "0x" + bytesToHex(pkBytes);
      await SecureStore.setItemAsync("xmtp_dev_pk", pkHex);
    }

    const pkClean = pkHex.startsWith("0x") ? pkHex.slice(2) : pkHex;
    const pkBytes = hexToBytes(pkClean);
    const address = privateKeyToAddress(pkBytes);

    const signer = {
      getIdentifier: async () => new PublicIdentity(address, "ETHEREUM"),
      signMessage: async (message: string) => ({
        signature: signEthMessage(pkBytes, message),
        publicKey: undefined,
        authenticatorData: undefined,
        clientDataJson: undefined,
      }),
      getChainId: () => undefined,
      getBlockNumber: () => undefined,
      signerType: () => undefined,
    };

    return Client.create(signer, {
      env: "production",
      dbEncryptionKey: dbKey,
    });
  }, []);

  const connect = useCallback(async () => {
    if (IS_EXPO_GO) {
      setError("XMTP no está disponible en Expo Go. Usa el Android dev client.");
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      // Try real wallet signer first
      if (walletAddress && getSigner) {
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

          setClientSafe(xmtp);
          return;
        } catch (err) {
          console.warn("[XMTP] Wallet signer failed, falling back to generated identity:", err);
        }
      }

      // Fallback: generated identity (works for email-only users)
      console.log("[XMTP] Using generated identity for messaging");
      const xmtp = await connectWithGeneratedIdentity();
      setClientSafe(xmtp);
    } catch (err) {
      console.error("[XMTP] Connection failed:", err);
      setError(err instanceof Error ? err.message : "XMTP connection failed");
    } finally {
      setIsConnecting(false);
    }
  }, [walletAddress, getSigner, connectWithGeneratedIdentity]);

  // Explicit generated identity connect (kept for internal use)
  const connectDev = useCallback(async () => {
    if (IS_EXPO_GO) {
      setError("XMTP no está disponible en Expo Go. Usa el Android dev client.");
      return;
    }
    setIsConnecting(true);
    setError(null);
    try {
      const xmtp = await connectWithGeneratedIdentity();
      setIsDevMode(true);
      setClientSafe(xmtp);
    } catch (err) {
      console.error("[XMTP] Connect failed:", err);
      setError(err instanceof Error ? err.message : "XMTP connect failed");
    } finally {
      setIsConnecting(false);
    }
  }, [connectWithGeneratedIdentity]);

  const disconnect = useCallback(() => {
    try {
      clientRef.current?.close();
    } catch {
      // Ignore close errors
    }
    clientRef.current = null;
    setClient(null);
    setIsDevMode(false);
    setError(null);
  }, []);

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

// --- Ethereum crypto helpers using @noble (works in React Native) ---

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

function privateKeyToAddress(pk: Uint8Array): string {
  // Get uncompressed public key (65 bytes: 0x04 + x + y), strip the 0x04 prefix
  const pubKey = secp256k1.getPublicKey(pk, false).slice(1);
  // Keccak-256 hash, take last 20 bytes
  const hash = keccak_256(pubKey);
  const addrBytes = hash.slice(12);
  const addrHex = bytesToHex(addrBytes);
  // EIP-55 checksum
  const checksumHash = bytesToHex(keccak_256(new TextEncoder().encode(addrHex)));
  let checksummed = "0x";
  for (let i = 0; i < 40; i++) {
    checksummed += parseInt(checksumHash[i], 16) >= 8
      ? addrHex[i].toUpperCase()
      : addrHex[i];
  }
  return checksummed;
}

function signEthMessage(pk: Uint8Array, message: string): string {
  // EIP-191 personal_sign: "\x19Ethereum Signed Message:\n" + len + message
  const prefix = `\x19Ethereum Signed Message:\n${message.length}`;
  const prefixed = new TextEncoder().encode(prefix + message);
  const hash = keccak_256(prefixed);
  const sig = secp256k1.sign(hash, pk);
  // Serialize to 65-byte r+s+v format
  const r = sig.r.toString(16).padStart(64, "0");
  const s = sig.s.toString(16).padStart(64, "0");
  const v = (sig.recovery + 27).toString(16).padStart(2, "0");
  return "0x" + r + s + v;
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
