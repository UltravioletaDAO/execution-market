# IRC Trading Signal Protocol

> Protocol specification for publishing, tracking, and monetizing trading signals via MeshRelay IRC.
> Version: 1.0 | Created: 2026-02-22

---

## Overview

Trading signals are published in IRC channels and tracked by the Signal Bot.
Traders earn reputation via verified P&L, and top traders can monetize their
signals via premium Turnstile-gated channels.

```
Trader                    Signal Bot               Price API
  |                          |                        |
  | [SIGNAL] BUY ETH @3500  |                        |
  |------------------------->| Store signal           |
  |                          | Poll price every 60s   |
  | [SIGNAL-UPDATE] ...      |<-----------------------|
  |<-------------------------|                        |
  |                          |                        |
  | !ts leaderboard          |                        |
  |------------------------->|                        |
  | Top traders: ...         |                        |
  |<-------------------------|                        |
```

---

## Signal Message Formats

Signals can be published as **structured IRC messages** (human-friendly) or
via **bot commands** (programmatic). The bot recognizes both.

### Structured Signal (Freeform)

Traders post signals directly in the channel using the `[SIGNAL]` prefix:

```
[SIGNAL] BUY ETH/USDC @ 3500 | SL: 3400 | TP: 3700 | 85% | 4H
[SIGNAL] SELL AVAX/USDC @ 38.50 | SL: 40.00 | TP: 35.00 | 72% | 1D
[SIGNAL] BUY SOL/USDC @ 180 | SL: 170 | TP: 200 | 90% | 1W
```

**Format**: `[SIGNAL] <DIR> <PAIR> @ <ENTRY> | SL: <STOP> | TP: <TARGET> | <CONF>% | <TF>`

| Field | Required | Description | Examples |
|-------|----------|-------------|----------|
| DIR | Yes | Direction | `BUY`, `SELL` |
| PAIR | Yes | Trading pair | `ETH/USDC`, `BTC/USDT`, `AVAX/USDC` |
| ENTRY | Yes | Entry price | `3500`, `38.50` |
| SL | Yes | Stop loss price | `3400` |
| TP | Yes | Take profit price | `3700` |
| CONF | No | Confidence 1-100 (default: 50) | `85` |
| TF | No | Timeframe (default: `4H`) | `1H`, `4H`, `1D`, `1W` |

### Bot Command Signal

```
!ts signal BUY ETH/USDC @ 3500 | SL: 3400 | TP: 3700 | 85% | 4H
```

Identical format but uses the `!ts signal` command prefix.

### Signal Update (Auto-Generated)

The bot posts updates when TP or SL is hit:

```
[SIGNAL-UPDATE] ETH/USDC TP HIT @ 3700 | P&L: +5.7% | Duration: 6H | by @trader
[SIGNAL-UPDATE] AVAX/USDC SL HIT @ 40.00 | P&L: -3.9% | Duration: 2D | by @trader
```

### Signal Close (Manual)

Traders can manually close a signal before TP/SL:

```
!ts close <signal_id> [price]
```

Bot responds:
```
[SIGNAL-CLOSE] ETH/USDC closed @ 3600 | P&L: +2.9% | Duration: 3H | by @trader
```

### Signal Expiry (Auto)

Signals expire after their timeframe elapses without hitting TP or SL:

```
[SIGNAL-EXPIRED] ETH/USDC expired @ 3520 | P&L: +0.6% | Duration: 4H | by @trader
```

---

## Bot Commands

All commands use the `!ts` prefix (trading signals). Case-insensitive.

### Publishing Signals

```
!ts signal BUY ETH/USDC @ 3500 | SL: 3400 | TP: 3700 | 85% | 4H
```

### Viewing Signals

```
!ts open                    # List all open signals
!ts open @nick              # Open signals by a specific trader
!ts history [limit]         # Recent closed signals (default: 10)
!ts detail <signal_id>      # Full details of a signal
```

### Leaderboard & Stats

```
!ts leaderboard [period]    # Top traders (period: 7d, 30d, all; default: 30d)
!ts stats @nick             # Performance stats for a trader
!ts stats                   # Your own stats
```

### Management

```
!ts close <signal_id> [price]   # Manually close your signal
!ts cancel <signal_id>          # Cancel signal (no P&L recorded)
!ts help                        # Show commands
```

---

## Response Formats

### Open Signals

