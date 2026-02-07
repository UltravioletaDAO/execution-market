"""
Multi-Token Payment Support (NOW-027, NOW-028)

Supports USDC, EURC, DAI, USDT and worker token preferences.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

logger = logging.getLogger(__name__)


class PaymentToken(str, Enum):
    """Supported payment tokens."""

    USDC = "usdc"
    EURC = "eurc"
    DAI = "dai"
    USDT = "usdt"


@dataclass
class TokenConfig:
    """Configuration for a payment token."""

    symbol: str
    name: str
    decimals: int
    base_address: str  # Base Mainnet address
    is_stablecoin: bool = True
    oracle_feed: Optional[str] = None  # For non-USD stablecoins
    min_bounty: float = 0.50
    enabled: bool = True


# Token configurations on Base Mainnet
TOKEN_CONFIGS: Dict[PaymentToken, TokenConfig] = {
    PaymentToken.USDC: TokenConfig(
        symbol="USDC",
        name="USD Coin",
        decimals=6,
        base_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        is_stablecoin=True,
        min_bounty=0.50,
    ),
    PaymentToken.EURC: TokenConfig(
        symbol="EURC",
        name="Euro Coin",
        decimals=6,
        base_address="0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
        is_stablecoin=True,
        oracle_feed="EUR/USD",  # Would need price conversion
        min_bounty=0.50,
    ),
    PaymentToken.DAI: TokenConfig(
        symbol="DAI",
        name="Dai Stablecoin",
        decimals=18,
        base_address="0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        is_stablecoin=True,
        min_bounty=0.50,
    ),
    PaymentToken.USDT: TokenConfig(
        symbol="USDT",
        name="Tether USD",
        decimals=6,
        base_address="0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
        is_stablecoin=True,
        min_bounty=0.50,
    ),
}


@dataclass
class WorkerTokenPreference:
    """Worker's token preferences (NOW-028)."""

    worker_id: str
    primary_token: PaymentToken
    accepted_tokens: List[PaymentToken]
    auto_convert: bool = False  # Auto-convert to primary token
    min_amount_for_conversion: float = 10.0


@dataclass
class PaymentRequest:
    """A payment request with token info."""

    amount: Decimal
    token: PaymentToken
    recipient: str
    task_id: Optional[str] = None
    reference: Optional[str] = None


class MultiTokenPayments:
    """
    Multi-token payment system for Execution Market.

    Features:
    - Support for USDC, EURC, DAI, USDT
    - Worker token preferences
    - Automatic token matching
    - Price conversion for non-USD tokens
    """

    def __init__(self):
        self._worker_preferences: Dict[str, WorkerTokenPreference] = {}
        self._exchange_rates: Dict[str, float] = {
            "EUR/USD": 1.08,  # Would be fetched from oracle
            "DAI/USD": 1.00,
            "USDT/USD": 1.00,
            "USDC/USD": 1.00,
        }

    def get_token_config(self, token: PaymentToken) -> TokenConfig:
        """Get configuration for a token."""
        return TOKEN_CONFIGS[token]

    def get_enabled_tokens(self) -> List[PaymentToken]:
        """Get list of enabled tokens."""
        return [t for t, c in TOKEN_CONFIGS.items() if c.enabled]

    def set_worker_preference(
        self,
        worker_id: str,
        primary_token: PaymentToken,
        accepted_tokens: Optional[List[PaymentToken]] = None,
        auto_convert: bool = False,
    ) -> WorkerTokenPreference:
        """Set worker's token preferences (NOW-028)."""
        pref = WorkerTokenPreference(
            worker_id=worker_id,
            primary_token=primary_token,
            accepted_tokens=accepted_tokens or [primary_token],
            auto_convert=auto_convert,
        )
        self._worker_preferences[worker_id] = pref
        logger.info(f"Worker {worker_id} preference set: {primary_token.value}")
        return pref

    def get_worker_preference(self, worker_id: str) -> Optional[WorkerTokenPreference]:
        """Get worker's token preference."""
        return self._worker_preferences.get(worker_id)

    def match_payment_token(
        self, agent_token: PaymentToken, worker_id: str
    ) -> tuple[PaymentToken, bool]:
        """
        Match agent's payment token with worker's preference.

        Returns:
            (token_to_use, needs_conversion)
        """
        pref = self._worker_preferences.get(worker_id)

        if not pref:
            # Default: accept what agent offers
            return (agent_token, False)

        if agent_token in pref.accepted_tokens:
            # Worker accepts this token
            return (agent_token, False)

        if pref.auto_convert and pref.primary_token != agent_token:
            # Need conversion to worker's preferred token
            return (pref.primary_token, True)

        # Fallback to agent's token (worker will need to accept)
        return (agent_token, False)

    def convert_amount(
        self, amount: Decimal, from_token: PaymentToken, to_token: PaymentToken
    ) -> Decimal:
        """Convert amount between tokens."""
        if from_token == to_token:
            return amount

        # Get exchange rates
        from_rate = self._get_usd_rate(from_token)
        to_rate = self._get_usd_rate(to_token)

        # Convert: amount_in_usd = amount * from_rate
        # amount_in_target = amount_in_usd / to_rate
        usd_amount = amount * Decimal(str(from_rate))
        target_amount = usd_amount / Decimal(str(to_rate))

        return target_amount.quantize(Decimal("0.000001"))

    def _get_usd_rate(self, token: PaymentToken) -> float:
        """Get USD rate for token."""
        TOKEN_CONFIGS[token]

        if token == PaymentToken.EURC:
            return self._exchange_rates.get("EUR/USD", 1.08)

        return 1.0  # USD stablecoins

    def validate_bounty(
        self, amount: float, token: PaymentToken
    ) -> tuple[bool, Optional[str]]:
        """Validate bounty amount for token."""
        config = TOKEN_CONFIGS[token]

        if not config.enabled:
            return (False, f"Token {token.value} is not enabled")

        if amount < config.min_bounty:
            return (False, f"Minimum bounty is ${config.min_bounty}")

        return (True, None)

    def get_payment_summary(
        self,
        task_id: str,
        bounty_usd: float,
        agent_token: PaymentToken,
        worker_id: str,
        platform_fee_pct: float = 0.08,
    ) -> Dict[str, Any]:
        """Generate payment summary for a task."""
        payment_token, needs_conversion = self.match_payment_token(
            agent_token, worker_id
        )

        bounty = Decimal(str(bounty_usd))

        if needs_conversion:
            bounty = self.convert_amount(bounty, agent_token, payment_token)

        platform_fee = bounty * Decimal(str(platform_fee_pct))
        worker_payout = bounty - platform_fee

        config = TOKEN_CONFIGS[payment_token]

        return {
            "task_id": task_id,
            "original_amount": bounty_usd,
            "original_token": agent_token.value,
            "payment_token": payment_token.value,
            "payment_address": config.base_address,
            "decimals": config.decimals,
            "bounty": float(bounty),
            "platform_fee": float(platform_fee),
            "platform_fee_pct": platform_fee_pct,
            "worker_payout": float(worker_payout),
            "conversion_applied": needs_conversion,
        }

    def format_amount(self, amount: float, token: PaymentToken) -> str:
        """Format amount for display."""
        config = TOKEN_CONFIGS[token]
        return f"{amount:.2f} {config.symbol}"


# Singleton
_payments: Optional[MultiTokenPayments] = None


def get_multi_token_payments() -> MultiTokenPayments:
    """Get singleton multi-token payments instance."""
    global _payments
    if _payments is None:
        _payments = MultiTokenPayments()
    return _payments
