"""
Worker Token Preferences Management (NOW-028)

Allows workers to set preferred payment tokens.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .multi_token import PaymentToken, MultiTokenPayments, get_multi_token_payments


class TokenPreferenceManager:
    """
    Manages worker token preferences.

    Workers can:
    - Set primary token preference
    - Accept multiple tokens
    - Enable auto-conversion
    - Set minimum amounts for conversion
    """

    def __init__(self, payments: Optional[MultiTokenPayments] = None):
        self.payments = payments or get_multi_token_payments()
        self._preferences: Dict[str, Dict[str, Any]] = {}

    def set_preference(
        self,
        worker_id: str,
        primary_token: str,
        accepted_tokens: Optional[List[str]] = None,
        auto_convert: bool = False,
        min_amount_for_conversion: float = 10.0
    ) -> Dict[str, Any]:
        """
        Set worker's token preference.

        Args:
            worker_id: Worker identifier
            primary_token: Preferred token (usdc, eurc, dai, usdt)
            accepted_tokens: List of accepted tokens
            auto_convert: Auto-convert to primary
            min_amount_for_conversion: Minimum for auto-conversion

        Returns:
            Updated preference dict
        """
        try:
            primary = PaymentToken(primary_token.lower())
        except ValueError:
            raise ValueError(f"Invalid token: {primary_token}")

        accepted = []
        for t in (accepted_tokens or [primary_token]):
            try:
                accepted.append(PaymentToken(t.lower()))
            except ValueError:
                continue

        if primary not in accepted:
            accepted.insert(0, primary)

        # Update in payments system
        self.payments.set_worker_preference(
            worker_id=worker_id,
            primary_token=primary,
            accepted_tokens=accepted,
            auto_convert=auto_convert
        )

        # Store extended preferences
        pref = {
            "worker_id": worker_id,
            "primary_token": primary.value,
            "accepted_tokens": [t.value for t in accepted],
            "auto_convert": auto_convert,
            "min_amount_for_conversion": min_amount_for_conversion,
            "updated_at": datetime.utcnow().isoformat()
        }
        self._preferences[worker_id] = pref

        return pref

    def get_preference(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get worker's stored preference."""
        return self._preferences.get(worker_id)

    def get_default_preference(self) -> Dict[str, Any]:
        """Get default preference for new workers."""
        return {
            "primary_token": "usdc",
            "accepted_tokens": ["usdc", "dai", "usdt"],
            "auto_convert": False,
            "min_amount_for_conversion": 10.0
        }

    def can_accept_task(
        self,
        worker_id: str,
        task_token: str
    ) -> tuple[bool, Optional[str]]:
        """Check if worker can accept task with given token."""
        pref = self._preferences.get(worker_id)

        if not pref:
            # No preference = accepts anything
            return (True, None)

        try:
            token = PaymentToken(task_token.lower())
        except ValueError:
            return (False, f"Invalid token: {task_token}")

        accepted = [PaymentToken(t) for t in pref["accepted_tokens"]]

        if token in accepted:
            return (True, None)

        if pref["auto_convert"]:
            return (True, f"Will auto-convert to {pref['primary_token']}")

        return (False, f"Worker only accepts: {', '.join(pref['accepted_tokens'])}")

    def get_payment_info(
        self,
        worker_id: str,
        amount: float,
        task_token: str
    ) -> Dict[str, Any]:
        """Get payment info respecting worker preference."""
        pref = self._preferences.get(worker_id) or self.get_default_preference()

        try:
            task_token_enum = PaymentToken(task_token.lower())
            primary_enum = PaymentToken(pref["primary_token"])
        except ValueError:
            task_token_enum = PaymentToken.USDC
            primary_enum = PaymentToken.USDC

        accepted = [PaymentToken(t) for t in pref["accepted_tokens"]]

        # Determine final payment token
        if task_token_enum in accepted:
            final_token = task_token_enum
            conversion_needed = False
        elif pref["auto_convert"] and amount >= pref["min_amount_for_conversion"]:
            final_token = primary_enum
            conversion_needed = True
        else:
            final_token = task_token_enum
            conversion_needed = False

        # Calculate amounts
        final_amount = amount
        if conversion_needed:
            from decimal import Decimal
            final_amount = float(
                self.payments.convert_amount(
                    amount=Decimal(str(amount)),
                    from_token=task_token_enum,
                    to_token=final_token
                )
            )

        return {
            "original_amount": amount,
            "original_token": task_token,
            "final_amount": final_amount,
            "final_token": final_token.value,
            "conversion_applied": conversion_needed,
            "worker_preference": pref["primary_token"]
        }


# Singleton
_manager: Optional[TokenPreferenceManager] = None

def get_token_preference_manager() -> TokenPreferenceManager:
    """Get singleton preference manager."""
    global _manager
    if _manager is None:
        _manager = TokenPreferenceManager()
    return _manager
