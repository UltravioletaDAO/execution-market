# Roadmap — Next Steps (Feb 11, 2026)

> Agreed with user as priority order after CI stabilization

---

## Current Blocker: ERC-8004 Integration

**Before expanding to multi-chain or any other feature, we need ERC-8004 working end-to-end.**

### What's needed:
- [ ] Worker gets ERC-8004 identity on registration (gasless via facilitator)
- [ ] Auto-rate worker on-chain after task approval
- [ ] Auto-rate agent on-chain after task completion
- [ ] Reputation scores visible in dashboard
- [ ] Full lifecycle: register → work → get rated → reputation grows

---

## Option A: Fase 2 Multi-chain Deployment (After ERC-8004)
**Timeline:** 2-4 hours
1. Deploy PaymentOperator on 7 pending networks (Ethereum, Polygon, Arbitrum, Avalanche, Celo, Monad, Optimism)
2. Register in facilitator's `addresses.rs`
3. Update token registry in `sdk_client.py`
4. E2E test Fase 2 on each network

## Option B: Multi-token Support Testing
**Timeline:** 1-2 hours
1. Test Fase 1/2 with USDT, EURC, PYUSD
2. Verify dashboard token selector
3. Add e2e tests

## Option C: Admin Dashboard Completion
**Timeline:** 3-5 hours
1. Dispute management
2. Payment override
3. Analytics
4. Deploy

## Option D: Solana Integration
**Timeline:** 4-6 hours
1. Design SPL payment flow
2. Implement transfers
3. Test on Devnet/Mainnet-Beta

---

## Priority Order
1. **ERC-8004 end-to-end** (BLOCKER — do this first)
2. **Option A** — Fase 2 multi-chain
3. **Option B** — Multi-token
4. **Option C** — Admin dashboard
5. **Option D** — Solana
