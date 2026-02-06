# Auth Session Strategy — Execution Market

## Overview

Execution Market uses **Dynamic.xyz** for wallet authentication (no email/password).
The wallet IS the identity. Supabase stores executor profiles keyed by `wallet_address`.

## Auth Flow

```
User clicks "Start Earning"
       |
       v
Dynamic.xyz Modal opens
       |
       v
User connects wallet (MetaMask, WalletConnect, Coinbase, etc.)
       |
       v
Dynamic SDK verifies ownership (signature)
       |
       v
AuthContext: useDynamicContext() detects wallet
       |
       v
get_or_create_executor(wallet_address) → Supabase RPC
       |
       v
Executor profile loaded → user is authenticated
```

## Session Persistence

### Dynamic.xyz SDK
- Sessions persist automatically via `localStorage` tokens
- `initialAuthenticationMode: 'connect'` enables auto-reconnect on page load
- When user returns, SDK restores wallet connection without requiring new signature
- Session lifetime: managed by Dynamic.xyz dashboard settings (default: 7 days)

### Supabase Session
- Anonymous Supabase session created for RLS compliance (`auth.uid()`)
- `link_wallet_to_session` RPC ties anonymous user to executor record
- Supabase session TTL: default 1 hour, auto-refreshes via `supabase.auth.onAuthStateChange()`

### localStorage Keys
| Key | Purpose | Cleared on logout |
|-----|---------|-------------------|
| `em_last_wallet_address` | Hint for executor lookup on page load | Yes |
| `em_user_type` | Worker or Agent role selection | Yes |
| Dynamic SDK internal keys | Wallet session persistence | Yes (via `handleLogOut()`) |

## Race Condition Protection

The AuthContext protects against timing races during SDK initialization:

1. `sdkHasLoaded` → sets `dynamicInitialized = true`
2. `isAuthenticated` requires ALL of: `dynamicInitialized && isLoggedIn && !!dynamicWalletAddress`
3. `openAuthModal()` blocks while `loading && !dynamicInitialized` to prevent premature sign-in prompt
4. `WorkerGuard` / `AgentGuard` show loading spinner during SDK restore

## Token/Session TTL Summary

| Layer | TTL | Refresh |
|-------|-----|---------|
| Dynamic.xyz wallet session | 7 days (configurable in dashboard) | Auto on SDK load |
| Supabase anonymous session | 1 hour | Auto-refresh via auth listener |
| `em_last_wallet_address` | Indefinite (until logout) | Set on each auth |

## Security Considerations

- `persistedWalletAddress` is NEVER used as an auth signal (line 103-104 in AuthContext)
- Only `dynamicWalletAddress` (from SDK) combined with `isLoggedIn` counts as authenticated
- If persisted wallet can't resolve to an executor, it's cleared and user must re-auth
- Logout clears all localStorage keys + Supabase session + Dynamic session

## Failure Modes

| Scenario | Behavior |
|----------|----------|
| Dynamic session expired | User sees "Start Earning" button, must reconnect |
| Supabase session expired | Auto-recreated via `ensureSupabaseSession()` |
| Executor record missing | Created via `get_or_create_executor` RPC |
| RPC fails | Fallback: direct `executors` table lookup by wallet |
| All fallbacks fail | User shown loading, then unauthenticated state |
