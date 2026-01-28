# NOW-205: Desplegar Contratos en Ethereum Mainnet

## Metadata
- **Prioridad**: P1 (Para ERC-8004 el jueves)
- **Fase**: Production Deployment
- **Dependencias**: Wallet fondeada con ETH
- **Archivos**: `contracts/`
- **Tiempo estimado**: 1-2 horas

## Descripción
Desplegar ChambaEscrow.sol en Ethereum Mainnet para el lanzamiento de ERC-8004.

## BLOQUEADO: Requiere Wallet Fondeada
```
ACCIÓN REQUERIDA DEL USUARIO:
1. Crear wallet nueva o usar existente
2. Fondear con ~0.1 ETH para gas de deployment
3. Proporcionar private key (o usar hardware wallet)
```

## Contratos a Desplegar
1. `ChambaEscrow.sol` - Escrow con partial release (30/70%)
2. (Opcional) Proxy para upgrades futuros

## Pasos de Deployment

### 1. Configurar Hardhat para Mainnet
```javascript
// hardhat.config.ts
networks: {
  mainnet: {
    url: process.env.RPC_URL_ETHEREUM,
    accounts: [process.env.DEPLOYER_PRIVATE_KEY],
    chainId: 1,
  },
}
```

### 2. Verificar contrato en local
```bash
cd contracts
npx hardhat compile
npx hardhat test
```

### 3. Deploy a Mainnet
```bash
# Dry run primero
npx hardhat run scripts/deploy.ts --network mainnet --dry-run

# Deploy real
npx hardhat run scripts/deploy.ts --network mainnet
```

### 4. Verificar en Etherscan
```bash
npx hardhat verify --network mainnet <CONTRACT_ADDRESS> <CONSTRUCTOR_ARGS>
```

### 5. Guardar direcciones
```bash
# Agregar a .env.deployed
CHAMBA_ESCROW_MAINNET=0x...
```

## Estimación de Gas
```
ChambaEscrow deployment: ~2,000,000 gas
Gas price (estimate): 30 gwei
Cost: ~0.06 ETH (~$150 USD)
```

## Variables de Entorno Requeridas
```bash
RPC_URL_ETHEREUM=https://eth-mainnet.g.alchemy.com/v2/...
DEPLOYER_PRIVATE_KEY=0x...
ETHERSCAN_API_KEY=...  # Para verificación
```

## Criterios de Éxito
- [ ] Contrato desplegado en mainnet
- [ ] Verificado en Etherscan
- [ ] Dirección guardada en .env.deployed
- [ ] Test de interacción exitoso
- [ ] Documentado para ERC-8004

## Plan B: Usar x402r Contracts Existentes
Si no hay tiempo, usar los contratos x402r que ya existen en Base:
- Factory: `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814`
- Escrow: `0xC409d3A6e3D67cAa1CCd0CC5f0Ff2F89DF15f6bC`

Esto permite escrow trustless sin desplegar nuevos contratos.
