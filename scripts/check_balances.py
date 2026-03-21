#!/usr/bin/env python3
"""Check ERC-20 balances for a wallet across 17 token pairs using urllib only."""

import json
import urllib.request
import urllib.error

WALLET = "YOUR_PLATFORM_WALLET"
SELECTOR = "0x70a08231"
DECIMALS = 6

# Pad wallet address to 32 bytes (remove 0x, left-pad to 64 hex chars)
PADDED_WALLET = WALLET[2:].lower().zfill(64)
CALL_DATA = SELECTOR + PADDED_WALLET

PAIRS = [
    (
        "Base",
        "USDC",
        ["https://mainnet.base.org", "https://base-rpc.publicnode.com"],
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    ),
    (
        "Base",
        "EURC",
        ["https://mainnet.base.org", "https://base-rpc.publicnode.com"],
        "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
    ),
    (
        "Ethereum",
        "USDC",
        ["https://1rpc.io/eth", "https://ethereum-rpc.publicnode.com"],
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    ),
    (
        "Ethereum",
        "EURC",
        ["https://1rpc.io/eth", "https://ethereum-rpc.publicnode.com"],
        "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c",
    ),
    (
        "Ethereum",
        "PYUSD",
        ["https://1rpc.io/eth", "https://ethereum-rpc.publicnode.com"],
        "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8",
    ),
    (
        "Ethereum",
        "AUSD",
        ["https://1rpc.io/eth", "https://ethereum-rpc.publicnode.com"],
        "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a",
    ),
    (
        "Polygon",
        "USDC",
        ["https://polygon-rpc.com"],
        "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    ),
    (
        "Polygon",
        "AUSD",
        ["https://polygon-rpc.com"],
        "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a",
    ),
    (
        "Arbitrum",
        "USDC",
        ["https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com"],
        "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    ),
    (
        "Arbitrum",
        "USDT0",
        ["https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com"],
        "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    ),
    (
        "Celo",
        "USDC",
        ["https://forno.celo.org"],
        "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
    ),
    (
        "Celo",
        "USDT0",
        ["https://forno.celo.org"],
        "0x48065fbBE25f71C9282ddf5e1cD6D6A887483D5e",
    ),
    (
        "Monad",
        "USDC",
        ["https://rpc.monad.xyz"],
        "0x754704Bc059F8C67012fEd69BC8A327a5aafb603",
    ),
    (
        "Monad",
        "AUSD",
        ["https://rpc.monad.xyz"],
        "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a",
    ),
    (
        "Avalanche",
        "USDC",
        ["https://api.avax.network/ext/bc/C/rpc"],
        "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
    ),
    (
        "Avalanche",
        "EURC",
        ["https://api.avax.network/ext/bc/C/rpc"],
        "0xC891EB4cbdEFf6e073e859e987815Ed1505c2ACD",
    ),
    (
        "Avalanche",
        "AUSD",
        ["https://api.avax.network/ext/bc/C/rpc"],
        "0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a",
    ),
]


def eth_call(rpc_url, token):
    """Make an eth_call to get balanceOf, returns hex result string."""
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": token, "data": CALL_DATA}, "latest"],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ExecutionMarket-BalanceChecker/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "error" in body:
        raise RuntimeError(body["error"].get("message", str(body["error"])))
    return body["result"]


def get_balance(rpcs, token):
    """Try each RPC in order; return balance as float with 6-decimal conversion."""
    last_err = None
    for rpc in rpcs:
        try:
            hex_result = eth_call(rpc, token)
            raw = int(hex_result, 16)
            return raw / (10**DECIMALS)
        except Exception as exc:
            last_err = exc
            continue
    raise RuntimeError("All RPCs failed. Last error: {}".format(last_err))


def main():
    print("Wallet: {}".format(WALLET))
    print("{:<4} {:<12} {:<7} {:>12}".format("#", "Chain", "Token", "Balance"))
    print("-" * 38)

    total = 0.0
    for i, (chain, token_name, rpcs, token_addr) in enumerate(PAIRS, 1):
        try:
            bal = get_balance(rpcs, token_addr)
            total += bal
            print("{:<4} {:<12} {:<7} ${:>10.2f}".format(i, chain, token_name, bal))
        except Exception as exc:
            print(
                "{:<4} {:<12} {:<7} {:>11}  ({})".format(
                    i, chain, token_name, "ERROR", exc
                )
            )

    print("-" * 38)
    print("{:.<23} TOTAL  ${:>10.2f}".format("", total))


if __name__ == "__main__":
    main()
