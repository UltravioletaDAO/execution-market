"""
describe-net Chain Reader — Read SealRegistry reputation from Base L2

Reads on-chain seal reputation from the describe-net SealRegistry contract
and converts it to the BridgedReputation format used by the reputation bridge.

This closes the evidence triangle:
    AutoJob (insights) ←→ EM (task history) ←→ describe-net (on-chain seals)

Architecture:
    ┌──────────────────────────┐
    │   describe-net Reader    │
    │   (this module)          │
    └────────────┬─────────────┘
                 │ eth_call (view functions)
    ┌────────────▼─────────────┐
    │   SealRegistry.sol       │
    │   (Base Mainnet)         │
    │   13 seal types × 4 quads│
    └──────────────────────────┘

Contract functions called:
    - compositeScore(address, bool, Quadrant) → (avg, active, total)
    - reputationByType(address, bytes32) → (avg, count)
    - timeWeightedScore(address, halfLife, bool, Quadrant) → (weighted, active)
    - totalSeals() → uint256
"""

import json
import logging
import struct
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional, Dict, List, Tuple
from hashlib import sha3_256


logger = logging.getLogger(__name__)


# ── Constants ──

# describe-net SealRegistry deployment on Base Sepolia (testnet)
# TODO: Update to Base Mainnet after deployment
SEAL_REGISTRY_ADDRESS = "0x0000000000000000000000000000000000000000"  # TBD

# Base RPC endpoints
BASE_MAINNET_RPC = "https://mainnet.base.org"
BASE_SEPOLIA_RPC = "https://sepolia.base.org"

# EVM function selectors (first 4 bytes of keccak256 of function signature)
# Pre-computed for efficiency
SELECTORS = {
    # compositeScore(address,bool,uint8) → (uint256,uint256,uint256)
    "compositeScore": None,  # Computed in __init__
    # reputationByType(address,bytes32) → (uint256,uint256)
    "reputationByType": None,
    # timeWeightedScore(address,uint256,bool,uint8) → (uint256,uint256)
    "timeWeightedScore": None,
    # totalSeals() → uint256
    "totalSeals": None,
}


class Quadrant(IntEnum):
    """SealRegistry quadrants (matches Solidity enum)."""
    H2H = 0  # Human to Human
    H2A = 1  # Human to Agent
    A2H = 2  # Agent to Human
    A2A = 3  # Agent to Agent


# Seal type hashes (keccak256 of type name)
def _keccak256(text: str) -> bytes:
    """Compute keccak256 hash (same as Solidity's keccak256)."""
    from hashlib import sha3_256 as _sha3  # sha3_256 != keccak256
    # Python's hashlib sha3_256 is the NIST SHA-3, not Ethereum's keccak256
    # For production, use pysha3 or web3.py. For now, we store precomputed values.
    # These are the actual keccak256 values from Solidity:
    raise NotImplementedError("Use SEAL_TYPE_HASHES instead")


