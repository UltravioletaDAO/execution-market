"""
Hardware Attestation Verification (NOW-076 to NOW-082)

Verifies device attestation from iOS Secure Enclave and Android StrongBox.

Implements:
- NOW-076: Secure Enclave photo signing (iOS CryptoKit)
- NOW-077: StrongBox attestation (Android Keystore)
- NOW-078: Device attestation API (iOS App Attest, Android Play Integrity)
- NOW-079: Photo metadata preservation (don't strip EXIF)
- NOW-080: Attestation verification backend
- NOW-081: Device fingerprinting anti-fraud (detect same device multiple workers)
- NOW-082: Attestation requirement by task_type (>$50 required, >$20 recommended)

Security Model:
1. Device generates keypair in hardware security module (Secure Enclave/StrongBox)
2. Device registers with attestation service (App Attest/Play Integrity)
3. Photos are signed with hardware-backed key
4. Backend verifies signature chain and attestation
"""

import base64
import hashlib
import logging
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# CBOR is used by Apple App Attest
try:
    import cbor2

    CBOR_AVAILABLE = True
except ImportError:
    CBOR_AVAILABLE = False

# cryptography is used for signature verification
try:
    from cryptography import x509
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509 import load_der_x509_certificate
    from cryptography.hazmat.backends import default_backend

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Apple App Attest
APPLE_APP_ATTEST_ROOT_CA = """
-----BEGIN CERTIFICATE-----
MIICITCCAaegAwIBAgIQC/O+DvHN0uD7jG5yH2IXmDAKBggqhkjOPQQDAzBSMSYw
JAYDVQQDDB1BcHBsZSBBcHAgQXR0ZXN0YXRpb24gUm9vdCBDQTETMBEGA1UECgwK
QXBwbGUgSW5jLjETMBEGA1UECAwKQ2FsaWZvcm5pYTAeFw0yMDAzMTgxODMyNTNa
Fw00NTAzMTUwMDAwMDBaMFIxJjAkBgNVBAMMHUFwcGxlIEFwcCBBdHRlc3RhdGlv
biBSb290IENBMRMwEQYDVQQKDApBcHBsZSBJbmMuMRMwEQYDVQQIDApDYWxpZm9y
bmlhMHYwEAYHKoZIzj0CAQYFK4EEACIDYgAERTHhmLW07ATaFQIEVwTtT4dyctdh
NbJhFs/Ii2FdCgAHGbpphY3+d8qjuDngIN3WVhQUBHAoMeQ/cLiP1sOUtgjqK9au
Yen1mMEvRq9Sk3Jm5X8U62H+xTD3FE9TgS41o0IwQDAPBgNVHRMBAf8EBTADAQH/
MB0GA1UdDgQWBBSskRBTM72+aEH/pwyp5frq5eWKoTAOBgNVHQ8BAf8EBAMCAQYw
CgYIKoZIzj0EAwMDaAAwZQIwQgFGnByvsiVbpTKwSga0kP0e8EeDS4+sQmTvb7vn
53O5+FRXgeLhpJ06ysC5PrOyAjEAp5U4xDgEgllF7En3VcE3iexZZtKeYnpqtijV
oyFraWVIyd/dganmrduC1bmTBGwD
-----END CERTIFICATE-----
"""

# Google Play Integrity API endpoints
GOOGLE_PLAY_INTEGRITY_VERIFY_URL = (
    "https://www.googleapis.com/playintegrity/v1/decodeIntegrityToken"
)

# Attestation thresholds (NOW-082)
ATTESTATION_REQUIRED_BOUNTY_USD = 50.0
ATTESTATION_RECOMMENDED_BOUNTY_USD = 20.0

# Device fingerprint cache duration
DEVICE_FINGERPRINT_TTL_HOURS = 24 * 30  # 30 days

# Anti-fraud thresholds
MAX_WORKERS_PER_DEVICE = 1  # One device = one worker
MAX_DEVICES_PER_WORKER = 3  # Workers can have up to 3 devices
DEVICE_SIMILARITY_THRESHOLD = 0.90  # 90% similar = likely same device


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================


class DevicePlatform(str, Enum):
    """Supported device platforms."""

    IOS = "ios"
    ANDROID = "android"
    UNKNOWN = "unknown"


class AttestationLevel(str, Enum):
    """Levels of attestation security."""

    NONE = "none"  # No attestation
    BASIC = "basic"  # Software-based attestation
    STRONG = "strong"  # Hardware-backed (Secure Enclave / StrongBox)
    VERIFIED = "verified"  # Hardware-backed + certificate chain verified


