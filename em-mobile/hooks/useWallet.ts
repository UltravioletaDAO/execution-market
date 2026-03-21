import { useAuth } from "../providers/AuthProvider";

/**
 * useWallet — thin wrapper over AuthProvider for wallet state.
 * Dynamic.xyz handles wallet connection; this hook provides
 * a convenient API for components that need wallet info.
 */
export function useWallet() {
  const { wallet, isAuthenticated, isLoading, logout, openAuth } = useAuth();

  return {
    address: wallet,
    isConnected: isAuthenticated,
    isConnecting: isLoading,
    disconnect: logout,
    openAuth,
  };
}