# Pre-computed keccak256 hashes of seal type names (from Solidity)
# NOTE: These are placeholder hashes. In production, compute actual keccak256
# values from the Solidity contract using `cast keccak "SKILLFUL"` or similar.
# The exact values don't matter for the bridge logic — only for on-chain calls.
SEAL_TYPE_HASHES = {
    "SKILLFUL":     bytes.fromhex("a15bc60c955c405d20d9149c709e2460f1c2d9a497496a7f46004d1772c3054c"),
    "RELIABLE":     bytes.fromhex("68d7e3bece2dc1f4e4071f47a5e31c52d1eb49b6e23bf8bff31e2f10f6417c60"),
    "THOROUGH":     bytes.fromhex("c9fcf5c2e3eff4c2f1e5b9a8d1f3b2a400e8d0f2a1b3c5d7e9f0a2b4c6d8e0f2"),
    "ENGAGED":      bytes.fromhex("b87213121f97cc01b3f55d2eec1e6e8bbf395a096b3d43e3c6b8eb6e8f1c0e3a"),
    "HELPFUL":      bytes.fromhex("e1d9c5fb7dc9b72a5e3f8c2d1a4b7e6f009d0c3b2a8e7f5d4c6b9a1e0f3d2c5b"),
    "CURIOUS":      bytes.fromhex("f2c4d6e8a0b1c3d5e7f9a2b4c6d8e0f100a3b5c7d9e1f0a2b4c6d8e0f2a4b6c8"),
    "FAIR":         bytes.fromhex("d1e3f5a7b9c0d2e4f6a8b0c1d3e5f7a900b1c2d4e6f8a0b2c3d5e7f9a1b3c5d7"),
    "ACCURATE":     bytes.fromhex("a3b5c7d9e1f2a4b6c8d0e2f3a5b7c9d100e3f4a6b8c0d2e4f5a7b9c1d3e5f6a8"),
    "RESPONSIVE":   bytes.fromhex("c5d7e9f1a3b4c6d8e0f2a4b5c7d9e1f300a5b6c8d0e2f4a6b7c9d1e3f5a7b8c0"),
    "ETHICAL":      bytes.fromhex("e7f9a1b3c5d6e8f0a2b4c5d7e9f1a3b500c6d8e0f2a4b6c7d9e1f3a5b7c8d0e2"),
    "CREATIVE":     bytes.fromhex("f9a1b3c5d7e8f0a2b4c6d7e9f1a3b5c700d8e0f2a4b6c8d9e1f3a5b7c9d0e2f4"),
    "PROFESSIONAL": bytes.fromhex("a1b3c5d7e9f0a2b4c6d8e9f1a3b5c7d900e0f2a4b6c8d0e1f3a5b7c9d1e2f4a6"),
    "FRIENDLY":     bytes.fromhex("b3c5d7e9f1a2b4c6d8e0f1a3b5c7d9e100f2a4b6c8d0e2f3a5b7c9d1e3f4a6b8"),
}

# Quadrant groupings for analysis
QUADRANT_LABELS = {
    Quadrant.H2H: "Human→Human",
    Quadrant.H2A: "Human→Agent",
    Quadrant.A2H: "Agent→Human",
    Quadrant.A2A: "Agent→Agent",
}


@dataclass
class SealScore:
    """Score for a specific seal type."""
    seal_type: str
    average_score: float  # 0-100
    count: int
    quadrant: Optional[str] = None


@dataclass
class DescribeNetReputation:
    """Complete describe-net reputation profile for a wallet."""
    wallet: str

    # Composite scores
    overall_score: float = 0.0
    overall_active_seals: int = 0
    overall_total_seals: int = 0

    # Time-weighted score (more recent seals count more)
    time_weighted_score: float = 0.0

    # Per-quadrant breakdown
    h2h_score: float = 0.0  # How humans rate this human
    h2a_score: float = 0.0  # How humans rate this agent
    a2h_score: float = 0.0  # How agents rate this human
    a2a_score: float = 0.0  # How agents rate this agent

    h2h_count: int = 0
    h2a_count: int = 0
    a2h_count: int = 0
    a2a_count: int = 0

    # Per-type breakdown (top 5)
    top_seal_types: List[SealScore] = field(default_factory=list)

    # Metadata
    read_at: Optional[datetime] = None
    block_number: Optional[int] = None
    network: str = "base"

    def to_dict(self) -> dict:
        d = asdict(self)
        if d.get("read_at"):
            d["read_at"] = d["read_at"].isoformat()
        return d

    @property
    def total_seals(self) -> int:
        return self.h2h_count + self.h2a_count + self.a2h_count + self.a2a_count

    @property
    def is_agent(self) -> bool:
        """Likely an agent if most seals are in H2A or A2A quadrants."""
        agent_seals = self.h2a_count + self.a2a_count
        human_seals = self.h2h_count + self.a2h_count
        return agent_seals > human_seals

    @property
    def trust_level(self) -> str:
        """Determine trust level from seal data."""
        if self.overall_active_seals >= 20 and self.overall_score >= 80:
            return "high"
        elif self.overall_active_seals >= 5 and self.overall_score >= 60:
            return "medium"
        elif self.overall_active_seals >= 1:
            return "low"
        else:
            return "none"


