"""
Lambda function to fetch USDC balances for any wallet across EM's 9 EVM chains.

Public-facing service called from the dashboard wallet panel. Accepts:
    GET /?wallet=0x<40-hex>

Returns per-chain USDC balance (raw uint256 hex + formatted human-readable).

Why this Lambda exists:
- Frontend was hitting public RPCs directly via viem `http()`, getting rate-limited
  on every render — every chain showed "RPC error" in the UI.
- Putting RPCs in the browser also leaks any private RPC URL we'd embed.
- This Lambda holds the private QuikNode RPC URLs (Secrets Manager) and exposes
  ONLY balances over a Function URL with CORS for execution.market.

Adapted from the x402-rs facilitator balance Lambda (Z:/ultravioleta/dao/x402-rs/lambda/balances/handler.py).
Differences:
- Accepts arbitrary wallet (not hardcoded facilitator address).
- Calls USDC `balanceOf(address)` via `eth_call` (not native `eth_getBalance`).
- Limited to EM's 9 EVM mainnet chains (matches dashboard/src/config/networks.ts).
- Per-wallet cache key.
- Reuses the `facilitator-rpc-mainnet` secret (same RPCs).
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
import urllib.error
import urllib.request

import boto3
from botocore.exceptions import ClientError

CACHE_TTL_SECONDS = 60
_cache: dict[str, dict[str, Any]] = {}  # keyed by lowercase wallet address
_cache_timestamp: dict[str, float] = {}
_secrets_cache: dict[str, str] = {}

MAINNET_SECRET_NAME = "facilitator-rpc-mainnet"

WALLET_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
USDC_DECIMALS = 6
# ERC-20 selector for `balanceOf(address)` — keccak256("balanceOf(address)")[:4]
BALANCE_OF_SELECTOR = "0x70a08231"

# EM's 9 EVM mainnet chains. USDC addresses must match dashboard/src/hooks/useOnchainBalance.ts
# and mcp_server/integrations/x402/sdk_client.py NETWORK_CONFIG.
# `secret_key = None` means we don't have a private RPC for that chain — the public RPC
# is the only option (fine for SKALE because it has zero gas fees and no rate limits).
NETWORKS: dict[str, dict[str, str | None]] = {
    "base": {
        "secret_key": "base",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "public_rpc": "https://mainnet.base.org",
    },
    "ethereum": {
        "secret_key": "ethereum",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "public_rpc": "https://ethereum-rpc.publicnode.com",
    },
    "polygon": {
        "secret_key": "polygon",
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "public_rpc": "https://polygon.drpc.org",
    },
    "arbitrum": {
        "secret_key": "arbitrum",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "public_rpc": "https://arb1.arbitrum.io/rpc",
    },
    "optimism": {
        "secret_key": "optimism",
        "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "public_rpc": "https://mainnet.optimism.io",
    },
    "avalanche": {
        "secret_key": "avalanche",
        "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "public_rpc": "https://avalanche-c-chain-rpc.publicnode.com",
    },
    "celo": {
        "secret_key": "celo",
        "usdc": "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
        "public_rpc": "https://rpc.celocolombia.org",
    },
    "monad": {
        "secret_key": "monad",
        "usdc": "0x754704Bc059F8C67012fEd69BC8A327a5aafb603",
        "public_rpc": "https://rpc.monad.xyz",
    },
    # SKALE has no private RPC in the secret — public RPC is fine because the chain
    # has zero gas fees and no rate limits on `eth_call`.
    "skale": {
        "secret_key": None,
        "usdc": "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20",
        "public_rpc": "https://skale-base.skalenodes.com/v1/base",
    },
}


def get_secret(secret_name: str, key: str | None = None) -> str | None:
    """Read a secret from AWS Secrets Manager. Cached per cold start."""
    cache_key = f"{secret_name}:{key}" if key else secret_name
    if cache_key in _secrets_cache:
        return _secrets_cache[cache_key]
    try:
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response.get("SecretString", "")
        if key:
            value = json.loads(secret_string).get(key)
        else:
            value = secret_string
        if value:
            _secrets_cache[cache_key] = value
        return value
    except ClientError as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing secret JSON {secret_name}: {e}")
        return None


def get_rpc_urls(network_key: str) -> list[str]:
    """Build ordered RPC list: private (Secrets Manager) → env var → public.

    `secret_key = None` means we don't have a private RPC for this chain — skip
    the Secrets Manager lookup so we don't accidentally read the whole secret.
    """
    cfg = NETWORKS[network_key]
    private = get_secret(MAINNET_SECRET_NAME, cfg["secret_key"]) if cfg["secret_key"] else None
    env = os.environ.get(f"RPC_URL_{network_key.upper()}")
    return [u for u in [private, env, cfg["public_rpc"]] if u]


def encode_balance_of(wallet: str) -> str:
    """Build calldata for ERC-20 balanceOf(address). Address is left-padded to 32 bytes."""
    return BALANCE_OF_SELECTOR + wallet.lower().replace("0x", "").rjust(64, "0")


def fetch_json(url: str, data: bytes | None = None, timeout: float = 8) -> dict:
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def fetch_usdc_balance(network_key: str, wallet: str) -> tuple[str, dict[str, Any]]:
    """
    Call USDC.balanceOf(wallet) on `network_key`. Returns (network_key, result_dict).
    result_dict shape:
      {"raw": "<hex>", "balance": <float>, "error": null}  on success
      {"raw": null, "balance": 0, "error": "<msg>"}        on failure
    """
    cfg = NETWORKS[network_key]
    rpcs = get_rpc_urls(network_key)
    calldata = encode_balance_of(wallet)

    last_error = "no rpc available"
    for rpc_url in rpcs:
        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [
                    {"to": cfg["usdc"], "data": calldata},
                    "latest",
                ],
                "id": 1,
            }).encode()
            data = fetch_json(rpc_url, payload, timeout=8)
            if "error" in data:
                last_error = str(data["error"].get("message", data["error"]))
                continue
            if "result" not in data:
                last_error = "no result field"
                continue
            raw_hex = data["result"]
            raw_int = int(raw_hex, 16)
            balance = raw_int / (10 ** USDC_DECIMALS)
            return network_key, {
                "raw": raw_hex,
                "balance": balance,
                "error": None,
            }
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}"
            continue
        except urllib.error.URLError as e:
            last_error = f"URL error: {e.reason}"
            continue
        except (ValueError, KeyError) as e:
            last_error = f"decode error: {e}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    return network_key, {"raw": None, "balance": 0, "error": last_error}


def fetch_all_balances(wallet: str) -> dict[str, dict[str, Any]]:
    """Fetch USDC balance across all 9 chains concurrently. Cached per wallet."""
    wallet_key = wallet.lower()
    now = time.time()
    cached_at = _cache_timestamp.get(wallet_key, 0)
    if wallet_key in _cache and (now - cached_at) < CACHE_TTL_SECONDS:
        return _cache[wallet_key]

    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(NETWORKS)) as executor:
        futures = [executor.submit(fetch_usdc_balance, k, wallet) for k in NETWORKS]
        for future in as_completed(futures):
            network_key, result = future.result()
            results[network_key] = result

    _cache[wallet_key] = results
    _cache_timestamp[wallet_key] = now
    return results


def response_headers() -> dict[str, str]:
    """Business headers only.

    CORS is handled by the Lambda Function URL (see em_balances.tf `cors` block).
    Returning ACAO from here would duplicate the header — browsers reject responses
    with multiple Access-Control-Allow-Origin headers with "Failed to fetch".
    """
    return {
        "Content-Type": "application/json",
        "Cache-Control": "public, max-age=60",
    }


def lambda_handler(event: dict, _context: Any) -> dict:
    """
    Lambda Function URL handler.

    Input:
      event["queryStringParameters"]["wallet"] — required, EVM address (0x + 40 hex)

    Output (200):
      {
        "wallet": "0x...",
        "balances": {
          "base":      {"raw": "0x..", "balance": 12.34, "error": null},
          "ethereum":  {"raw": null,    "balance": 0,     "error": "RPC timeout"},
          ...
        },
        "total_usdc": 12.34,
        "cached_at": <epoch>,
        "ttl_seconds": 60
      }

    OPTIONS preflight is handled by the Function URL — this Lambda is never invoked
    for OPTIONS, so we don't need a branch for it.
    """

    qs = event.get("queryStringParameters") or {}
    wallet = (qs.get("wallet") or "").strip()

    if not wallet:
        return {
            "statusCode": 400,
            "headers": response_headers(),
            "body": json.dumps({"error": "missing 'wallet' query parameter"}),
        }
    if not WALLET_RE.match(wallet):
        return {
            "statusCode": 400,
            "headers": response_headers(),
            "body": json.dumps({"error": "invalid wallet address — expected 0x + 40 hex chars"}),
        }

    try:
        balances = fetch_all_balances(wallet)
        total = sum(b["balance"] for b in balances.values() if b.get("error") is None)
        body = {
            "wallet": wallet.lower(),
            "balances": balances,
            "total_usdc": total,
            "cached_at": int(_cache_timestamp.get(wallet.lower(), time.time())),
            "ttl_seconds": CACHE_TTL_SECONDS,
        }
        return {"statusCode": 200, "headers": response_headers(), "body": json.dumps(body)}
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {
            "statusCode": 500,
            "headers": response_headers(),
            "body": json.dumps({"error": str(e)}),
        }
