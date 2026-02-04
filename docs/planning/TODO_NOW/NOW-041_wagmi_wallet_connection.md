# NOW-041: Implementar Wagmi wallet connection REAL

## Metadata
- **Prioridad**: P1
- **Fase**: 3 - Dashboard
- **Dependencias**: NOW-008
- **Archivos a modificar**: `dashboard/src/components/AuthModal.tsx`, `dashboard/src/lib/wagmi.ts`
- **Tiempo estimado**: 2-3 horas

## Descripción
El dashboard tiene Wagmi configurado pero NO USADO (stub only). Implementar conexión real de wallet.

## Problema Actual
- AuthModal existe pero usa stubs
- Wagmi provider configurado pero useConnect/useAccount no conectados
- Wallet connection es fake/mock

## Código de Referencia

### wagmi.ts (actualizar)
```typescript
// dashboard/src/lib/wagmi.ts
import { createConfig, http } from 'wagmi';
import { base, baseSepolia } from 'wagmi/chains';
import { injected, walletConnect } from 'wagmi/connectors';

const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID;

export const config = createConfig({
  chains: [base, baseSepolia],
  connectors: [
    injected(),
    walletConnect({ projectId }),
  ],
  transports: {
    [base.id]: http(),
    [baseSepolia.id]: http(),
  },
});
```

### AuthModal.tsx (actualizar)
```tsx
// dashboard/src/components/AuthModal.tsx
import { useConnect, useAccount, useDisconnect } from 'wagmi';
import { useEffect } from 'react';
import { supabase } from '@/lib/supabase';

export function AuthModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { connectors, connect, isPending, error } = useConnect();
  const { address, isConnected } = useAccount();
  const { disconnect } = useDisconnect();

  // When wallet connects, link to Supabase
  useEffect(() => {
    if (isConnected && address) {
      linkWalletToSession(address);
    }
  }, [isConnected, address]);

  async function linkWalletToSession(walletAddress: string) {
    try {
      // Get or create executor
      const { data: executorId } = await supabase.rpc('get_or_create_executor', {
        p_wallet_address: walletAddress
      });

      // Store in local state/context
      localStorage.setItem('em_executor_id', executorId);
      localStorage.setItem('em_wallet', walletAddress);

      onClose();
    } catch (err) {
      console.error('Failed to link wallet:', err);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded-xl p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold mb-4">Connect Wallet</h2>

        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
            {error.message}
          </div>
        )}

        <div className="space-y-3">
          {connectors.map((connector) => (
            <button
              key={connector.id}
              onClick={() => connect({ connector })}
              disabled={isPending}
              className="w-full flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              <img
                src={getConnectorIcon(connector.id)}
                alt={connector.name}
                className="w-8 h-8"
              />
              <span className="font-medium">{connector.name}</span>
              {isPending && <span className="ml-auto">Connecting...</span>}
            </button>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t">
          <p className="text-sm text-gray-500 text-center">
            Don't have a wallet?{' '}
            <a href="#" className="text-violet-600 hover:underline">
              Create with email
            </a>
          </p>
        </div>

        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

function getConnectorIcon(connectorId: string): string {
  const icons: Record<string, string> = {
    injected: '/icons/metamask.svg',
    walletConnect: '/icons/walletconnect.svg',
  };
  return icons[connectorId] || '/icons/wallet.svg';
}
```

### useAuth hook (crear)
```typescript
// dashboard/src/hooks/useAuth.ts
import { useAccount } from 'wagmi';
import { useEffect, useState } from 'react';

export function useAuth() {
  const { address, isConnected } = useAccount();
  const [executorId, setExecutorId] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('em_executor_id');
    if (stored) setExecutorId(stored);
  }, []);

  return {
    address,
    isConnected,
    executorId,
    isAuthenticated: isConnected && !!executorId,
  };
}
```

## Criterios de Éxito
- [ ] MetaMask connection funciona
- [ ] WalletConnect funciona
- [ ] Address se muestra correctamente
- [ ] Executor se crea/obtiene de Supabase
- [ ] Session persiste en localStorage
- [ ] Disconnect funciona
- [ ] Error handling para rejected connections

## Test con Playwright
```typescript
// tests/e2e/wallet-connection.spec.ts
import { test, expect } from '@playwright/test';

test('wallet connection flow', async ({ page }) => {
  await page.goto('/');

  // Click connect button
  await page.click('button:has-text("Connect")');

  // Modal should appear
  await expect(page.locator('text=Connect Wallet')).toBeVisible();

  // MetaMask option should be available
  await expect(page.locator('text=MetaMask')).toBeVisible();
});
```
