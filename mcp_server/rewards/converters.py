"""
Reward Converters

Convert between different reward types and currencies.
"""

import logging
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ConversionRate:
    """Conversion rate between units."""

    from_unit: str
    to_unit: str
    rate: float
    timestamp: datetime
    source: str = "fixed"


class PointsConverter:
    """
    Converts between points and USD.

    Supports:
    - Fixed rate conversion
    - Variable rates by tier
    - Bonus multipliers
    """

    def __init__(
        self,
        base_rate: float = 100.0,  # 100 points = $1
        tier_rates: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize points converter.

        Args:
            base_rate: Points per USD
            tier_rates: Custom rates by tier (e.g., {"gold": 120})
        """
        self.base_rate = base_rate
        self.tier_rates = tier_rates or {}

    def points_to_usd(self, points: float, tier: Optional[str] = None) -> float:
        """
        Convert points to USD.

        Args:
            points: Points amount
            tier: Optional tier for custom rate

        Returns:
            USD amount
        """
        rate = self.tier_rates.get(tier, self.base_rate) if tier else self.base_rate
        return points / rate

    def usd_to_points(
        self, usd: float, tier: Optional[str] = None, bonus_multiplier: float = 1.0
    ) -> float:
        """
        Convert USD to points.

        Args:
            usd: USD amount
            tier: Optional tier for custom rate
            bonus_multiplier: Bonus multiplier (e.g., 1.5 for 50% bonus)

        Returns:
            Points amount
        """
        rate = self.tier_rates.get(tier, self.base_rate) if tier else self.base_rate
        return usd * rate * bonus_multiplier

    def get_rate(self, tier: Optional[str] = None) -> ConversionRate:
        """Get current conversion rate."""
        rate = self.tier_rates.get(tier, self.base_rate) if tier else self.base_rate
        return ConversionRate(
            from_unit="USD",
            to_unit="Points",
            rate=rate,
            timestamp=datetime.now(timezone.utc),
            source="fixed",
        )


class TokenConverter:
    """
    Converts between tokens and USD.

    Supports:
    - Price feed integration
    - Fixed rate fallback
    - Slippage handling
    """

    # Default token prices (fallback)
    DEFAULT_PRICES = {
        "USDC": 1.0,
        "USDT": 1.0,
        "DAI": 1.0,
        "ETH": 3000.0,  # Example
    }

    def __init__(
        self, price_feed_url: Optional[str] = None, cache_ttl_seconds: int = 300
    ):
        """
        Initialize token converter.

        Args:
            price_feed_url: Price oracle URL
            cache_ttl_seconds: Cache TTL for prices
        """
        self.price_feed_url = price_feed_url
        self.cache_ttl = cache_ttl_seconds
        self._price_cache: Dict[str, tuple] = {}

    async def get_token_price(self, symbol: str) -> float:
        """
        Get current token price in USD.

        Args:
            symbol: Token symbol

        Returns:
            Price in USD
        """
        # Check cache
        if symbol in self._price_cache:
            price, timestamp = self._price_cache[symbol]
            if (datetime.now(timezone.utc) - timestamp).seconds < self.cache_ttl:
                return price

        # Try price feed
        if self.price_feed_url:
            try:
                price = await self._fetch_price(symbol)
                self._price_cache[symbol] = (price, datetime.now(timezone.utc))
                return price
            except Exception as e:
                logger.warning(f"Price feed error for {symbol}: {e}")

        # Fallback to defaults
        return self.DEFAULT_PRICES.get(symbol.upper(), 1.0)

    async def token_to_usd(self, amount: float, symbol: str) -> float:
        """
        Convert token amount to USD.

        Args:
            amount: Token amount
            symbol: Token symbol

        Returns:
            USD amount
        """
        price = await self.get_token_price(symbol)
        return amount * price

    async def usd_to_token(
        self, usd: float, symbol: str, slippage: float = 0.01
    ) -> float:
        """
        Convert USD to token amount.

        Args:
            usd: USD amount
            symbol: Token symbol
            slippage: Slippage tolerance (e.g., 0.01 = 1%)

        Returns:
            Token amount (with slippage buffer)
        """
        price = await self.get_token_price(symbol)
        base_amount = usd / price
        # Add slippage buffer (get slightly more tokens)
        return base_amount * (1 - slippage)

    async def _fetch_price(self, symbol: str) -> float:
        """Fetch price from external feed."""
        # Would implement actual price feed call
        # For now, return default
        return self.DEFAULT_PRICES.get(symbol.upper(), 1.0)

    def get_conversion_rate(
        self, from_symbol: str, to_symbol: str = "USD"
    ) -> ConversionRate:
        """Get conversion rate between tokens."""
        # Synchronous fallback
        from_price = self.DEFAULT_PRICES.get(from_symbol.upper(), 1.0)
        to_price = self.DEFAULT_PRICES.get(to_symbol.upper(), 1.0)
        rate = from_price / to_price

        return ConversionRate(
            from_unit=from_symbol,
            to_unit=to_symbol,
            rate=rate,
            timestamp=datetime.now(timezone.utc),
            source="default",
        )


# Utility functions


def format_reward_display(amount: float, unit: str, decimals: int = 2) -> str:
    """
    Format reward for display.

    Args:
        amount: Amount
        unit: Unit (USDC, Points, etc.)
        decimals: Decimal places

    Returns:
        Formatted string (e.g., "$5.00 USDC", "500 Points")
    """
    if unit.upper() in ["USDC", "USDT", "DAI", "USD"]:
        return f"${amount:.{decimals}f} {unit}"
    else:
        if amount == int(amount):
            return f"{int(amount)} {unit}"
        return f"{amount:.{decimals}f} {unit}"
