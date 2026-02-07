"""
Execution Market Verification System

Multi-tier verification for task evidence:
1. Auto-verification (GPS, timestamp, schema)
2. AI verification (Claude Vision)
3. Agent review
4. Human arbitration

Includes fraud detection for:
- Screenshots
- Gallery photos
- GPS spoofing (NOW-108: network triangulation, movement patterns, sensor fusion)
- Multi-device detection (NOW-109: same worker using multiple devices)
- Rate limits (NOW-111: 50 tasks/day/IP, 20/device)
- Hardware attestation (NOW-076 to NOW-082: iOS Secure Enclave, Android StrongBox)
- Duplicate submissions
"""

from .checks.photo_source import check_photo_source, PhotoSourceResult
from .ai_review import AIVerifier, VerificationResult, VerificationDecision, verify_with_ai
from .providers import (
    VerificationProvider,
    AnthropicProvider,
    OpenAIProvider,
    BedrockProvider,
    get_provider,
    list_available_providers,
)
from .gps_antispoofing import (
    GPSAntiSpoofing,
    SpoofingResult,
    SpoofingRisk,
    GPSData,
    DeviceInfo,
    SensorData,
    RateLimitResult,
    MultiDeviceResult,
    check_gps_spoofing,
)
from .attestation import (
    AttestationVerifier,
    AttestationResult,
    AttestationLevel,
    AttestationRequirement,
    AttestationError,
    DevicePlatform,
    PhotoSignature,
    DeviceAttestation,
    PhotoMetadata,
    DeviceFingerprint,
    verify_attestation,
    get_attestation_requirement,
)

__all__ = [
    # Photo source verification
    "check_photo_source",
    "PhotoSourceResult",
    # AI verification
    "AIVerifier",
    "VerificationResult",
    "VerificationDecision",
    "verify_with_ai",
    # Multi-provider support
    "VerificationProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "BedrockProvider",
    "get_provider",
    "list_available_providers",
    # GPS anti-spoofing (NOW-108, NOW-109, NOW-111)
    "GPSAntiSpoofing",
    "SpoofingResult",
    "SpoofingRisk",
    "GPSData",
    "DeviceInfo",
    "SensorData",
    "RateLimitResult",
    "MultiDeviceResult",
    "check_gps_spoofing",
    # Hardware attestation (NOW-076 to NOW-082)
    "AttestationVerifier",
    "AttestationResult",
    "AttestationLevel",
    "AttestationRequirement",
    "AttestationError",
    "DevicePlatform",
    "PhotoSignature",
    "DeviceAttestation",
    "PhotoMetadata",
    "DeviceFingerprint",
    "verify_attestation",
    "get_attestation_requirement",
]
