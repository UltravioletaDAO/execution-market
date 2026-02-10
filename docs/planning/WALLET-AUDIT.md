# AWS Secrets Wallet Audit

**Date:** 2025-02-09  
**Objective:** Find the funded wallet mentioned by Saúl that's "funded on all networks with USDC for testing all stablecoin flows"

## AWS Secrets Checked

**Total secrets found:** 26
- ✅ Checked 14 secrets that could contain wallets
- 🔍 Found 6 EVM wallets with actual USDC balances on Base
- ❌ No "heavily funded" wallet found

## Wallets Found with USDC Balances (Base Network)

| Secret Name | Wallet Address | USDC Balance |
|-------------|----------------|--------------|
| `karmacadabra-test-seller` | 0x4dFB1Cd42604194e79eDaCff4e0d28A576e40d19 | ~0.92 USDC |
| `karmacadabra-test-buyer` | 0x6bdc03ae4BBAb31843dDDaAE749149aE675ea011 | ~4.69 USDC |
| `test-buyer-client-1` | 0xaeabb3ee30d13FA83AD8e3FDa8322C98530B7F3B | ~4.79 USDC |
| `test-buyer-client-2` | 0x20Bb866105414Ef7AAC273d5fa782C7F83336b50 | ~4.87 USDC |

**Total USDC found:** ~15.27 USDC

## Other Wallets Found (0 USDC Balance)

### Main `karmacadabra` Secret Contains:
- **validator-agent:** Private key 0xf407...f83 (address not provided)
- **karma-hello-agent:** Private key 0x50db...898 (address not provided)  
- **abracadabra-agent:** Private key 0xe066...b1c (address not provided)
- **client-agent:** 0xCf30021812F27132d36dc791E0eC17f34B4eE8BA (0 USDC)
- **voice-extractor-agent:** 0xDd63D5840090B98D9EB86f2c31974f9d6c270b17 (0 USDC)
- **erc-20:** 0x34033041a5944B8F10f8E4D8496Bfb84f1A293A8 (0 USDC)
- **93 user-agents:** Various addresses (spot-checked several, all 0 USDC)

### Solana Wallets Found:
- `karmacadabra-test-seller-solana`: Ez4frLQzDbV1AT9BNJkQFEjyTFRTsEwJ5YFaSGG8nRGB
- `karmacadabra-test-buyer-solana`: Hn344ScrpYT99Vp9pwQPfAtA3tfMLrhoVhQ445efCvNP

## Previously Checked (Empty)
- `erc8004-sniper/hotwallet`: 0xD577...32A0 (0 USDC on all chains)
- `chamba/production`: Contains placeholders, not actual wallets
- `chamba/admin-key`: API key only, not a wallet
- EM Treasury: 0xae07...9a6ad (only $0.11 USDC on Base)

## Not Checked (Non-wallet secrets)
- `openai.api.key`
- `instagram.credentials.cuchorapido.ai`
- `lagentedao.twitch.notification.telegram.bot.secrets`
- `karmacadabra-quicknode-base-rpc` (RPC URL only)
- `karmacadabra-marketplace` (null private key)
- `pixel-marketplace/x-twitter-credentials`
- `metatof-prod-llm-api-keys`
- `meshrelay/ssh-key`
- `uvd-production-verification-api-secrets`
- `meshrelay-ec2-ssh-key`
- `uvd-production-meshrelay-credentials`

## Summary

**❌ WALLET NOT FOUND**

The heavily funded wallet Saúl mentioned does not appear to exist in the current AWS Secrets Manager configuration. The highest balance found was ~4.87 USDC in `test-buyer-client-2`.

**Recommendations:**
1. Check if the wallet exists in a different AWS account or region
2. Verify if it's stored in a different secret manager (HashiCorp Vault, etc.)
3. Check if it's stored locally or in a different environment variable
4. Contact Saúl for the exact secret name or location

**Next Steps:**
- Derive addresses from private keys that don't have addresses provided
- Check balances on other networks (Arbitrum, Polygon, Avalanche, Ethereum, Celo)
- Check if any wallets need to be topped up for testing purposes