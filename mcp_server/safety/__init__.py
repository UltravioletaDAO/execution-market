"""
Chamba Safety Module

Provides worker safety features:
- NOW-112: Safety pre-investigation (crime data, time of day risk, private property)
- NOW-113: Hostile meatspace protocol (safety score, proof of attempt for obstacles)

Usage:
    from chamba.safety import SafetyInvestigator, HostileProtocolManager
    from chamba.safety.investigation import SafetyRisk, RiskFactor
    from chamba.safety.hostile_protocol import ObstacleType, ObstacleReport
"""

from .investigation import (
    SafetyInvestigator,
    SafetyAssessment,
    SafetyRisk,
    RiskFactor,
    LocationRiskData,
)
from .hostile_protocol import (
    HostileProtocolManager,
    ObstacleReport,
    ObstacleType,
    ProofOfAttempt,
    CompensationDecision,
)

__all__ = [
    # Investigation
    "SafetyInvestigator",
    "SafetyAssessment",
    "SafetyRisk",
    "RiskFactor",
    "LocationRiskData",
    # Hostile Protocol
    "HostileProtocolManager",
    "ObstacleReport",
    "ObstacleType",
    "ProofOfAttempt",
    "CompensationDecision",
]
