"""
Query Supabase for all on-chain transaction hashes from multichain Golden Flow tests.
Groups results by network/chain.

Tables:
- payment_events (migration 027): tx_hash, network, event_type, amount_usdc, status
- escrows (migration 002 + 015): funding_tx, deposit_tx, release_tx, refund_tx, metadata (may contain network)
"""

import os
import httpx
from dotenv import load_dotenv

# Load env from mcp_server/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "mcp_server", ".env"))

SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

BASE_URL = f"{SUPABASE_URL}/rest/v1"


def query_payment_events(client: httpx.Client) -> list[dict]:
    """Query payment_events table for all rows with tx_hash."""
    url = (
        f"{BASE_URL}/payment_events"
        "?select=network,event_type,tx_hash,amount_usdc,status,task_id,from_address,to_address,token,metadata,created_at"
        "&tx_hash=not.is.null"
        "&order=created_at.desc"
        "&limit=100"
    )
    resp = client.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def query_all_payment_events(client: httpx.Client) -> list[dict]:
    """Query ALL payment_events (including those without tx_hash) for visibility."""
    url = (
        f"{BASE_URL}/payment_events"
        "?select=network,event_type,tx_hash,amount_usdc,status,task_id,error,created_at"
        "&order=created_at.desc"
        "&limit=200"
    )
    resp = client.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def query_escrows(client: httpx.Client) -> list[dict]:
    """Query escrows table. Uses correct column names from migration 002+015."""
    url = (
        f"{BASE_URL}/escrows"
        "?select=task_id,escrow_id,status,funding_tx,deposit_tx,release_tx,refund_tx,amount_usdc,total_amount_usdc,metadata,created_at"
        "&order=created_at.desc"
        "&limit=100"
    )
    resp = client.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def query_tasks_with_network(client: httpx.Client) -> dict[str, str]:
    """Query tasks table to get payment_network for each task_id."""
    url = (
        f"{BASE_URL}/tasks"
        "?select=id,payment_network,status"
        "&limit=500"
    )
    resp = client.get(url, headers=HEADERS)
    resp.raise_for_status()
    rows = resp.json()
    return {r["id"]: r.get("payment_network") or "base" for r in rows}


def print_payment_events(events: list[dict]) -> None:
    """Print payment events with tx_hash grouped by chain."""
    if not events:
        print("\n=== PAYMENT EVENTS WITH TX HASH: No records found ===")
        return

    # Group by network
    by_chain: dict[str, list[dict]] = {}
    for e in events:
        chain = e.get("network") or "unknown"
        by_chain.setdefault(chain, []).append(e)

    print("\n" + "=" * 140)
    print("PAYMENT EVENTS WITH ON-CHAIN TX HASHES (grouped by chain)")
    print("=" * 140)

    header = f"{'Chain':<14} | {'Event Type':<20} | {'TX Hash':<68} | {'Amount':<10} | {'Status':<10} | {'Created':<20}"
    print(header)
    print("-" * 140)

    for chain in sorted(by_chain.keys()):
        rows = by_chain[chain]
        for r in rows:
            tx = r.get("tx_hash") or ""
            amt = r.get("amount_usdc")
            amt_str = f"${amt}" if amt is not None else "-"
            created = str(r.get("created_at", ""))[:19]
            print(
                f"{chain:<14} | {r.get('event_type', '-'):<20} | {tx:<68} | {amt_str:<10} | {r.get('status', '-'):<10} | {created:<20}"
            )
        print("-" * 140)

    print(f"\nTotal payment events with tx_hash: {len(events)}")
    print(f"Chains: {', '.join(sorted(by_chain.keys()))}")


def print_all_events_summary(events: list[dict]) -> None:
    """Print summary of ALL payment events (including failed/no-tx)."""
    if not events:
        print("\n=== ALL PAYMENT EVENTS: No records found ===")
        return

    print("\n" + "=" * 100)
    print("ALL PAYMENT EVENTS SUMMARY (including failed/pending)")
    print("=" * 100)

    # Group by network and status
    by_chain_status: dict[str, dict[str, int]] = {}
    by_chain_type: dict[str, dict[str, int]] = {}
    for e in events:
        chain = e.get("network") or "unknown"
        status = e.get("status") or "unknown"
        etype = e.get("event_type") or "unknown"
        by_chain_status.setdefault(chain, {})
        by_chain_status[chain][status] = by_chain_status[chain].get(status, 0) + 1
        by_chain_type.setdefault(chain, {})
        by_chain_type[chain][etype] = by_chain_type[chain].get(etype, 0) + 1

    for chain in sorted(by_chain_status.keys()):
        statuses = by_chain_status[chain]
        types = by_chain_type[chain]
        total = sum(statuses.values())
        status_str = ", ".join(f"{k}={v}" for k, v in sorted(statuses.items()))
        type_str = ", ".join(f"{k}={v}" for k, v in sorted(types.items()))
        print(f"\n  {chain} ({total} events):")
        print(f"    By status: {status_str}")
        print(f"    By type:   {type_str}")

    print(f"\n  Total events across all chains: {len(events)}")


