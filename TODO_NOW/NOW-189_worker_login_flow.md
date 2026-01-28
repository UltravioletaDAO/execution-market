# NOW-189: Worker Login Flow

**Prioridad**: P0
**Status**: TODO
**Dependencias**: NOW-188, NOW-041

## Problema

Workers necesitan autenticarse para:
- Ver tareas disponibles cerca de su ubicación
- Aplicar a tareas
- Subir evidencia
- Recibir pagos

Actualmente no hay flujo de login para workers.

## Solución

Implementar autenticación basada en wallet signature que crea una sesión JWT.

## Archivos a Crear/Modificar

- `dashboard/src/components/WorkerAuth.tsx` - Componente de auth
- `dashboard/src/hooks/useWorkerSession.ts` - Hook de sesión
- `dashboard/src/context/AuthContext.tsx` - Contexto global
- `mcp_server/api/worker_auth.py` - Endpoint de verificación

## Flujo de Autenticación

```
1. Worker conecta wallet (MetaMask, WalletConnect, Crossmint)
2. Frontend solicita firma de mensaje: "Sign in to Chamba: {nonce}"
3. Backend verifica firma → crea/obtiene executor en Supabase
4. Backend genera JWT con executor_id
5. Frontend guarda JWT en localStorage
6. Requests incluyen JWT en header Authorization
```

## Implementación

### 1. WorkerAuth.tsx

```tsx
import { useAccount, useSignMessage } from 'wagmi';
import { useState } from 'react';

export function WorkerAuth({ onSuccess }: { onSuccess: () => void }) {
  const { address } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!address) return;
    setIsLoading(true);

    try {
      // 1. Get nonce from backend
      const nonceRes = await fetch(`/api/auth/nonce?address=${address}`);
      const { nonce } = await nonceRes.json();

      // 2. Sign message
      const message = `Sign in to Chamba: ${nonce}`;
      const signature = await signMessageAsync({ message });

      // 3. Verify signature and get JWT
      const loginRes = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, signature, message }),
      });

      const { token, executor } = await loginRes.json();

      // 4. Store session
      localStorage.setItem('chamba_token', token);
      localStorage.setItem('chamba_executor', JSON.stringify(executor));

      onSuccess();
    } catch (error) {
      console.error('Login failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button onClick={handleLogin} disabled={isLoading}>
      {isLoading ? 'Signing in...' : 'Sign in as Worker'}
    </button>
  );
}
```

### 2. Backend worker_auth.py

```python
from fastapi import APIRouter, HTTPException
from eth_account.messages import encode_defunct
from web3 import Web3
import jwt
import secrets

router = APIRouter(prefix="/api/auth", tags=["Worker Auth"])

# In-memory nonce storage (use Redis in production)
_nonces: dict[str, str] = {}

@router.get("/nonce")
async def get_nonce(address: str):
    """Generate nonce for wallet signature."""
    nonce = secrets.token_hex(16)
    _nonces[address.lower()] = nonce
    return {"nonce": nonce}

@router.post("/login")
async def login(address: str, signature: str, message: str):
    """Verify signature and create session."""
    address_lower = address.lower()

    # Verify nonce is valid
    expected_nonce = _nonces.get(address_lower)
    if not expected_nonce or expected_nonce not in message:
        raise HTTPException(400, "Invalid nonce")

    # Verify signature
    w3 = Web3()
    message_hash = encode_defunct(text=message)
    recovered = w3.eth.account.recover_message(message_hash, signature=signature)

    if recovered.lower() != address_lower:
        raise HTTPException(401, "Invalid signature")

    # Clear nonce (single use)
    del _nonces[address_lower]

    # Get or create executor
    from supabase_client import get_client
    client = get_client()

    result = client.rpc('get_or_create_executor', {
        'p_wallet_address': address
    }).execute()

    executor = result.data

    # Generate JWT
    token = jwt.encode(
        {
            "executor_id": executor["id"],
            "wallet": address,
            "exp": datetime.now(UTC) + timedelta(days=7)
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256"
    )

    return {"token": token, "executor": executor}
```

## Criterios de Aceptación

- [ ] Worker puede conectar wallet
- [ ] Firma mensaje de autenticación
- [ ] Recibe JWT válido por 7 días
- [ ] JWT se guarda en localStorage
- [ ] Requests a API incluyen JWT
- [ ] Executor se crea en Supabase si no existe

## Testing

```bash
# Test endpoint
curl -X GET "http://localhost:8000/api/auth/nonce?address=0x123..."
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"address": "0x...", "signature": "0x...", "message": "Sign in to Chamba: abc123"}'
```
