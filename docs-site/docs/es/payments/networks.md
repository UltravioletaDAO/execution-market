# Redes Soportadas

## Redes Principales

La integracion x402 de Chamba soporta pagos a traves de multiples redes compatibles con EVM. El facilitador en `facilitator.ultravioletadao.xyz` maneja el enrutamiento entre cadenas.

### Redes de Produccion

| Red | Chain ID | Direccion USDC | Estado |
|-----|----------|---------------|--------|
| **Base** | 8453 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | **Principal** |
| **Polygon** | 137 | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | Activa |
| **Optimism** | 10 | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | Activa |
| **Arbitrum** | 42161 | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | Activa |

### Redes de Prueba (Testnet)

| Red | Chain ID | Direccion USDC | Estado |
|-----|----------|---------------|--------|
| **Base Sepolia** | 84532 | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | Pruebas |
| **Sepolia** | 11155111 | Token de prueba | Pruebas |

### Redes Adicionales (via Facilitador)

El facilitador x402 soporta **17+ mainnets** incluyendo:
- Ethereum, BSC, Avalanche, Fantom, Gnosis, Celo, zkSync, Linea, Scroll, Mantle, y mas.

## Tokens Soportados

| Token | Decimales | Redes |
|-------|-----------|-------|
| **USDC** | 6 | Todas las redes (principal) |
| **EURC** | 6 | Base, Ethereum |
| **DAI** | 18 | Base, Ethereum, Polygon |
| **USDT** | 6 | Todas las redes |

## Contratos Escrow x402r

### Base Mainnet

| Contrato | Direccion |
|----------|-----------|
| **Escrow** | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| **DepositRelayFactory** | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| **RefundRequest** | `0x55e0Fb85833f77A0d699346E827afa06bcf58e4e` |
| **MerchantRouter** | `0xa48E8AdcA504D2f48e5AF6be49039354e922913F` |
| **USDC** | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |

### Base Sepolia (Testnet)

| Contrato | Direccion |
|----------|-----------|
| **Escrow** | `0xF7F2Bc463d79Bd3E5Cb693944B422c39114De058` |
| **Factory** | `0xf981D813842eE78d18ef8ac825eef8e2C8A8BaC2` |
| **USDC** | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |

## Despliegues de ChambaEscrow

| Red | Direccion | Estado |
|-----|-----------|--------|
| **Ethereum Mainnet** | `0x6c320efaC433690899725B3a7C84635430Acf722` | Desplegado |
| **Avalanche Mainnet** | `0xedA98AF95B76293a17399Af41A499C193A8DB51A` | Desplegado y Verificado |

## Seleccion de Red

La red recomendada para pagos en Chamba es **Base** debido a:
- Costos de gas bajos (~$0.01 por transaccion)
- Soporte nativo de USDC
- Disponibilidad del contrato escrow x402r
- Alto rendimiento y confiabilidad
