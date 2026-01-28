"""
Chamba ERC-8004 Integration

On-chain identity and reputation for the Chamba platform.
"""

from .register import ERC8004Registry
from .reputation import ReputationManager

__all__ = ['ERC8004Registry', 'ReputationManager']
