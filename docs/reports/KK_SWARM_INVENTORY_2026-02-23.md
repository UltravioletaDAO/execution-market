# KK Swarm Inventory — 2026-02-23

> Snapshot after fund rebalancing v3. All balances verified on-chain.

## Summary

| Metric | Value |
|--------|-------|
| Total agents | 24 |
| Chains covered | 8 (Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad) |
| Wallet-chain slots | 192/192 funded |
| Stablecoins in use | 5 (USDC, EURC, AUSD, PYUSD, USDT) |
| Total in agents | **$148.12** |
| Total in master | **$42.81** |
| **Grand total** | **$190.93** |
| Per-agent average | **$6.17** |

## Master Wallet

**Address**: `0xD3868E1eD738CED6945A574a7c769433BeD5d474`

### Stablecoin Balances

| Chain | USDC | EURC | AUSD | PYUSD | USDT | **Total** |
|-------|------|------|------|-------|------|-----------|
| Base | $6.54 | $0.68 | - | - | - | **$7.22** |
| Ethereum | $0.24 | $0.20 | $1.12 | $2.21 | - | **$3.77** |
| Polygon | $6.20 | - | $0.07 | - | - | **$6.27** |
| Arbitrum | $6.80 | - | $0.00 | - | $1.29 | **$8.09** |
| Avalanche | $0.84 | $1.72 | $3.69 | - | - | **$6.25** |
| Optimism | $5.22 | - | - | - | - | **$5.22** |
| Celo | $0.21 | - | - | - | $0.38 | **$0.59** |
| Monad | $5.31 | - | $0.08 | - | - | **$5.39** |
| **Total** | **$31.37** | **$2.59** | **$4.97** | **$2.21** | **$1.67** | **$42.81** |

### Native Gas Balances

| Chain | Symbol | Balance |
|-------|--------|---------|
| Base | ETH | 0.000407 |
| Ethereum | ETH | 0.004215 |
| Polygon | POL | 11.590 |
| Arbitrum | ETH | 0.003252 |
| Avalanche | AVAX | 1.431 |
| Optimism | ETH | 0.002316 |
| Celo | CELO | 0.647 |
| Monad | MON | 19.446 |

---

## Agent Wallets (24 agents)

### Per-Agent Balance by Chain

Each agent holds stablecoins + native gas on all 8 chains. All 24 agents are identically funded except `kk-coordinator` and `kk-karma-hello` which have $0.10 less USDC on Base (from an earlier distribution round).

| Chain | USDC | EURC | AUSD | PYUSD | USDT | **Total/agent** | Tasks at $0.10 |
|-------|------|------|------|-------|------|-----------------|----------------|
| Monad | $0.75 | - | $0.25 | - | - | **$1.00** | ~10 |
| Arbitrum | $0.75 | - | - | - | $0.20 | **$0.95** | ~9 |
| Avalanche | $0.50 | $0.35 | $0.10 | - | - | **$0.95** | ~9 |
| Base | $0.75 | $0.10 | - | - | - | **$0.85** | ~8 |
| Polygon | $0.50 | - | $0.25 | - | - | **$0.75** | ~7 |
| Optimism | $0.75 | - | - | - | - | **$0.75** | ~7 |
| Celo | $0.02 | - | - | - | $0.45 | **$0.47** | ~4 |
| Ethereum | $0.10 | $0.12 | $0.12 | $0.12 | - | **$0.46** | ~4 |
| **Total** | **$4.12** | **$0.57** | **$0.72** | **$0.12** | **$0.65** | **$6.18** | **~58** |

> `kk-coordinator` and `kk-karma-hello`: Base USDC = $0.65 (total $6.08/agent).

### Per-Agent Native Gas

| Chain | Symbol | Amount | Sufficient for |
|-------|--------|--------|----------------|
| Base | ETH | 0.0002 | ~50 TXs |
| Ethereum | ETH | 0.0003 | ~5 TXs |
| Polygon | POL | 0.1000 | ~200 TXs |
| Arbitrum | ETH | 0.0002 | ~50 TXs |
| Avalanche | AVAX | 0.0050 | ~20 TXs |
| Optimism | ETH | 0.0002 | ~50 TXs |
| Celo | CELO | 0.0100 | ~100 TXs |
| Monad | MON | 0.0100 | ~100 TXs |

### Aggregate Token Totals (all 24 agents)

| Token | Total across agents |
|-------|---------------------|
| USDC | $98.68 |
| AUSD | $17.28 |
| USDT | $15.60 |
| EURC | $13.68 |
| PYUSD | $2.88 |
| **Total** | **$148.12** |

---

## Full Agent Roster