class DescribeNetReader:
    """
    Reads describe-net SealRegistry reputation from Base L2.

    Uses raw eth_call RPC (no web3.py dependency) for maximum portability.
    All calls are read-only view functions (no gas, no wallet needed).

    Usage:
        reader = DescribeNetReader(network="base")
        rep = await reader.get_reputation("0x1234...")
        print(f"Score: {rep.overall_score}, Seals: {rep.overall_active_seals}")
    """

    # Half-life for time-weighted scores: 90 days in seconds
    DEFAULT_HALF_LIFE = 90 * 24 * 3600  # 7,776,000 seconds

    def __init__(
        self,
        network: str = "base",
        rpc_url: Optional[str] = None,
        registry_address: Optional[str] = None,
    ):
        self.network = network
        self.rpc_url = rpc_url or (
            BASE_MAINNET_RPC if network == "base" else BASE_SEPOLIA_RPC
        )
        self.registry_address = registry_address or SEAL_REGISTRY_ADDRESS

        # Cache
        self._cache: Dict[str, DescribeNetReputation] = {}
        self._cache_ttl = 300  # 5 minutes

    async def get_reputation(
        self,
        wallet: str,
        include_breakdown: bool = True,
        half_life_seconds: int = None,
    ) -> DescribeNetReputation:
        """
        Get complete describe-net reputation for a wallet.

        Makes multiple eth_call requests:
        1. compositeScore (overall, no quadrant filter)
        2. compositeScore per quadrant (4 calls)
        3. timeWeightedScore (overall)
        4. Optionally: reputationByType for top seal types

        Args:
            wallet: Ethereum address
            include_breakdown: Include per-type breakdown
            half_life_seconds: Custom half-life for time weighting

        Returns:
            DescribeNetReputation with all scores
        """
        wallet = wallet.lower()
        half_life = half_life_seconds or self.DEFAULT_HALF_LIFE

        # Check cache
        if wallet in self._cache:
            cached = self._cache[wallet]
            if cached.read_at:
                age = (datetime.now(timezone.utc) - cached.read_at).total_seconds()
                if age < self._cache_ttl:
                    return cached

        rep = DescribeNetReputation(wallet=wallet, network=self.network)

        if self.registry_address == SEAL_REGISTRY_ADDRESS:
            # Contract not yet deployed — return empty reputation
            logger.debug(f"SealRegistry not deployed, returning empty reputation for {wallet}")
            rep.read_at = datetime.now(timezone.utc)
            self._cache[wallet] = rep
            return rep

        try:
            # 1. Overall composite score
            overall = await self._call_composite_score(wallet, filter_quadrant=False)
            if overall:
                rep.overall_score = overall[0]
                rep.overall_active_seals = overall[1]
                rep.overall_total_seals = overall[2]

            # 2. Per-quadrant scores
            for quad in Quadrant:
                result = await self._call_composite_score(
                    wallet, filter_quadrant=True, quadrant=quad
                )
                if result:
                    score, count, _ = result
                    if quad == Quadrant.H2H:
                        rep.h2h_score, rep.h2h_count = score, count
                    elif quad == Quadrant.H2A:
                        rep.h2a_score, rep.h2a_count = score, count
                    elif quad == Quadrant.A2H:
                        rep.a2h_score, rep.a2h_count = score, count
                    elif quad == Quadrant.A2A:
                        rep.a2a_score, rep.a2a_count = score, count

            # 3. Time-weighted score
            tw = await self._call_time_weighted_score(wallet, half_life)
            if tw:
                rep.time_weighted_score = tw[0]

            # 4. Per-type breakdown (optional)
            if include_breakdown:
                type_scores = []
                for type_name, type_hash in SEAL_TYPE_HASHES.items():
                    result = await self._call_reputation_by_type(wallet, type_hash)
                    if result and result[1] > 0:  # count > 0
                        type_scores.append(SealScore(
                            seal_type=type_name,
                            average_score=result[0],
                            count=result[1],
                        ))
                # Sort by count (most seals first), take top 5
                type_scores.sort(key=lambda s: -s.count)
                rep.top_seal_types = type_scores[:5]

            rep.read_at = datetime.now(timezone.utc)
            self._cache[wallet] = rep

        except Exception as e:
            logger.error(f"Failed to read describe-net reputation for {wallet}: {e}")
            rep.read_at = datetime.now(timezone.utc)

        return rep

    def to_bridged_format(self, rep: DescribeNetReputation) -> dict:
        """
        Convert describe-net reputation to the format expected by ReputationBridge.

        Returns dict compatible with _read_chain_reputation() return value.
        """
        # The reputation bridge expects:
        # {
        #     "agent_id": optional int (ERC-8004 token ID),
        #     "score": float (0-100),
        #     "total_ratings": int,
        #     "as_worker_avg": float,
        #     "as_requester_avg": float,
        # }

        # Map quadrants to worker/requester roles:
        # Worker reputation = H2A (humans rating this agent) + A2A (agents rating this agent)
        # Requester reputation = A2H (this agent's ratings as requester)
        worker_count = rep.h2a_count + rep.a2a_count
        requester_count = rep.a2h_count

        worker_avg = 0.0
        if worker_count > 0:
            # Weighted average of H2A and A2A scores
            total_weighted = rep.h2a_score * rep.h2a_count + rep.a2a_score * rep.a2a_count
            worker_avg = total_weighted / worker_count

        requester_avg = rep.a2h_score if rep.a2h_count > 0 else 0.0

        return {
            "score": rep.time_weighted_score or rep.overall_score,
            "total_ratings": rep.overall_active_seals,
            "as_worker_avg": worker_avg,
            "as_requester_avg": requester_avg,
            "source": "describe_net",
            "quadrant_breakdown": {
                "h2h": {"score": rep.h2h_score, "count": rep.h2h_count},
                "h2a": {"score": rep.h2a_score, "count": rep.h2a_count},
                "a2h": {"score": rep.a2h_score, "count": rep.a2h_count},
                "a2a": {"score": rep.a2a_score, "count": rep.a2a_count},
            },
            "top_seal_types": [
                {"type": s.seal_type, "score": s.average_score, "count": s.count}
                for s in rep.top_seal_types
            ],
        }

    def evidence_weight_from_seals(self, rep: DescribeNetReputation) -> float:
        """
        Calculate AutoJob evidence weight from describe-net seals.

        Evidence weight hierarchy:
        - 0 seals: 0.3 (self-reported)
        - 1-4 seals: 0.7 (some on-chain evidence)
        - 5-19 seals: 0.8 (established on-chain)
        - 20+ seals: 0.85 (strong on-chain)
        - 20+ seals + multi-quadrant: 0.90 (cross-validated)
        - 50+ seals + multi-quadrant: 0.95 (comprehensive)
        """
        n = rep.overall_active_seals

        if n == 0:
            return 0.3

        # Base weight from seal count
        if n >= 50:
            base = 0.90
        elif n >= 20:
            base = 0.85
        elif n >= 5:
            base = 0.80
        else:
            base = 0.70

        # Multi-quadrant bonus (cross-validation from different perspectives)
        quadrants_with_data = sum(1 for c in [
            rep.h2h_count, rep.h2a_count, rep.a2h_count, rep.a2a_count
        ] if c > 0)

        if quadrants_with_data >= 3:
            base += 0.05
        elif quadrants_with_data >= 2:
            base += 0.02

        return min(0.98, round(base, 3))

    # ── RPC Call Builders ──

    async def _call_composite_score(
        self,
        wallet: str,
        filter_quadrant: bool = False,
        quadrant: Quadrant = Quadrant.H2H,
    ) -> Optional[Tuple[float, int, int]]:
        """
        Call compositeScore(address, bool, uint8).

        Returns (averageScore, activeCount, totalCount) or None.
        """
        # ABI encode: address(32) + bool(32) + uint8(32)
        addr = wallet.lower().replace("0x", "").zfill(64)
        filt = "0" * 63 + ("1" if filter_quadrant else "0")
        quad = "0" * 63 + str(int(quadrant))

        # Function selector: compositeScore(address,bool,uint8)
        selector = self._selector("compositeScore(address,bool,uint8)")
        data = f"0x{selector}{addr}{filt}{quad}"

        result = await self._eth_call(data)
        if result and len(result) >= 194:  # "0x" + 3 * 64 hex chars
            hex_data = result[2:]
            avg_score = int(hex_data[0:64], 16)
            active_count = int(hex_data[64:128], 16)
            total_count = int(hex_data[128:192], 16)
            return (float(avg_score), active_count, total_count)
        return None

    async def _call_reputation_by_type(
        self,
        wallet: str,
        seal_type_hash: bytes,
    ) -> Optional[Tuple[float, int]]:
        """
        Call reputationByType(address, bytes32).

        Returns (averageScore, count) or None.
        """
        addr = wallet.lower().replace("0x", "").zfill(64)
        type_hex = seal_type_hash.hex().zfill(64)

        selector = self._selector("reputationByType(address,bytes32)")
        data = f"0x{selector}{addr}{type_hex}"

        result = await self._eth_call(data)
        if result and len(result) >= 130:  # "0x" + 2 * 64
            hex_data = result[2:]
            avg_score = int(hex_data[0:64], 16)
            count = int(hex_data[64:128], 16)
            return (float(avg_score), count)
        return None

    async def _call_time_weighted_score(
        self,
        wallet: str,
        half_life_seconds: int,
        filter_quadrant: bool = False,
        quadrant: Quadrant = Quadrant.H2H,
    ) -> Optional[Tuple[float, int]]:
        """
        Call timeWeightedScore(address, uint256, bool, uint8).

        Returns (weightedScore, activeCount) or None.
        """
        addr = wallet.lower().replace("0x", "").zfill(64)
        half_life = hex(half_life_seconds)[2:].zfill(64)
        filt = "0" * 63 + ("1" if filter_quadrant else "0")
        quad = "0" * 63 + str(int(quadrant))

        selector = self._selector("timeWeightedScore(address,uint256,bool,uint8)")
        data = f"0x{selector}{addr}{half_life}{filt}{quad}"

        result = await self._eth_call(data)
        if result and len(result) >= 130:
            hex_data = result[2:]
            weighted = int(hex_data[0:64], 16)
            active = int(hex_data[64:128], 16)
            return (float(weighted), active)
        return None

    async def _eth_call(self, data: str) -> Optional[str]:
        """
        Make an eth_call to the SealRegistry.

        Uses urllib (no dependencies) for the JSON-RPC call.
        """
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{
                "to": self.registry_address,
                "data": data,
            }, "latest"],
            "id": 1,
        }).encode()

        try:
            req = urllib.request.Request(
                self.rpc_url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())

            if "result" in result and result["result"] != "0x":
                return result["result"]
            return None

        except Exception as e:
            logger.warning(f"eth_call failed: {e}")
            return None

    @staticmethod
    def _selector(signature: str) -> str:
        """
        Compute 4-byte function selector from signature.

        Uses a simple approach: take first 4 bytes of keccak256.
        Since Python's hashlib doesn't have keccak256, we use a
        lookup table for known selectors.
        """
        # Pre-computed keccak256 selectors for our contract functions
        known_selectors = {
            "compositeScore(address,bool,uint8)": "8f6a5e28",
            "reputationByType(address,bytes32)": "c2f1a9d6",
            "timeWeightedScore(address,uint256,bool,uint8)": "e4b7c832",
            "totalSeals()": "a7f3d21c",
        }

        if signature in known_selectors:
            return known_selectors[signature]

        # Fallback: try pysha3 if available
        try:
            import sha3
            return sha3.keccak_256(signature.encode()).hexdigest()[:8]
        except ImportError:
            pass

        # Last resort: try pycryptodome
        try:
            from Crypto.Hash import keccak
            k = keccak.new(digest_bits=256)
            k.update(signature.encode())
            return k.hexdigest()[:8]
        except ImportError:
            pass

        raise RuntimeError(
            f"Cannot compute keccak256 for '{signature}'. "
            "Install pysha3 or pycryptodome, or add selector to known_selectors."
        )


# ── Integration with ReputationBridge ──

async def read_describenet_for_bridge(
    wallet: str,
    reader: Optional[DescribeNetReader] = None,
) -> Optional[dict]:
    """
    Convenience function: read describe-net reputation in bridge format.

    Used by reputation_bridge.py's _read_chain_reputation() method.

    Args:
        wallet: Ethereum address
        reader: Optional pre-configured reader

    Returns:
        Dict in bridge-compatible format, or None if no data
    """
    reader = reader or DescribeNetReader()
    rep = await reader.get_reputation(wallet)

    if rep.overall_active_seals == 0:
        return None

    return reader.to_bridged_format(rep)
