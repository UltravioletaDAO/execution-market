# NOW-019: Registrar Chamba como merchant en x402r

## Metadata
- **Prioridad**: P0
- **Fase**: 2 - x402 Integration
- **Dependencias**: Ninguna (x402-rs ya está LIVE)
- **Archivos a crear**: Documentación, scripts de registro
- **Tiempo estimado**: 1-2 horas

## Descripción
Registrar Chamba como merchant en el protocolo x402r para poder recibir y procesar pagos.

## Contexto Técnico
- **Protocolo**: x402r (x402 con refunds)
- **Network**: Base Mainnet
- **Contract**: MerchantRouter `0xa48E8AdcA504D2f48e5AF6be49039354e922913F`
- **Token**: USDC (Base)

## Pasos de Registro

### 1. Crear Merchant Wallet
```bash
# Generar nueva wallet para Chamba merchant operations
# IMPORTANTE: Guardar private key en AWS Secrets Manager

# Usando cast (foundry)
cast wallet new

# Output:
# Address: 0x...
# Private Key: 0x...
```

### 2. Registrar Merchant en MerchantRouter

```typescript
// scripts/register_merchant.ts
import { createWalletClient, http, parseAbi } from 'viem';
import { base } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';

const MERCHANT_ROUTER = '0xa48E8AdcA504D2f48e5AF6be49039354e922913F';

const abi = parseAbi([
  'function registerMerchant(string calldata name, string calldata metadata) external returns (uint256)',
  'function getMerchant(address merchant) external view returns (tuple(uint256 id, string name, string metadata, bool active))'
]);

async function registerMerchant() {
  const account = privateKeyToAccount(process.env.MERCHANT_PRIVATE_KEY as `0x${string}`);

  const client = createWalletClient({
    account,
    chain: base,
    transport: http()
  });

  const hash = await client.writeContract({
    address: MERCHANT_ROUTER,
    abi,
    functionName: 'registerMerchant',
    args: [
      'Chamba',
      JSON.stringify({
        description: 'Human execution layer for AI agents',
        website: 'https://chamba.ultravioleta.xyz',
        support: 'support@ultravioleta.xyz'
      })
    ]
  });

  console.log('Registration tx:', hash);
  return hash;
}

registerMerchant();
```

### 3. Deploy Relay Proxy

```typescript
// scripts/deploy_relay.ts
import { createWalletClient, http, parseAbi } from 'viem';
import { base } from 'viem/chains';

const DEPOSIT_RELAY_FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814';

const abi = parseAbi([
  'function createRelay(address merchant, address token) external returns (address)',
  'function getRelay(address merchant, address token) external view returns (address)'
]);

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

async function deployRelay() {
  const account = privateKeyToAccount(process.env.MERCHANT_PRIVATE_KEY as `0x${string}`);

  const client = createWalletClient({
    account,
    chain: base,
    transport: http()
  });

  const hash = await client.writeContract({
    address: DEPOSIT_RELAY_FACTORY,
    abi,
    functionName: 'createRelay',
    args: [account.address, USDC_BASE]
  });

  console.log('Relay deployment tx:', hash);

  // Get relay address after confirmation
  // const relayAddress = await client.readContract({...});

  return hash;
}

deployRelay();
```

## Configuración Final

```yaml
# config/x402.yaml
merchant:
  address: "0x..."  # Merchant wallet address
  relay_address: "0x..."  # Deployed relay proxy
  network: base
  chain_id: 8453

contracts:
  merchant_router: "0xa48E8AdcA504D2f48e5AF6be49039354e922913F"
  deposit_relay_factory: "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814"
  usdc: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

fees:
  platform_percent: 8  # 8% platform fee
  min_payout_usdc: 0.50
```

## Criterios de Éxito
- [ ] Merchant wallet creada
- [ ] Private key guardada en Secrets Manager
- [ ] Merchant registrado en MerchantRouter
- [ ] Relay proxy deployed
- [ ] Configuración guardada
- [ ] Test payment exitoso

## Comandos de Verificación
```bash
# Verificar registro de merchant
cast call $MERCHANT_ROUTER "getMerchant(address)" $MERCHANT_ADDRESS --rpc-url https://mainnet.base.org

# Verificar relay
cast call $DEPOSIT_RELAY_FACTORY "getRelay(address,address)" $MERCHANT_ADDRESS $USDC_ADDRESS --rpc-url https://mainnet.base.org

# Test small payment (0.01 USDC)
# ... usar x402 SDK
```

## Addresses Oficiales (Base Mainnet)

| Contract | Address |
|----------|---------|
| MerchantRouter | `0xa48E8AdcA504D2f48e5AF6be49039354e922913F` |
| DepositRelayFactory | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |

## Security Checklist
- [ ] Private key NEVER in code
- [ ] Private key ONLY in Secrets Manager
- [ ] Relay proxy deployed from merchant wallet
- [ ] Test on Sepolia first if unsure
