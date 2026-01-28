"""
Superfluid Integration for Streaming Payments

Enables real-time payment streams for long-running tasks.
"""

from .client import SuperfluidClient
from .streams import StreamManager

__all__ = ['SuperfluidClient', 'StreamManager']