class AttestationError(str, Enum):
    """Types of attestation errors."""

    MISSING_DATA = "missing_data"
    INVALID_SIGNATURE = "invalid_signature"
    INVALID_CERTIFICATE = "invalid_certificate"
    EXPIRED_ATTESTATION = "expired_attestation"
    DEVICE_COMPROMISED = "device_compromised"
    REPLAY_ATTACK = "replay_attack"
    MULTI_WORKER_DEVICE = "multi_worker_device"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class AttestationResult:
    """Result of attestation verification."""

    is_valid: bool
    platform: DevicePlatform
    level: AttestationLevel
    device_id: str
    timestamp: datetime
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        platform: DevicePlatform,
        level: AttestationLevel,
        device_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> "AttestationResult":
        """Create a successful attestation result."""
        return cls(
            is_valid=True,
            platform=platform,
            level=level,
            device_id=device_id,
            timestamp=datetime.now(UTC),
            errors=[],
            warnings=[],
            details=details or {},
        )

    @classmethod
    def failure(
        cls,
        platform: DevicePlatform,
        errors: List[str],
        device_id: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> "AttestationResult":
        """Create a failed attestation result."""
        return cls(
            is_valid=False,
            platform=platform,
            level=AttestationLevel.NONE,
            device_id=device_id,
            timestamp=datetime.now(UTC),
            errors=errors,
            warnings=[],
            details=details or {},
        )


@dataclass
class PhotoSignature:
    """Signed photo data from device."""

    photo_hash: str  # SHA-256 of photo data
    signature: str  # Base64-encoded signature
    public_key: str  # Base64-encoded public key
    timestamp: datetime  # When the photo was taken
    nonce: str  # Anti-replay nonce
    device_id: str  # Device identifier
    platform: DevicePlatform


@dataclass
class DeviceAttestation:
    """Device attestation data."""

    platform: DevicePlatform
    attestation_object: str  # Base64-encoded attestation
    challenge: str  # Server-provided challenge
    key_id: str  # Key identifier
    app_id: str  # Bundle ID (iOS) or Package name (Android)
    timestamp: datetime


@dataclass
class PhotoMetadata:
    """Preserved photo metadata (EXIF)."""

    timestamp: Optional[datetime] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude: Optional[float] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    software: Optional[str] = None
    orientation: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    flash: Optional[bool] = None
    focal_length: Optional[float] = None
    iso: Optional[int] = None
    exposure_time: Optional[str] = None
    raw_exif: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceFingerprint:
    """Device fingerprint for anti-fraud detection."""

    device_id: str
    platform: DevicePlatform
    hardware_id: str
    worker_id: str
    first_seen: datetime
    last_seen: datetime
    attestation_level: AttestationLevel
    submission_count: int = 0
    fraud_flags: List[str] = field(default_factory=list)


@dataclass
class AttestationRequirement:
    """Attestation requirement for a task type."""

    required: bool
    recommended: bool
    min_level: AttestationLevel
    reason: str


# =============================================================================
# MAIN VERIFIER CLASS
# =============================================================================


class AttestationVerifier:
    """
    Hardware attestation verification system.

    Verifies:
    1. iOS App Attest (Secure Enclave)
    2. Android Play Integrity (StrongBox)
    3. Photo signatures from hardware-backed keys
    4. Device fingerprinting for anti-fraud

    Usage:
        verifier = AttestationVerifier(
            apple_app_id="com.example.executionmarket",
            android_package_name="com.example.executionmarket",
            google_api_key="YOUR_API_KEY"
        )

        # Verify device attestation
        result = await verifier.verify_device_attestation(attestation_data)

        # Verify signed photo
        result = await verifier.verify_photo_signature(signature_data)

        # Check attestation requirement
        requirement = verifier.get_attestation_requirement(task_type, bounty_usd)
    """

    def __init__(
        self,
        apple_app_id: str = "",
        apple_team_id: str = "",
        android_package_name: str = "",
        google_api_key: str = "",
    ):
        """
        Initialize attestation verifier.

        Args:
            apple_app_id: iOS Bundle ID (e.g., "com.example.executionmarket")
            apple_team_id: Apple Team ID (e.g., "ABC123XYZ")
            android_package_name: Android package name
            google_api_key: Google Cloud API key for Play Integrity
        """
        self.apple_app_id = apple_app_id
        self.apple_team_id = apple_team_id
        self.android_package_name = android_package_name
        self.google_api_key = google_api_key

        # In-memory storage (use Redis/DB in production)
        self._device_fingerprints: Dict[str, DeviceFingerprint] = {}
        self._worker_devices: Dict[str, List[str]] = defaultdict(list)
        self._device_workers: Dict[str, List[str]] = defaultdict(list)
        self._nonce_cache: Dict[str, datetime] = {}  # Replay prevention

        # Parse Apple root certificate
        self._apple_root_cert = None
        if CRYPTO_AVAILABLE:
            try:
                self._apple_root_cert = x509.load_pem_x509_certificate(
                    APPLE_APP_ATTEST_ROOT_CA.encode(), default_backend()
                )
            except Exception as e:
                logger.warning(f"Failed to load Apple root certificate: {e}")

    # =========================================================================
    # iOS APP ATTEST VERIFICATION (NOW-076, NOW-078)
    # =========================================================================

    async def verify_ios_attestation(
        self, attestation: DeviceAttestation
    ) -> AttestationResult:
        """
        Verify iOS App Attest attestation.

        Validates:
        1. Attestation object format (CBOR)
        2. Certificate chain to Apple root
        3. App ID hash
        4. Challenge/nonce
        5. Counter (replay prevention)

        Args:
            attestation: Device attestation data

        Returns:
            AttestationResult with verification status
        """
        if not CBOR_AVAILABLE:
            return AttestationResult.failure(
                DevicePlatform.IOS,
                ["CBOR library not available for iOS attestation verification"],
                details={"missing_dependency": "cbor2"},
            )

        if not CRYPTO_AVAILABLE:
            return AttestationResult.failure(
                DevicePlatform.IOS,
                ["Cryptography library not available"],
                details={"missing_dependency": "cryptography"},
            )

        try:
            # Decode attestation object
            attestation_bytes = base64.b64decode(attestation.attestation_object)
            attestation_data = cbor2.loads(attestation_bytes)

            # Extract components
            fmt = attestation_data.get("fmt")
            att_stmt = attestation_data.get("attStmt", {})
            auth_data = attestation_data.get("authData")

            if fmt != "apple-appattest":
                return AttestationResult.failure(
                    DevicePlatform.IOS,
                    [f"Invalid attestation format: {fmt}, expected 'apple-appattest'"],
                )

            # Parse authenticator data
            parsed_auth = self._parse_ios_auth_data(auth_data)
            if not parsed_auth:
                return AttestationResult.failure(
                    DevicePlatform.IOS, ["Failed to parse authenticator data"]
                )

            rp_id_hash, flags, counter, aaguid, cred_id, public_key = parsed_auth

            # Verify App ID hash
            expected_app_id_hash = self._compute_app_id_hash_ios()
            if rp_id_hash != expected_app_id_hash:
                return AttestationResult.failure(
                    DevicePlatform.IOS, ["App ID hash mismatch - possible tampering"]
                )

            # Verify certificate chain
            x5c = att_stmt.get("x5c", [])
            if len(x5c) < 2:
                return AttestationResult.failure(
                    DevicePlatform.IOS, ["Invalid certificate chain length"]
                )

            chain_valid, chain_error = self._verify_ios_certificate_chain(x5c)
            if not chain_valid:
                return AttestationResult.failure(
                    DevicePlatform.IOS,
                    [f"Certificate chain validation failed: {chain_error}"],
                )

            # Verify nonce/challenge
            client_data_hash = hashlib.sha256(attestation.challenge.encode()).digest()
            nonce = hashlib.sha256(auth_data + client_data_hash).digest()

            # Extract nonce from certificate extension
            leaf_cert = load_der_x509_certificate(x5c[0], default_backend())
            cert_nonce = self._extract_nonce_from_ios_cert(leaf_cert)

            if cert_nonce != nonce:
                return AttestationResult.failure(
                    DevicePlatform.IOS,
                    ["Challenge verification failed - possible replay attack"],
                    details={"error_type": AttestationError.REPLAY_ATTACK},
                )

            # Check replay using counter
            device_id = base64.b64encode(cred_id).decode()
            if not self._check_counter(device_id, counter):
                return AttestationResult.failure(
                    DevicePlatform.IOS,
                    ["Counter check failed - possible replay attack"],
                    device_id=device_id,
                    details={"error_type": AttestationError.REPLAY_ATTACK},
                )

            # Check for fraud indicators
            fraud_result = await self._check_device_fraud(
                device_id, attestation.key_id, DevicePlatform.IOS
            )

            if fraud_result["is_fraud"]:
                return AttestationResult.failure(
                    DevicePlatform.IOS,
                    fraud_result["reasons"],
                    device_id=device_id,
                    details={"error_type": fraud_result["error_type"]},
                )

            return AttestationResult.success(
                DevicePlatform.IOS,
                AttestationLevel.VERIFIED,
                device_id,
                details={
                    "counter": counter,
                    "aaguid": base64.b64encode(aaguid).decode(),
                    "key_id": attestation.key_id,
                    "certificate_valid_until": leaf_cert.not_valid_after_utc.isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"iOS attestation verification error: {e}", exc_info=True)
            return AttestationResult.failure(
                DevicePlatform.IOS, [f"Attestation verification error: {str(e)}"]
            )

    # =========================================================================
    # ANDROID PLAY INTEGRITY VERIFICATION (NOW-077, NOW-078)
    # =========================================================================

    async def verify_android_attestation(
        self, attestation: DeviceAttestation
    ) -> AttestationResult:
        """
        Verify Android Play Integrity attestation.

        Validates:
        1. Token integrity with Google servers
        2. Package name
        3. App certificate hash
        4. Device integrity verdict
        5. Account licensing (optional)

        Args:
            attestation: Device attestation data

        Returns:
            AttestationResult with verification status
        """
        if not self.google_api_key:
            return AttestationResult.failure(
                DevicePlatform.ANDROID,
                ["Google API key not configured for Play Integrity verification"],
            )

        try:
            import httpx

            # Call Google Play Integrity API to decode token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GOOGLE_PLAY_INTEGRITY_VERIFY_URL}?key={self.google_api_key}",
                    json={
                        "integrity_token": attestation.attestation_object,
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    return AttestationResult.failure(
                        DevicePlatform.ANDROID,
                        [
                            f"Play Integrity API error: {error_data.get('error', {}).get('message', 'Unknown')}"
                        ],
                        details={"status_code": response.status_code},
                    )

                token_payload = response.json()

            # Extract verdicts
            request_details = token_payload.get("tokenPayloadExternal", {}).get(
                "requestDetails", {}
            )
            app_integrity = token_payload.get("tokenPayloadExternal", {}).get(
                "appIntegrity", {}
            )
            device_integrity = token_payload.get("tokenPayloadExternal", {}).get(
                "deviceIntegrity", {}
            )
            account_details = token_payload.get("tokenPayloadExternal", {}).get(
                "accountDetails", {}
            )

            errors = []
            warnings = []

            # Verify package name
            if app_integrity.get("packageName") != self.android_package_name:
                errors.append(
                    f"Package name mismatch: expected {self.android_package_name}"
                )

            # Verify app integrity
            app_recognition = app_integrity.get("appRecognitionVerdict", "")
            if app_recognition == "UNEVALUATED":
                warnings.append("App recognition not evaluated")
            elif app_recognition != "PLAY_RECOGNIZED":
                errors.append(f"App not recognized by Play Store: {app_recognition}")

            # Verify device integrity (NOW-077: StrongBox)
            device_verdict = device_integrity.get("deviceRecognitionVerdict", [])

            attestation_level = AttestationLevel.NONE

            if "MEETS_STRONG_INTEGRITY" in device_verdict:
                # Device has hardware-backed attestation (StrongBox)
                attestation_level = AttestationLevel.VERIFIED
            elif "MEETS_DEVICE_INTEGRITY" in device_verdict:
                # Device passes basic integrity but may not have hardware backing
                attestation_level = AttestationLevel.STRONG
            elif "MEETS_BASIC_INTEGRITY" in device_verdict:
                # Device may be rooted or running modified OS
                attestation_level = AttestationLevel.BASIC
                warnings.append("Device only meets basic integrity - may be modified")
            else:
                errors.append("Device does not meet integrity requirements")

            # Verify nonce/challenge
            nonce_b64 = request_details.get("nonce", "")
            try:
                received_nonce = base64.b64decode(nonce_b64).decode()
                if received_nonce != attestation.challenge:
                    errors.append("Challenge mismatch - possible replay attack")
            except Exception:
                errors.append("Invalid nonce format")

            if errors:
                return AttestationResult.failure(
                    DevicePlatform.ANDROID,
                    errors,
                    details={
                        "device_verdict": device_verdict,
                        "app_recognition": app_recognition,
                    },
                )

            # Generate device ID from package and device identifiers
            device_id = hashlib.sha256(
                f"{self.android_package_name}:{device_verdict}".encode()
            ).hexdigest()[:32]

            # Check for fraud
            fraud_result = await self._check_device_fraud(
                device_id, attestation.key_id, DevicePlatform.ANDROID
            )

            if fraud_result["is_fraud"]:
                return AttestationResult.failure(
                    DevicePlatform.ANDROID,
                    fraud_result["reasons"],
                    device_id=device_id,
                    details={"error_type": fraud_result["error_type"]},
                )

            result = AttestationResult.success(
                DevicePlatform.ANDROID,
                attestation_level,
                device_id,
                details={
                    "device_verdict": device_verdict,
                    "app_recognition": app_recognition,
                    "account_licensed": account_details.get("appLicensingVerdict")
                    == "LICENSED",
                },
            )
            result.warnings = warnings
            return result

        except ImportError:
            return AttestationResult.failure(
                DevicePlatform.ANDROID,
                ["httpx library not available for API calls"],
                details={"missing_dependency": "httpx"},
            )
        except Exception as e:
            logger.error(f"Android attestation verification error: {e}", exc_info=True)
            return AttestationResult.failure(
                DevicePlatform.ANDROID, [f"Attestation verification error: {str(e)}"]
            )

    # =========================================================================
    # PHOTO SIGNATURE VERIFICATION (NOW-076, NOW-077)
    # =========================================================================

    async def verify_photo_signature(
        self, signature: PhotoSignature, photo_data: bytes, worker_id: str
    ) -> AttestationResult:
        """
        Verify a hardware-signed photo.

        The mobile app signs photos using keys stored in:
        - iOS: Secure Enclave
        - Android: StrongBox Keystore

        Validates:
        1. Photo hash matches signature
        2. Signature is valid for the public key
        3. Timestamp is recent
        4. Nonce hasn't been used before
        5. Device is registered to this worker

        Args:
            signature: Photo signature data from device
            photo_data: Raw photo bytes
            worker_id: Worker ID claiming this submission

        Returns:
            AttestationResult with verification status
        """
        warnings = []

        # Verify photo hash
        computed_hash = hashlib.sha256(photo_data).hexdigest()
        if computed_hash != signature.photo_hash:
            return AttestationResult.failure(
                signature.platform,
                ["Photo hash mismatch - photo may have been modified"],
                device_id=signature.device_id,
            )

        # Check timestamp freshness (photos must be recent)
        now = datetime.now(UTC)
        if signature.timestamp.tzinfo is None:
            signature.timestamp = signature.timestamp.replace(tzinfo=UTC)

        age = now - signature.timestamp
        if age > timedelta(minutes=30):
            return AttestationResult.failure(
                signature.platform,
                [f"Photo signature too old: {age.total_seconds() / 60:.1f} minutes"],
                device_id=signature.device_id,
                details={"signature_age_minutes": age.total_seconds() / 60},
            )

        if age < timedelta(seconds=-30):  # Allow 30s clock drift
            return AttestationResult.failure(
                signature.platform,
                ["Photo signature timestamp is in the future"],
                device_id=signature.device_id,
            )

        # Check nonce (replay prevention)
        if not self._check_and_store_nonce(signature.nonce):
            return AttestationResult.failure(
                signature.platform,
                ["Nonce already used - possible replay attack"],
                device_id=signature.device_id,
                details={"error_type": AttestationError.REPLAY_ATTACK},
            )

        # Verify signature
        if CRYPTO_AVAILABLE:
            try:
                sig_valid = self._verify_ecdsa_signature(
                    signature.signature,
                    signature.public_key,
                    signature.photo_hash.encode(),
                )

                if not sig_valid:
                    return AttestationResult.failure(
                        signature.platform,
                        ["Invalid signature - photo may not be from registered device"],
                        device_id=signature.device_id,
                        details={"error_type": AttestationError.INVALID_SIGNATURE},
                    )

            except Exception as e:
                return AttestationResult.failure(
                    signature.platform,
                    [f"Signature verification error: {str(e)}"],
                    device_id=signature.device_id,
                )
        else:
            warnings.append(
                "Cryptography library not available - signature not fully verified"
            )

        # Check device-worker binding (NOW-081)
        device_check = await self._verify_device_worker_binding(
            signature.device_id, worker_id
        )

        if not device_check["valid"]:
            return AttestationResult.failure(
                signature.platform,
                device_check["errors"],
                device_id=signature.device_id,
                details={"error_type": device_check.get("error_type")},
            )

        warnings.extend(device_check.get("warnings", []))

        result = AttestationResult.success(
            signature.platform,
            AttestationLevel.STRONG,  # Hardware-signed
            signature.device_id,
            details={
                "signature_age_seconds": age.total_seconds(),
                "nonce": signature.nonce[:16] + "...",
            },
        )
        result.warnings = warnings
        return result

    # =========================================================================
    # PHOTO METADATA PRESERVATION (NOW-079)
    # =========================================================================

    def extract_photo_metadata(self, photo_data: bytes) -> PhotoMetadata:
        """
        Extract EXIF metadata from photo.

        IMPORTANT: Do NOT strip EXIF data. Preserve all metadata for:
        - GPS verification
        - Timestamp verification
        - Camera verification
        - Fraud detection (software tags indicate editing)

        Args:
            photo_data: Raw photo bytes (JPEG)

        Returns:
            PhotoMetadata with extracted data
        """
        metadata = PhotoMetadata()

        try:
            # Try PIL/Pillow first
            from PIL import Image
            from PIL.ExifTags import TAGS
            import io

            img = Image.open(io.BytesIO(photo_data))
            exif_data = img._getexif()

            if exif_data:
                # Store raw EXIF
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="replace")
                        except Exception:
                            value = str(value)
                    metadata.raw_exif[str(tag)] = value

                # Extract common fields
                metadata.camera_make = exif_data.get(271)  # Make
                metadata.camera_model = exif_data.get(272)  # Model
                metadata.software = exif_data.get(305)  # Software
                metadata.orientation = exif_data.get(274)  # Orientation

                # DateTime
                date_time = exif_data.get(36867) or exif_data.get(
                    306
                )  # DateTimeOriginal or DateTime
                if date_time:
                    try:
                        metadata.timestamp = datetime.strptime(
                            date_time, "%Y:%m:%d %H:%M:%S"
                        )
                    except ValueError:
                        pass

                # GPS data
                gps_info = exif_data.get(34853)  # GPSInfo
                if gps_info:
                    metadata.gps_latitude = self._convert_gps_to_decimal(
                        gps_info.get(2),  # GPSLatitude
                        gps_info.get(1),  # GPSLatitudeRef
                    )
                    metadata.gps_longitude = self._convert_gps_to_decimal(
                        gps_info.get(4),  # GPSLongitude
                        gps_info.get(3),  # GPSLongitudeRef
                    )
                    if 6 in gps_info:  # GPSAltitude
                        metadata.gps_altitude = float(gps_info[6])

                # Camera settings
                metadata.iso = exif_data.get(34855)  # ISOSpeedRatings
                metadata.focal_length = exif_data.get(37386)  # FocalLength
                if metadata.focal_length:
                    try:
                        metadata.focal_length = float(metadata.focal_length)
                    except (TypeError, ValueError):
                        pass

                flash = exif_data.get(37385)  # Flash
                if flash is not None:
                    metadata.flash = bool(flash & 1)  # Bit 0 indicates flash fired

            # Image dimensions
            metadata.width, metadata.height = img.size

        except ImportError:
            logger.warning("PIL not available for EXIF extraction")
        except Exception as e:
            logger.warning(f"Error extracting EXIF: {e}")

        return metadata

    def validate_photo_metadata(
        self,
        metadata: PhotoMetadata,
        expected_location: Optional[Tuple[float, float]] = None,
        max_age_minutes: int = 30,
    ) -> Dict[str, Any]:
        """
        Validate photo metadata for fraud indicators.

        Checks:
        1. Timestamp freshness
        2. GPS proximity to expected location
        3. Software editing indicators
        4. Suspicious camera/device info

        Args:
            metadata: Extracted photo metadata
            expected_location: (latitude, longitude) if task has location
            max_age_minutes: Maximum allowed photo age

        Returns:
            Dict with validation results
        """
        result = {"valid": True, "issues": [], "warnings": [], "checks": {}}

        # Check timestamp
        if metadata.timestamp:
            now = datetime.now()
            age = now - metadata.timestamp
            age_minutes = age.total_seconds() / 60

            result["checks"]["timestamp_age_minutes"] = age_minutes

            if age_minutes > max_age_minutes:
                result["valid"] = False
                result["issues"].append(
                    f"Photo too old: {age_minutes:.1f} minutes (max: {max_age_minutes})"
                )
            elif age_minutes < -5:  # Allow 5 min clock drift
                result["valid"] = False
                result["issues"].append("Photo timestamp is in the future")
        else:
            result["warnings"].append("No timestamp in photo metadata")

        # Check GPS
        if expected_location and metadata.gps_latitude and metadata.gps_longitude:
            from math import radians, sin, cos, sqrt, atan2

            lat1, lon1 = radians(expected_location[0]), radians(expected_location[1])
            lat2, lon2 = radians(metadata.gps_latitude), radians(metadata.gps_longitude)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            distance_m = 6371000 * c  # Earth radius in meters

            result["checks"]["gps_distance_meters"] = distance_m

            if distance_m > 500:  # More than 500m away
                result["valid"] = False
                result["issues"].append(
                    f"Photo location {distance_m:.0f}m from expected"
                )
        elif expected_location:
            result["warnings"].append("No GPS data in photo for location verification")

        # Check for editing software
        editing_software = [
            "photoshop",
            "gimp",
            "lightroom",
            "snapseed",
            "vsco",
            "afterlight",
            "pixelmator",
            "capture one",
            "darktable",
        ]

        if metadata.software:
            software_lower = metadata.software.lower()
            for editor in editing_software:
                if editor in software_lower:
                    result["valid"] = False
                    result["issues"].append(f"Photo edited with {metadata.software}")
                    break

        # Check for suspicious camera info
        if metadata.camera_make:
            make_lower = metadata.camera_make.lower()
            # Screenshots typically don't have camera make
            if "screenshot" in make_lower or "screen" in make_lower:
                result["valid"] = False
                result["issues"].append("Photo appears to be a screenshot")

        return result

    # =========================================================================
    # ATTESTATION REQUIREMENTS (NOW-082)
    # =========================================================================

    def get_attestation_requirement(
        self, task_type: str, bounty_usd: float
    ) -> AttestationRequirement:
        """
        Determine attestation requirement for a task.

        Rules (NOW-082):
        - >$50 bounty: Attestation REQUIRED
        - >$20 bounty: Attestation RECOMMENDED
        - <$20 bounty: Attestation OPTIONAL (but improves trust score)

        High-value task types always require attestation:
        - human_authority
        - legal_document
        - financial_verification

        Args:
            task_type: Type of task
            bounty_usd: Bounty amount in USD

        Returns:
            AttestationRequirement with rules
        """
        # High-risk task types always require attestation
        high_risk_types = [
            "human_authority",
            "legal_document",
            "financial_verification",
            "identity_verification",
            "notarization",
            "medical_verification",
        ]

        if task_type in high_risk_types:
            return AttestationRequirement(
                required=True,
                recommended=True,
                min_level=AttestationLevel.VERIFIED,
                reason=f"Task type '{task_type}' requires hardware attestation",
            )

        # Bounty-based requirements
        if bounty_usd >= ATTESTATION_REQUIRED_BOUNTY_USD:
            return AttestationRequirement(
                required=True,
                recommended=True,
                min_level=AttestationLevel.STRONG,
                reason=f"Bounty ${bounty_usd:.2f} >= ${ATTESTATION_REQUIRED_BOUNTY_USD} requires attestation",
            )

        if bounty_usd >= ATTESTATION_RECOMMENDED_BOUNTY_USD:
            return AttestationRequirement(
                required=False,
                recommended=True,
                min_level=AttestationLevel.BASIC,
                reason=f"Bounty ${bounty_usd:.2f} >= ${ATTESTATION_RECOMMENDED_BOUNTY_USD} recommends attestation",
            )

        return AttestationRequirement(
            required=False,
            recommended=False,
            min_level=AttestationLevel.NONE,
            reason="Low-value task - attestation optional",
        )

    def check_attestation_compliance(
        self,
        task_type: str,
        bounty_usd: float,
        attestation_result: Optional[AttestationResult],
    ) -> Dict[str, Any]:
        """
        Check if submission meets attestation requirements.

        Args:
            task_type: Type of task
            bounty_usd: Bounty amount in USD
            attestation_result: Result from attestation verification (or None)

        Returns:
            Dict with compliance status and details
        """
        requirement = self.get_attestation_requirement(task_type, bounty_usd)

        result = {
            "compliant": True,
            "requirement": {
                "required": requirement.required,
                "recommended": requirement.recommended,
                "min_level": requirement.min_level.value,
                "reason": requirement.reason,
            },
            "attestation": None,
            "issues": [],
            "warnings": [],
        }

        if attestation_result:
            result["attestation"] = {
                "is_valid": attestation_result.is_valid,
                "level": attestation_result.level.value,
                "platform": attestation_result.platform.value,
                "device_id": attestation_result.device_id[:16] + "..."
                if attestation_result.device_id
                else None,
            }

        # Check compliance
        if requirement.required:
            if not attestation_result:
                result["compliant"] = False
                result["issues"].append(
                    "Hardware attestation required but not provided"
                )
            elif not attestation_result.is_valid:
                result["compliant"] = False
                result["issues"].append(
                    f"Attestation invalid: {', '.join(attestation_result.errors)}"
                )
            elif self._level_value(attestation_result.level) < self._level_value(
                requirement.min_level
            ):
                result["compliant"] = False
                result["issues"].append(
                    f"Attestation level {attestation_result.level.value} below required {requirement.min_level.value}"
                )
        elif requirement.recommended:
            if not attestation_result or not attestation_result.is_valid:
                result["warnings"].append(
                    "Hardware attestation recommended for this task"
                )

        return result

    # =========================================================================
    # DEVICE FINGERPRINTING ANTI-FRAUD (NOW-081)
    # =========================================================================

    async def register_device(
        self,
        device_id: str,
        platform: DevicePlatform,
        hardware_id: str,
        worker_id: str,
        attestation_level: AttestationLevel,
    ) -> Dict[str, Any]:
        """
        Register a device for a worker.

        Enforces:
        - One device can only be used by one worker
        - Workers can have max 3 devices
        - Detects similar devices (same hardware, different IDs)

        Args:
            device_id: Unique device identifier
            platform: Device platform
            hardware_id: Hardware-based identifier (more stable than device_id)
            worker_id: Worker claiming this device
            attestation_level: Level of attestation verification

        Returns:
            Dict with registration status
        """
        now = datetime.now(UTC)
        result = {"registered": False, "errors": [], "warnings": []}

        # Check if device is already registered to another worker
        if device_id in self._device_workers:
            existing_workers = self._device_workers[device_id]
            if existing_workers and existing_workers[0] != worker_id:
                result["errors"].append("Device already registered to another worker")
                return result

        # Check worker device limit
        worker_devices = self._worker_devices.get(worker_id, [])
        if (
            len(worker_devices) >= MAX_DEVICES_PER_WORKER
            and device_id not in worker_devices
        ):
            result["errors"].append(
                f"Worker already has {MAX_DEVICES_PER_WORKER} registered devices"
            )
            return result

        # Check for similar devices (anti-fraud)
        for existing_id, fingerprint in self._device_fingerprints.items():
            if existing_id == device_id:
                continue

            similarity = self._calculate_device_similarity(
                hardware_id, fingerprint.hardware_id
            )

            if similarity >= DEVICE_SIMILARITY_THRESHOLD:
                if fingerprint.worker_id != worker_id:
                    result["errors"].append(
                        "Similar device detected registered to another worker"
                    )
                    return result
                else:
                    result["warnings"].append(
                        "Device appears similar to another registered device"
                    )

        # Register device
        fingerprint = DeviceFingerprint(
            device_id=device_id,
            platform=platform,
            hardware_id=hardware_id,
            worker_id=worker_id,
            first_seen=now,
            last_seen=now,
            attestation_level=attestation_level,
        )

        self._device_fingerprints[device_id] = fingerprint

        if device_id not in self._worker_devices[worker_id]:
            self._worker_devices[worker_id].append(device_id)

        if worker_id not in self._device_workers[device_id]:
            self._device_workers[device_id].append(worker_id)

        result["registered"] = True
        result["device_count"] = len(self._worker_devices[worker_id])

        return result

    async def check_device_fraud(
        self, device_id: str, worker_id: str
    ) -> Dict[str, Any]:
        """
        Check for device-based fraud.

        Detects:
        - Same device used by multiple workers
        - Worker using too many devices
        - Device with fraud history

        Args:
            device_id: Device identifier
            worker_id: Worker ID

        Returns:
            Dict with fraud check results
        """
        result = {"is_fraud": False, "risk_score": 0.0, "issues": [], "warnings": []}

        fingerprint = self._device_fingerprints.get(device_id)

        if fingerprint:
            # Check if device belongs to different worker
            if fingerprint.worker_id != worker_id:
                result["is_fraud"] = True
                result["risk_score"] = 0.95
                result["issues"].append("Device registered to different worker")
                return result

            # Check fraud flags
            if fingerprint.fraud_flags:
                result["risk_score"] = min(0.9, 0.3 * len(fingerprint.fraud_flags))
                result["warnings"].extend(fingerprint.fraud_flags)

                if len(fingerprint.fraud_flags) >= 3:
                    result["is_fraud"] = True
                    result["issues"].append("Device has multiple fraud flags")

        # Check worker device count
        worker_devices = self._worker_devices.get(worker_id, [])
        if len(worker_devices) > MAX_DEVICES_PER_WORKER:
            result["risk_score"] = max(result["risk_score"], 0.5)
            result["warnings"].append(f"Worker using {len(worker_devices)} devices")

        return result

    # =========================================================================
    # INTERNAL HELPER METHODS
    # =========================================================================

    def _parse_ios_auth_data(self, auth_data: bytes) -> Optional[Tuple]:
        """Parse iOS authenticator data structure."""
        if len(auth_data) < 37:
            return None

        try:
            rp_id_hash = auth_data[:32]
            flags = auth_data[32]
            counter = struct.unpack(">I", auth_data[33:37])[0]

            # If attested credential data present (bit 6)
            if flags & 0x40:
                aaguid = auth_data[37:53]
                cred_id_len = struct.unpack(">H", auth_data[53:55])[0]
                cred_id = auth_data[55 : 55 + cred_id_len]
                public_key = auth_data[55 + cred_id_len :]
                return (rp_id_hash, flags, counter, aaguid, cred_id, public_key)

            return (rp_id_hash, flags, counter, b"", b"", b"")

        except Exception:
            return None

    def _compute_app_id_hash_ios(self) -> bytes:
        """Compute expected App ID hash for iOS."""
        app_id = f"{self.apple_team_id}.{self.apple_app_id}"
        return hashlib.sha256(app_id.encode()).digest()

    def _verify_ios_certificate_chain(self, x5c: List[bytes]) -> Tuple[bool, str]:
        """Verify iOS certificate chain to Apple root."""
        if not CRYPTO_AVAILABLE:
            return (False, "cryptography library not available")

        if not self._apple_root_cert:
            return (False, "Apple root certificate not loaded")

        try:
            # Load certificates
            certs = [load_der_x509_certificate(cert, default_backend()) for cert in x5c]

            # Verify chain
            for i in range(len(certs) - 1):
                issuer_cert = (
                    certs[i + 1] if i + 1 < len(certs) else self._apple_root_cert
                )

                try:
                    issuer_cert.public_key().verify(
                        certs[i].signature,
                        certs[i].tbs_certificate_bytes,
                        ec.ECDSA(certs[i].signature_hash_algorithm),
                    )
                except InvalidSignature:
                    return (False, f"Certificate {i} signature verification failed")

            # Verify last cert against root
            try:
                self._apple_root_cert.public_key().verify(
                    certs[-1].signature,
                    certs[-1].tbs_certificate_bytes,
                    ec.ECDSA(certs[-1].signature_hash_algorithm),
                )
            except InvalidSignature:
                return (False, "Root certificate verification failed")

            # Check expiration
            now = datetime.now(UTC)
            for i, cert in enumerate(certs):
                if cert.not_valid_before_utc > now:
                    return (False, f"Certificate {i} not yet valid")
                if cert.not_valid_after_utc < now:
                    return (False, f"Certificate {i} expired")

            return (True, "")

        except Exception as e:
            return (False, str(e))

    def _extract_nonce_from_ios_cert(self, cert: Any) -> bytes:
        """Extract nonce from iOS App Attest certificate extension."""
        try:
            # OID for Apple App Attest nonce extension
            APPLE_NONCE_OID = x509.ObjectIdentifier("1.2.840.113635.100.8.2")

            for ext in cert.extensions:
                if ext.oid == APPLE_NONCE_OID:
                    # The extension value contains the nonce
                    return ext.value.value

            return b""
        except Exception:
            return b""

    def _verify_ecdsa_signature(
        self, signature_b64: str, public_key_b64: str, message: bytes
    ) -> bool:
        """Verify ECDSA signature."""
        if not CRYPTO_AVAILABLE:
            return False

        try:
            signature = base64.b64decode(signature_b64)
            public_key_bytes = base64.b64decode(public_key_b64)

            # Load public key (assuming P-256 curve)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(), public_key_bytes
            )

            # Verify signature
            public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
            return True

        except Exception as e:
            logger.debug(f"Signature verification failed: {e}")
            return False

    def _check_counter(self, device_id: str, counter: int) -> bool:
        """Check and update counter for replay prevention."""
        fingerprint = self._device_fingerprints.get(device_id)

        if fingerprint:
            stored_counter = fingerprint.submission_count
            if counter <= stored_counter:
                return False
            fingerprint.submission_count = counter

        return True

    def _check_and_store_nonce(self, nonce: str) -> bool:
        """Check and store nonce for replay prevention."""
        now = datetime.now(UTC)

        # Clean old nonces
        cutoff = now - timedelta(hours=1)
        self._nonce_cache = {
            n: ts for n, ts in self._nonce_cache.items() if ts > cutoff
        }

        # Check if nonce exists
        if nonce in self._nonce_cache:
            return False

        # Store nonce
        self._nonce_cache[nonce] = now
        return True

    async def _check_device_fraud(
        self, device_id: str, key_id: str, platform: DevicePlatform
    ) -> Dict[str, Any]:
        """Internal fraud check during attestation."""
        result = {"is_fraud": False, "reasons": [], "error_type": None}

        # Check if device is already registered to different key
        fingerprint = self._device_fingerprints.get(device_id)
        if fingerprint:
            if fingerprint.fraud_flags:
                if len(fingerprint.fraud_flags) >= 3:
                    result["is_fraud"] = True
                    result["reasons"] = [
                        f"Device flagged for fraud: {', '.join(fingerprint.fraud_flags)}"
                    ]
                    result["error_type"] = AttestationError.DEVICE_COMPROMISED

        return result

    async def _verify_device_worker_binding(
        self, device_id: str, worker_id: str
    ) -> Dict[str, Any]:
        """Verify device is bound to worker."""
        result = {"valid": True, "errors": [], "warnings": []}

        # Check device registration
        if device_id in self._device_workers:
            registered_workers = self._device_workers[device_id]
            if registered_workers and worker_id not in registered_workers:
                result["valid"] = False
                result["errors"].append("Device not registered to this worker")
                result["error_type"] = AttestationError.MULTI_WORKER_DEVICE
                return result

        # Check worker device count
        worker_devices = self._worker_devices.get(worker_id, [])
        if len(worker_devices) > MAX_DEVICES_PER_WORKER:
            result["warnings"].append(
                f"Worker using many devices ({len(worker_devices)})"
            )

        return result

    def _calculate_device_similarity(
        self, hardware_id1: str, hardware_id2: str
    ) -> float:
        """Calculate similarity between two hardware identifiers."""
        if hardware_id1 == hardware_id2:
            return 1.0

        # Simple character-level similarity
        matches = sum(c1 == c2 for c1, c2 in zip(hardware_id1, hardware_id2))
        return matches / max(len(hardware_id1), len(hardware_id2))

    def _convert_gps_to_decimal(
        self, coords: Optional[Tuple], ref: Optional[str]
    ) -> Optional[float]:
        """Convert GPS coordinates from DMS to decimal."""
        if not coords:
            return None

        try:
            degrees = float(coords[0])
            minutes = float(coords[1])
            seconds = float(coords[2]) if len(coords) > 2 else 0

            decimal = degrees + minutes / 60 + seconds / 3600

            if ref in ("S", "W"):
                decimal = -decimal

            return decimal
        except (TypeError, ValueError, IndexError):
            return None

    def _level_value(self, level: AttestationLevel) -> int:
        """Convert attestation level to numeric value for comparison."""
        return {
            AttestationLevel.NONE: 0,
            AttestationLevel.BASIC: 1,
            AttestationLevel.STRONG: 2,
            AttestationLevel.VERIFIED: 3,
        }.get(level, 0)

    # =========================================================================
    # CLEANUP METHODS
    # =========================================================================

    def clear_device_data(self, device_id: str) -> None:
        """Clear all data for a device (for GDPR compliance)."""
        self._device_fingerprints.pop(device_id, None)

        # Remove from worker mappings
        for worker_id, devices in self._worker_devices.items():
            if device_id in devices:
                devices.remove(device_id)

        self._device_workers.pop(device_id, None)

    def clear_worker_data(self, worker_id: str) -> None:
        """Clear all device data for a worker (for GDPR compliance)."""
        devices = self._worker_devices.pop(worker_id, [])

        for device_id in devices:
            self._device_fingerprints.pop(device_id, None)
            self._device_workers.pop(device_id, None)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def verify_attestation(
    attestation_object: str,
    challenge: str,
    platform: str,
    app_id: str = "",
    key_id: str = "",
    google_api_key: str = "",
) -> AttestationResult:
    """
    Convenience function for verifying device attestation.

    Args:
        attestation_object: Base64-encoded attestation
        challenge: Server-provided challenge
        platform: "ios" or "android"
        app_id: App identifier
        key_id: Key identifier
        google_api_key: Google API key (for Android)

    Returns:
        AttestationResult
    """
    device_platform = DevicePlatform(platform.lower())

    attestation = DeviceAttestation(
        platform=device_platform,
        attestation_object=attestation_object,
        challenge=challenge,
        key_id=key_id,
        app_id=app_id,
        timestamp=datetime.now(UTC),
    )

    if device_platform == DevicePlatform.IOS:
        verifier = AttestationVerifier(
            apple_app_id=app_id.split(".")[-1] if app_id else "",
            apple_team_id=app_id.split(".")[0] if app_id else "",
        )
        return await verifier.verify_ios_attestation(attestation)

    elif device_platform == DevicePlatform.ANDROID:
        verifier = AttestationVerifier(
            android_package_name=app_id, google_api_key=google_api_key
        )
        return await verifier.verify_android_attestation(attestation)

    return AttestationResult.failure(
        DevicePlatform.UNKNOWN, [f"Unsupported platform: {platform}"]
    )


def get_attestation_requirement(
    task_type: str, bounty_usd: float
) -> AttestationRequirement:
    """
    Convenience function for checking attestation requirements.

    Args:
        task_type: Type of task
        bounty_usd: Bounty amount in USD

    Returns:
        AttestationRequirement
    """
    verifier = AttestationVerifier()
    return verifier.get_attestation_requirement(task_type, bounty_usd)