| # | Agent | Wallet | Total |
|---|-------|--------|-------|
| 1 | kk-coordinator | HD path m/44'/60'/0'/0/0 | $6.08 |
| 2 | kk-karma-hello | HD path m/44'/60'/0'/0/1 | $6.08 |
| 3 | kk-skill-extractor | HD path m/44'/60'/0'/0/2 | $6.18 |
| 4 | kk-voice-extractor | HD path m/44'/60'/0'/0/3 | $6.18 |
| 5 | kk-validator | HD path m/44'/60'/0'/0/4 | $6.18 |
| 6 | kk-soul-extractor | HD path m/44'/60'/0'/0/5 | $6.18 |
| 7 | kk-juanjumagalp | HD path m/44'/60'/0'/0/6 | $6.18 |
| 8 | kk-elboorja | HD path m/44'/60'/0'/0/7 | $6.18 |
| 9 | kk-stovedove | HD path m/44'/60'/0'/0/8 | $6.18 |
| 10 | kk-0xroypi | HD path m/44'/60'/0'/0/9 | $6.18 |
| 11 | kk-sanvalencia2 | HD path m/44'/60'/0'/0/10 | $6.18 |
| 12 | kk-0xjokker | HD path m/44'/60'/0'/0/11 | $6.18 |
| 13 | kk-cyberpaisa | HD path m/44'/60'/0'/0/12 | $6.18 |
| 14 | kk-cymatix | HD path m/44'/60'/0'/0/13 | $6.18 |
| 15 | kk-eljuyan | HD path m/44'/60'/0'/0/14 | $6.18 |
| 16 | kk-1nocty | HD path m/44'/60'/0'/0/15 | $6.18 |
| 17 | kk-elbitterx | HD path m/44'/60'/0'/0/16 | $6.18 |
| 18 | kk-acpm444 | HD path m/44'/60'/0'/0/17 | $6.18 |
| 19 | kk-davidtherich | HD path m/44'/60'/0'/0/18 | $6.18 |
| 20 | kk-karenngo | HD path m/44'/60'/0'/0/19 | $6.18 |
| 21 | kk-datbo0i_lp | HD path m/44'/60'/0'/0/20 | $6.18 |
| 22 | kk-psilocibin3 | HD path m/44'/60'/0'/0/21 | $6.18 |
| 23 | kk-0xsoulavax | HD path m/44'/60'/0'/0/22 | $6.18 |
| 24 | kk-painbrayan | HD path m/44'/60'/0'/0/23 | $6.18 |

> Wallets derived from swarm mnemonic stored in AWS Secrets Manager (`kk/swarm-seed`). HD paths shown for reference — actual addresses omitted for security.

---

## Distribution by Chain (agents + master)

| Chain | Agents (24) | Master | **Total** | % of grand total |
|-------|-------------|--------|-----------|------------------|
| Arbitrum | $22.80 | $8.09 | **$30.89** | 16.2% |
| Monad | $24.00 | $5.39 | **$29.39** | 15.4% |
| Avalanche | $22.80 | $6.25 | **$29.05** | 15.2% |
| Base | $20.40 | $7.22 | **$27.62** | 14.5% |
| Optimism | $18.00 | $5.22 | **$23.22** | 12.2% |
| Polygon | $18.00 | $6.27 | **$24.27** | 12.7% |
| Ethereum | $11.04 | $3.77 | **$14.81** | 7.8% |
| Celo | $11.28 | $0.59 | **$11.87** | 6.2% |
| **Total** | **$148.32** | **$42.81** | **$191.13** | 100% |

---

## Facilitator Token Support Matrix

Shows which stablecoins the x402 Facilitator can settle on each chain:

| Chain | USDC | EURC | AUSD | PYUSD | USDT |
|-------|------|------|------|-------|------|
| Base | Y | Y | - | - | - |
| Ethereum | Y | Y | Y | Y | - |
| Polygon | Y | - | Y | - | - |
| Arbitrum | Y | - | Y | - | Y |
| Avalanche | Y | Y | Y | - | - |
| Optimism | Y | - | - | - | Y |
| Celo | Y | - | - | - | Y |
| Monad | Y | - | Y | - | Y |

---

## Notes

- **Celo is underfunded** ($0.47/agent vs ~$0.95 target) because Squid Router had zero USDC liquidity to Celo during the rebalancing session. deBridge does not support Celo. Retry bridge when Squid restores liquidity.
- **Ethereum is intentionally light** ($0.46/agent) — L1 gas makes frequent small tasks uneconomical. Agents carry 4 diverse stablecoins for protocol coverage.
- **Master reserve** ($42.81, 22%) is spread across chains with no single chain exceeding $8.09 (Arbitrum).
- **Monad master USDC**: $5.31 (well under the $10 cap constraint).
- All agent wallets were derived from the same HD mnemonic for operational simplicity. Mnemonic in AWS Secrets Manager `kk/swarm-seed`.
- Gas tokens are sufficient for 20-200 TXs per chain depending on network costs.

---

*Generated 2026-02-23. Run `npx tsx kk/check-balances.ts` and `npx tsx kk/check-full-inventory.ts` for live data.*
