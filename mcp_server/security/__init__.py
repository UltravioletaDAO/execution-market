"""
Security module for Execution Market MCP Server.

Includes:
- Fraud detection (multi-device, wash trading, collusion, behavioral)
- GPS anti-spoofing (mock location, plausibility, history)
- Image analysis (AI detection, manipulation, metadata)
- Behavioral analysis (velocity, collusion, multi-account)
- Rate limiting (tier-based, Redis backend)
"""

# Core fraud detection (existing)
from .fraud_detection import (
    FraudDetector as CoreFraudDetector,
    FraudSignal,
    FraudAlert,
    RiskLevel as CoreRiskLevel,
    EntityProfile,
    FraudConfig,
)

# Unified fraud detector (NEW - main entry point)
from .fraud_detector import (
    FraudDetector,
    FraudScore,
    FraudCheckResult,
    SubmissionData,
    FraudDetectorConfig,
    RiskLevel,
    analyze_submission_fraud,
)

# GPS anti-spoofing (NEW)
from .gps_antispoofing import (
    GPSAntiSpoofing,
    GPSData,
    DeviceInfo,
    SensorData,
    SpoofingResult,
    MockLocationResult,
    PlausibilityResult,
    MockLocationIndicator,
)

# Image analysis (NEW)
from .image_analysis import (
    ImageAnalyzer,
    ImageAnalysisResult,
    MetadataConsistencyResult,
    SimilarityResult,
)

# Behavioral analysis (NEW)
from .behavioral import (
    BehavioralAnalyzer,
    BehavioralResult,
    BehavioralFlag,
    ExecutorProfile,
)

# Rate limiter with Redis (NEW)
from .rate_limiter import (
    RateLimiter,
    RateLimitTier,
    RateLimitResult,
    SlidingWindowConfig,
    TIER_LIMITS,
    check_all_limits,
)

# Legacy rate limits (may not exist)
try:
    from .rate_limits import TASK_LIMITS
    _HAS_LEGACY_RATE_LIMITS = True
except ImportError:
    _HAS_LEGACY_RATE_LIMITS = False

__all__ = [
    # Main fraud detector (unified)
    "FraudDetector",
    "FraudScore",
    "FraudCheckResult",
    "SubmissionData",
    "FraudDetectorConfig",
    "RiskLevel",
    "analyze_submission_fraud",

    # Core fraud detection
    "CoreFraudDetector",
    "FraudSignal",
    "FraudAlert",
    "CoreRiskLevel",
    "EntityProfile",
    "FraudConfig",

    # GPS anti-spoofing
    "GPSAntiSpoofing",
    "GPSData",
    "DeviceInfo",
    "SensorData",
    "SpoofingResult",
    "MockLocationResult",
    "PlausibilityResult",
    "MockLocationIndicator",

    # Image analysis
    "ImageAnalyzer",
    "ImageAnalysisResult",
    "MetadataConsistencyResult",
    "SimilarityResult",

    # Behavioral analysis
    "BehavioralAnalyzer",
    "BehavioralResult",
    "BehavioralFlag",
    "ExecutorProfile",

    # Rate limiting
    "RateLimiter",
    "RateLimitTier",
    "RateLimitResult",
    "SlidingWindowConfig",
    "TIER_LIMITS",
    "check_all_limits",
]

if _HAS_LEGACY_RATE_LIMITS:
    __all__.append("TASK_LIMITS")
