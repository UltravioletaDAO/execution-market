#!/usr/bin/env python3
"""
Bulk ERC-8004 Identity Registration across all mainnet networks.

Registers a wallet on all 9 mainnet ERC-8004 Identity Registries via the
Execution Market API (which uses the Facilitator for gasless registration).

Usage:
    python scripts/bulk_register_erc8004.py --wallet 0x1234... [--networks base,polygon,ethereum]
    python scripts/bulk_register_erc8004.py --wallet 0x1234... --all-mainnets
    python scripts/bulk_register_erc8004.py --wallet 0x1234... --metadata-uri https://example.com/agent-card.json

All registrations are gasless (Facilitator pays gas).
"""

import argparse
import asyncio
import sys
import time

import httpx

API_BASE = "https://api.execution.market"

# All 9 mainnet networks supported by ERC-8004 via Facilitator
ALL_MAINNETS = [
    "base",
    "ethereum",
    "polygon",
    "arbitrum",
    "celo",
    "bsc",
    "monad",
    "avalanche",
    "optimism",
]


async def check_identity(
    client: httpx.AsyncClient, wallet: str, network: str
) -> dict:
    """Check if wallet is already registered on a network."""
    url = f"{API_BASE}/api/v1/reputation/identity/{wallet}"
    resp = await client.get(url, params={"network": network})
    if resp.status_code == 200:
        return resp.json()
    return {"registered": False, "agent_id": None}


async def register_identity(
    client: httpx.AsyncClient,
    wallet: str,
    network: str,
    metadata_uri: str | None = None,
) -> dict:
    """Register wallet on a single network. Returns result dict."""
    payload: dict = {"wallet_address": wallet, "network": network}
    if metadata_uri:
        payload["metadata_uri"] = metadata_uri

    url = f"{API_BASE}/api/v1/reputation/register"
    resp = await client.post(url, json=payload)

    if resp.status_code == 409:
        return {"network": network, "status": "already_registered", "detail": resp.text}
    if resp.status_code != 200:
        return {
            "network": network,
            "status": "error",
            "code": resp.status_code,
            "detail": resp.text,
        }

    data = resp.json()
    return {
        "network": network,
        "status": "registered",
        "agent_id": data.get("agent_id"),
        "tx_hash": data.get("transaction_hash"),
    }


async def register_on_network(
    client: httpx.AsyncClient,
    wallet: str,
    network: str,
    metadata_uri: str | None = None,
    skip_existing: bool = True,
) -> dict:
    """Check + register on a single network."""
    if skip_existing:
        check = await check_identity(client, wallet, network)
        if check.get("registered"):
            return {
                "network": network,
                "status": "already_registered",
                "agent_id": check.get("agent_id"),
            }

    return await register_identity(client, wallet, network, metadata_uri)


async def bulk_register(
    wallet: str,
    networks: list[str],
    metadata_uri: str | None = None,
    concurrency: int = 3,
) -> list[dict]:
    """Register wallet on multiple networks with concurrency limit."""
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict] = []

    async def register_with_limit(network: str) -> dict:
        async with semaphore:
            async with httpx.AsyncClient(timeout=60.0) as client:
                return await register_on_network(
                    client, wallet, network, metadata_uri
                )

    tasks = [register_with_limit(n) for n in networks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            final.append({
                "network": networks[i],
                "status": "error",
                "detail": str(r),
            })
        else:
            final.append(r)
    return final


def print_results(results: list[dict], elapsed: float) -> None:
    """Print registration results table."""
    print("\n" + "=" * 70)
    print(f"{'Network':<12} {'Status':<20} {'Agent ID':<10} {'TX Hash'}")
    print("-" * 70)

    registered = 0
    already = 0
    errors = 0

    for r in results:
        network = r.get("network", "?")
        status = r.get("status", "?")
        agent_id = r.get("agent_id", "")
        tx_hash = r.get("tx_hash", "")

        if status == "registered":
            registered += 1
            symbol = "[OK]"
        elif status == "already_registered":
            already += 1
            symbol = "[--]"
        else:
            errors += 1
            symbol = "[!!]"
            tx_hash = r.get("detail", "")[:40]

        agent_str = str(agent_id) if agent_id else ""
        tx_str = tx_hash[:20] + "..." if len(str(tx_hash)) > 20 else str(tx_hash)
        print(f"{symbol} {network:<9} {status:<20} {agent_str:<10} {tx_str}")

    print("-" * 70)
    print(
        f"Total: {len(results)} networks | "
        f"New: {registered} | Already: {already} | Errors: {errors} | "
        f"Time: {elapsed:.1f}s"
    )
    print("=" * 70)


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bulk ERC-8004 Identity Registration"
    )
    parser.add_argument(
        "--wallet", required=True, help="Wallet address (0x...)"
    )
    parser.add_argument(
        "--networks",
        help="Comma-separated list of networks (default: all mainnets)",
    )
    parser.add_argument(
        "--all-mainnets",
        action="store_true",
        help="Register on all 9 mainnet networks",
    )
    parser.add_argument(
        "--metadata-uri",
        help="URL to agent-card.json metadata",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Max concurrent registrations (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only check existing registrations, don't register",
    )

    args = parser.parse_args()

    wallet = args.wallet
    if not wallet.startswith("0x") or len(wallet) != 42:
        print(f"Error: Invalid wallet address: {wallet}")
        return 1

    if args.networks:
        networks = [n.strip() for n in args.networks.split(",")]
    elif args.all_mainnets:
        networks = ALL_MAINNETS
    else:
        networks = ALL_MAINNETS

    print(f"Wallet: {wallet}")
    print(f"Networks: {', '.join(networks)}")
    print(f"Metadata URI: {args.metadata_uri or '(none)'}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'REGISTER'}")
    print()

    if args.dry_run:
        async with httpx.AsyncClient(timeout=30.0) as client:
            results = []
            for network in networks:
                check = await check_identity(client, wallet, network)
                results.append({
                    "network": network,
                    "status": "already_registered"
                    if check.get("registered")
                    else "not_registered",
                    "agent_id": check.get("agent_id"),
                })
        print_results(results, 0.0)
        return 0

    start = time.monotonic()
    results = await bulk_register(
        wallet=wallet,
        networks=networks,
        metadata_uri=args.metadata_uri,
        concurrency=args.concurrency,
    )
    elapsed = time.monotonic() - start

    print_results(results, elapsed)

    errors = sum(1 for r in results if r.get("status") == "error")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
