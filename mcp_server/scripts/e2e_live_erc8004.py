#!/usr/bin/env python
"""
Live E2E test: Execute REAL ERC-8004 transactions via the Ultravioleta Facilitator.

Produces on-chain tx hashes on Base Mainnet verifiable on BaseScan.
"""

import os
import sys
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
for env_path in [
    os.path.join(os.path.dirname(__file__), "..", "..", ".env.local"),
    os.path.join(os.path.dirname(__file__), "..", ".env"),
]:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

os.environ["EM_AGENT_ID"] = "2106"
os.environ["ERC8004_NETWORK"] = "base"

import httpx

FACILITATOR = "https://facilitator.ultravioletadao.xyz"
DEV_WALLET = "YOUR_DEV_WALLET"


def format_tx_hash(tx_data):
    """Extract tx hash from facilitator response."""
    if isinstance(tx_data, str):
        return tx_data
    if isinstance(tx_data, dict) and "Evm" in tx_data:
        evm = tx_data["Evm"]
        if isinstance(evm, list):
            return "0x" + "".join(f"{b:02x}" for b in evm)
        return evm
    return str(tx_data)


async def main():
    results = {}

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0, connect=15.0),
        headers={"Content-Type": "application/json"},
    ) as client:
        # ==== TX 1: Agent rates worker (score=78) ====
        print("=" * 60)
        print("TX 1: Agent #2106 rates Agent #1 (worker_rating, score=78)")
        print("  Simulates: agent rates worker after task completion")
        print("=" * 60)

        resp = await client.post(
            f"{FACILITATOR}/feedback",
            json={
                "x402Version": 1,
                "network": "base",
                "feedback": {
                    "agentId": 1,
                    "value": 78,
                    "valueDecimals": 0,
                    "tag1": "worker_rating",
                    "tag2": "e2e_2026-02-11",
                    "endpoint": "task:e2e-happy-path-001",
                    "feedbackUri": "https://execution.market/feedback/e2e-happy-path-001",
                },
            },
        )
        data = resp.json()
        print(f"  HTTP: {resp.status_code}, Success: {data.get('success')}")
        if data.get("transaction"):
            h = format_tx_hash(data["transaction"])
            print(f"  TX Hash: {h}")
            print(f"  BaseScan: https://basescan.org/tx/{h}")
            data["tx_hash_formatted"] = h
        if data.get("feedbackIndex") is not None:
            print(f"  Feedback Index: {data['feedbackIndex']}")
        if data.get("error"):
            print(f"  Error: {data['error']}")
        results["tx1_rate_worker"] = data
        print()

        await asyncio.sleep(3)

        # ==== TX 2: Worker auto-rates agent (score=85) ====
        print("=" * 60)
        print("TX 2: Rate Agent #2 (agent_rating, score=85)")
        print("  Simulates: WS-2 worker auto-rates agent after payment")
        print("=" * 60)

        resp = await client.post(
            f"{FACILITATOR}/feedback",
            json={
                "x402Version": 1,
                "network": "base",
                "feedback": {
                    "agentId": 2,
                    "value": 85,
                    "valueDecimals": 0,
                    "tag1": "agent_rating",
                    "tag2": "execution-market",
                    "endpoint": "task:e2e-happy-path-001",
                    "feedbackUri": "",
                },
            },
        )
        data = resp.json()
        print(f"  HTTP: {resp.status_code}, Success: {data.get('success')}")
        if data.get("transaction"):
            h = format_tx_hash(data["transaction"])
            print(f"  TX Hash: {h}")
            print(f"  BaseScan: https://basescan.org/tx/{h}")
            data["tx_hash_formatted"] = h
        if data.get("feedbackIndex") is not None:
            print(f"  Feedback Index: {data['feedbackIndex']}")
        if data.get("error"):
            print(f"  Error: {data['error']}")
        results["tx2_rate_agent"] = data
        print()

        await asyncio.sleep(3)

        # ==== TX 3: Major rejection penalty (score=30) ====
        print("=" * 60)
        print("TX 3: Rejection feedback on Agent #3 (score=30)")
        print("  Simulates: WS-3 major rejection penalty")
        print("=" * 60)

        resp = await client.post(
            f"{FACILITATOR}/feedback",
            json={
                "x402Version": 1,
                "network": "base",
                "feedback": {
                    "agentId": 3,
                    "value": 30,
                    "valueDecimals": 0,
                    "tag1": "worker_rating",
                    "tag2": "rejection_major",
                    "endpoint": "task:e2e-rejection-001",
                    "feedbackUri": "https://execution.market/feedback/e2e-rejection-001",
                },
            },
        )
        data = resp.json()
        print(f"  HTTP: {resp.status_code}, Success: {data.get('success')}")
        if data.get("transaction"):
            h = format_tx_hash(data["transaction"])
            print(f"  TX Hash: {h}")
            print(f"  BaseScan: https://basescan.org/tx/{h}")
            data["tx_hash_formatted"] = h
        if data.get("feedbackIndex") is not None:
            print(f"  Feedback Index: {data['feedbackIndex']}")
        if data.get("error"):
            print(f"  Error: {data['error']}")
        results["tx3_rejection"] = data
        print()

        await asyncio.sleep(3)

        # ==== TX 4: Gasless worker registration ====
        print("=" * 60)
        print(f"TX 4: Gasless registration for {DEV_WALLET[:10]}...")
        print("  Simulates: WS-1 auto-register worker after first completion")
        print("=" * 60)

        resp = await client.post(
            f"{FACILITATOR}/register",
            json={
                "x402Version": 1,
                "network": "base",
                "agentUri": f"https://execution.market/workers/{DEV_WALLET.lower()}",
                "recipient": DEV_WALLET,
            },
        )
        data = resp.json()
        print(f"  HTTP: {resp.status_code}, Success: {data.get('success')}")
        if data.get("agentId"):
            print(f"  New Agent ID: {data['agentId']}")
        if data.get("transaction"):
            h = format_tx_hash(data["transaction"])
            print(f"  Reg TX: {h}")
            print(f"  BaseScan: https://basescan.org/tx/{h}")
            data["tx_hash_formatted"] = h
        if data.get("transferTransaction"):
            h2 = format_tx_hash(data["transferTransaction"])
            print(f"  Transfer TX: {h2}")
            print(f"  BaseScan: https://basescan.org/tx/{h2}")
            data["transfer_tx_formatted"] = h2
        if data.get("error"):
            print(f"  Error: {data['error']}")
        results["tx4_register"] = data
        print()

        # ==== VERIFY: Check reputation ====
        print("=" * 60)
        print("VERIFY: Reputation after all transactions")
        print("=" * 60)

        for aid in [1, 2, 3, 2106]:
            try:
                resp = await client.get(f"{FACILITATOR}/reputation/base/{aid}")
                rep = resp.json()
                s = rep.get("summary", {})
                print(
                    f"  Agent #{aid}: count={s.get('count', 0)}, "
                    f"summaryValue={s.get('summaryValue', 0)}"
                )
                results[f"reputation_{aid}"] = rep
            except Exception as e:
                print(f"  Agent #{aid}: error {e}")

    # Save full results
    out_path = os.path.join(os.path.dirname(__file__), "..", "e2e_tx_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