```
[SIGNALS] 3 open:
  1. s-a1b2c3 BUY ETH/USDC @ 3500 | TP: 3700 | SL: 3400 | 85% 4H | by @trader1
  2. s-d4e5f6 SELL AVAX/USDC @ 38.50 | TP: 35.00 | SL: 40.00 | 72% 1D | by @trader2
  3. s-g7h8i9 BUY SOL/USDC @ 180 | TP: 200 | SL: 170 | 90% 1W | by @trader1
```

### Leaderboard

```
[LEADERBOARD] Top 5 (30d):
  1. @trader1 | Win: 68% | Avg P&L: +3.2% | 45 signals | Total: +48.5%
  2. @trader2 | Win: 62% | Avg P&L: +2.1% | 31 signals | Total: +29.7%
  3. @trader3 | Win: 55% | Avg P&L: +1.5% | 22 signals | Total: +18.3%
```

### Trader Stats

```
[STATS] @trader1 (30d):
  Signals: 45 (38 closed, 3 open, 4 expired)
  Win Rate: 68% | Avg P&L: +3.2% | Best: +12.5% | Worst: -4.8%
  Total P&L: +48.5% | Sharpe: 1.85
  Streak: 5W (current) | Longest: 8W
```

---

## Signal Lifecycle

```
OPEN ──> TP HIT ──> CLOSED (win)
  |
  ├──> SL HIT ──> CLOSED (loss)
  |
  ├──> MANUAL CLOSE ──> CLOSED (P&L at close price)
  |
  ├──> CANCELLED ──> REMOVED (no P&L)
  |
  └──> EXPIRED ──> CLOSED (P&L at expiry price)
```

---

## Price Monitoring

The bot polls price APIs every 60 seconds for open signals.

### Price Sources (Priority Order)

1. **DexScreener** — `https://api.dexscreener.com/latest/dex/tokens/{address}`
   - Free, no API key, real-time DEX prices
   - Best for on-chain pairs (USDC, USDT denominated)

2. **CoinGecko** — `https://api.coingecko.com/api/v3/simple/price`
   - Free tier: 10-30 calls/min
   - Best for major assets (ETH, BTC, SOL)

### Pair Resolution

| Pair in Signal | Resolved To | Price Source |
|----------------|-------------|--------------|
| `ETH/USDC` | CoinGecko `ethereum` | USD price |
| `BTC/USDT` | CoinGecko `bitcoin` | USD price |
| `SOL/USDC` | CoinGecko `solana` | USD price |
| `AVAX/USDC` | CoinGecko `avalanche-2` | USD price |
| Custom token | DexScreener by address | DEX price |

### P&L Calculation

For BUY signals:
```
P&L% = ((current_price - entry_price) / entry_price) * 100
```

For SELL signals:
```
P&L% = ((entry_price - current_price) / entry_price) * 100
```

---

## Storage

Signals are stored as JSON files in `scripts/kk/data/trading_signals/`:

```
trading_signals/
  signals.json           # Active + recently closed signals
  leaderboard.json       # Cached leaderboard stats
  archive/
    2026-02-22.json      # Daily archive of closed signals
```

### Signal Schema

```json
{
  "id": "s-a1b2c3d4",
  "author": "trader1",
  "direction": "BUY",
  "pair": "ETH/USDC",
  "entry_price": 3500.0,
  "stop_loss": 3400.0,
  "take_profit": 3700.0,
  "confidence": 85,
  "timeframe": "4H",
  "status": "open",
  "created_at": "2026-02-22T15:30:00Z",
  "closed_at": null,
  "close_price": null,
  "pnl_percent": null,
  "close_reason": null
}
```

---

## Rate Limiting

| Resource | Limit | Window |
|----------|-------|--------|
| Signal publish per nick | 5 | 1 hour |
| Commands per nick | 10 | 1 minute |
| Global signals | 30 | 1 hour |

---

## Channels

| Channel | Purpose |
|---------|---------|
| `#kk-alpha` | Premium signal channel ($1.00 USDC/hr via Turnstile) |
| `#Agents` | General signals and leaderboard queries |

---

## Future: Copy Trading (Task 3.3)

Phase 2 adds subscription-based copy trading:

```
!ts subscribe @trader1 daily     # $0.50/day — DM signals
!ts subscribe @trader1 weekly    # $2.00/week
!ts subscribe @trader1 monthly   # $5.00/month
!ts unsubscribe @trader1
```

Revenue split: 70% trader / 20% MeshRelay / 10% Execution Market treasury.
Payment via x402 Turnstile subscription model.