def print_escrows(escrows: list[dict], task_network_map: dict[str, str]) -> None:
    """Print escrow records with tx hashes."""
    if not escrows:
        print("\n=== ESCROWS: No records found ===")
        return

    # Determine network from task_id or metadata
    def get_network(esc: dict) -> str:
        # Try metadata first
        meta = esc.get("metadata") or {}
        if isinstance(meta, dict):
            net = meta.get("network") or meta.get("payment_network")
            if net:
                return net
        # Fall back to task's payment_network
        tid = esc.get("task_id")
        if tid and tid in task_network_map:
            return task_network_map[tid]
        return "base"  # default

    by_chain: dict[str, list[dict]] = {}
    for e in escrows:
        chain = get_network(e)
        by_chain.setdefault(chain, []).append(e)

    print("\n" + "=" * 150)
    print("ESCROW RECORDS WITH TX HASHES (grouped by chain)")
    print("=" * 150)

    header = f"{'Chain':<14} | {'TX Type':<14} | {'TX Hash':<68} | {'Amount':<12} | {'Status':<14} | {'Created':<20}"
    print(header)
    print("-" * 150)

    total_tx = 0
    for chain in sorted(by_chain.keys()):
        rows = by_chain[chain]
        for r in rows:
            amt = r.get("total_amount_usdc") or r.get("amount_usdc")
            amt_str = f"${amt}" if amt is not None else "-"
            created = str(r.get("created_at", ""))[:19]
            status = r.get("status") or "-"

            has_any_tx = False

            for field, label in [
                ("funding_tx", "escrow_fund"),
                ("deposit_tx", "deposit"),
                ("release_tx", "release"),
                ("refund_tx", "refund"),
            ]:
                tx = r.get(field)
                if tx:
                    has_any_tx = True
                    total_tx += 1
                    print(
                        f"{chain:<14} | {label:<14} | {tx:<68} | {amt_str:<12} | {status:<14} | {created:<20}"
                    )

            # Also check metadata for tx hashes
            meta = r.get("metadata") or {}
            if isinstance(meta, dict):
                for key in sorted(meta.keys()):
                    val = meta[key]
                    if isinstance(val, str) and val.startswith("0x") and len(val) == 66:
                        has_any_tx = True
                        total_tx += 1
                        print(
                            f"{chain:<14} | {'meta:' + key[:9]:<14} | {val:<68} | {amt_str:<12} | {status:<14} | {created:<20}"
                        )

            if not has_any_tx:
                print(
                    f"{chain:<14} | {'(no tx)':<14} | {'-':<68} | {amt_str:<12} | {status:<14} | {created:<20}"
                )

        print("-" * 150)

    print(f"\nTotal escrow records: {len(escrows)}")
    print(f"Total TX hashes found: {total_tx}")
    print(f"Chains: {', '.join(sorted(by_chain.keys()))}")


def main():
    print("=" * 80)
    print("MULTICHAIN TX HASH QUERY — Execution Market")
    print("=" * 80)
    print(f"Supabase: {SUPABASE_URL}")
    print(f"Service key: {'set' if SERVICE_KEY else 'NOT SET'}")

    with httpx.Client(timeout=30) as client:
        # 1. Get task-to-network mapping
        print("\nFetching task network mappings...")
        task_networks = query_tasks_with_network(client)
        print(f"  Found {len(task_networks)} tasks with payment_network set")

        # 2. Payment events with tx_hash
        print("Fetching payment events with TX hashes...")
        events_with_tx = query_payment_events(client)
        print(f"  Found {len(events_with_tx)} payment events with tx_hash")

        # 3. All payment events
        print("Fetching all payment events...")
        all_events = query_all_payment_events(client)
        print(f"  Found {len(all_events)} total payment events")

        # 4. Escrows
        print("Fetching escrow records...")
        escrows = query_escrows(client)
        print(f"  Found {len(escrows)} escrow records")

    # Print detailed results
    print_payment_events(events_with_tx)
    print_all_events_summary(all_events)
    print_escrows(escrows, task_networks)

    # Final combined summary
    all_chains = set()
    all_tx_hashes = set()

    for e in events_with_tx:
        if e.get("network"):
            all_chains.add(e["network"])
        if e.get("tx_hash"):
            all_tx_hashes.add(e["tx_hash"])

    for e in escrows:
        for field in ("funding_tx", "deposit_tx", "release_tx", "refund_tx"):
            if e.get(field):
                all_tx_hashes.add(e[field])
        meta = e.get("metadata") or {}
        if isinstance(meta, dict):
            for v in meta.values():
                if isinstance(v, str) and v.startswith("0x") and len(v) == 66:
                    all_tx_hashes.add(v)

    print("\n" + "=" * 80)
    print("COMBINED SUMMARY")
    print("=" * 80)
    print(f"Total unique TX hashes: {len(all_tx_hashes)}")
    print(f"Total chains with on-chain activity: {len(all_chains)}")
    if all_chains:
        print(f"Chains: {', '.join(sorted(all_chains))}")

    # Print non-base chains specifically
    non_base = {c for c in all_chains if c != "base"}
    if non_base:
        print(f"\nNon-base chains with TX hashes: {', '.join(sorted(non_base))}")
        print("\nNon-base TX hashes:")
        for e in events_with_tx:
            if e.get("network") in non_base and e.get("tx_hash"):
                print(f"  [{e['network']}] {e['event_type']}: {e['tx_hash']}")
    else:
        print("\nNo non-base chain activity found in payment_events.")


if __name__ == "__main__":
    main()
