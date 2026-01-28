"""
Safety Pre-Investigation (NOW-112)

Analyzes task locations for safety risks before assignment.

Features:
- Crime data integration (placeholder for external APIs)
- Time of day risk assessment
- Private property detection
- Weather hazard checks
- Accessibility analysis
- Location history and incident tracking

This module helps protect workers by:
1. Warning about high-risk locations
2. Recommending safer time windows
3. Flagging private property that may require permission
4. Providing actionable safety recommendations
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, UTC
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class SafetyRisk(str, Enum):
    """Overall safety risk level for a location/task."""
    LOW = "low"           # Safe to proceed
    MEDIUM = "medium"     # Proceed with caution
    HIGH = "high"         # Additional precautions required
    RESTRICTED = "restricted"  # Do not proceed without special approval


class RiskFactor(str, Enum):
    """Individual risk factors that contribute to safety assessment."""
    CRIME_RATE = "crime_rate"              # Local crime statistics
    TIME_OF_DAY = "time_of_day"            # Night/early morning risks
    PRIVATE_PROPERTY = "private_property"  # Access restrictions
    WEATHER = "weather"                    # Weather hazards
    ACCESSIBILITY = "accessibility"        # Physical access challenges
    INCIDENT_HISTORY = "incident_history"  # Previous incidents at location
    AREA_TYPE = "area_type"                # Industrial, residential, etc.
    LIGHTING = "lighting"                  # Street lighting conditions
    EMERGENCY_ACCESS = "emergency_access"  # Distance to emergency services


class AreaType(str, Enum):
    """Type of area for the location."""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    RURAL = "rural"
    DOWNTOWN = "downtown"
    TRANSIT_HUB = "transit_hub"
    UNKNOWN = "unknown"


class WeatherRisk(str, Enum):
    """Weather-related risk levels."""
    NONE = "none"
    RAIN = "rain"
    STORM = "storm"
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"
    SNOW_ICE = "snow_ice"
    FLOODING = "flooding"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class LocationRiskData:
    """Risk data for a specific location."""
    latitude: float
    longitude: float
    crime_index: float = 0.0  # 0.0 (safest) to 1.0 (most dangerous)
    area_type: AreaType = AreaType.UNKNOWN
    has_street_lighting: bool = True
    is_private_property: bool = False
    property_owner: Optional[str] = None
    access_requirements: Optional[str] = None
    nearest_police_km: float = 0.0
    nearest_hospital_km: float = 0.0
    incident_count_90d: int = 0
    last_incident_date: Optional[datetime] = None
    known_hazards: List[str] = field(default_factory=list)


@dataclass
class SafetyAssessment:
    """Complete safety assessment for a task location."""
    task_id: str
    location: Tuple[float, float]
    overall_risk: SafetyRisk
    risk_score: float  # 0.0 (safest) to 1.0 (most dangerous)
    factors: Dict[RiskFactor, float]  # Individual factor scores
    warnings: List[str]
    recommendations: List[str]
    safe_hours: List[Tuple[int, int]]  # List of (start_hour, end_hour) ranges
    requires_approval: bool
    approval_reason: Optional[str]
    assessed_at: datetime
    expires_at: datetime  # Assessment validity period
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "location": {"lat": self.location[0], "lng": self.location[1]},
            "overall_risk": self.overall_risk.value,
            "risk_score": self.risk_score,
            "factors": {k.value: v for k, v in self.factors.items()},
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "safe_hours": self.safe_hours,
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
            "assessed_at": self.assessed_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "metadata": self.metadata,
        }


# =============================================================================
# CONSTANTS
# =============================================================================


# Time windows considered higher risk
HIGH_RISK_HOURS: List[Tuple[int, int]] = [
    (22, 24),  # 10pm - midnight
    (0, 6),    # Midnight - 6am
]

# Risk thresholds
RISK_THRESHOLD_LOW = 0.25
RISK_THRESHOLD_MEDIUM = 0.50
RISK_THRESHOLD_HIGH = 0.75

# Assessment validity in hours
ASSESSMENT_VALIDITY_HOURS = 24

# Crime index weights by area type
AREA_CRIME_MULTIPLIERS: Dict[AreaType, float] = {
    AreaType.RESIDENTIAL: 0.8,
    AreaType.COMMERCIAL: 1.0,
    AreaType.INDUSTRIAL: 1.2,
    AreaType.RURAL: 0.7,
    AreaType.DOWNTOWN: 1.1,
    AreaType.TRANSIT_HUB: 1.3,
    AreaType.UNKNOWN: 1.0,
}

# Night risk multipliers
NIGHT_RISK_MULTIPLIERS: Dict[AreaType, float] = {
    AreaType.RESIDENTIAL: 1.3,
    AreaType.COMMERCIAL: 1.5,  # Closed businesses = less foot traffic
    AreaType.INDUSTRIAL: 1.8,  # Isolated at night
    AreaType.RURAL: 1.6,
    AreaType.DOWNTOWN: 1.2,
    AreaType.TRANSIT_HUB: 1.4,
    AreaType.UNKNOWN: 1.5,
}


# =============================================================================
# SAFETY INVESTIGATOR
# =============================================================================


class SafetyInvestigator:
    """
    Pre-investigates task locations for safety risks.

    This class provides comprehensive safety assessment including:
    - Crime data analysis (via external API integration)
    - Time-of-day risk assessment
    - Private property detection
    - Weather hazard checks
    - Historical incident tracking
    - Actionable safety recommendations

    Usage:
        investigator = SafetyInvestigator()
        assessment = await investigator.assess_location(
            lat=40.7128,
            lng=-74.0060,
            task_time=datetime.now()
        )

        if assessment.overall_risk == SafetyRisk.HIGH:
            # Warn worker or require additional precautions
            pass
    """

    def __init__(
        self,
        crime_data_service: Optional[Any] = None,
        weather_service: Optional[Any] = None,
        property_service: Optional[Any] = None,
    ):
        """
        Initialize safety investigator.

        Args:
            crime_data_service: Optional service for crime data lookups.
                Should implement: async get_crime_index(lat, lng) -> float
            weather_service: Optional weather data service.
                Should implement: async get_weather_risk(lat, lng) -> WeatherRisk
            property_service: Optional property/land registry service.
                Should implement: async check_property(lat, lng) -> LocationRiskData
        """
        self.crime_data_service = crime_data_service
        self.weather_service = weather_service
        self.property_service = property_service

        # In-memory cache for location assessments
        # In production, use Redis with TTL
        self._assessment_cache: Dict[str, SafetyAssessment] = {}

        # Incident history tracking
        self._incident_history: Dict[str, List[Dict[str, Any]]] = {}

    async def assess_location(
        self,
        lat: float,
        lng: float,
        task_id: Optional[str] = None,
        task_time: Optional[datetime] = None,
        task_type: Optional[str] = None,
        force_refresh: bool = False,
    ) -> SafetyAssessment:
        """
        Perform comprehensive safety assessment for a location.

        Args:
            lat: Latitude of task location
            lng: Longitude of task location
            task_id: Optional task ID for tracking
            task_time: Planned task execution time (default: now)
            task_type: Type of task for context-specific assessment
            force_refresh: Force new assessment even if cached

        Returns:
            SafetyAssessment with risk analysis and recommendations
        """
        # Generate cache key
        cache_key = self._get_cache_key(lat, lng, task_time)

        # Check cache
        if not force_refresh and cache_key in self._assessment_cache:
            cached = self._assessment_cache[cache_key]
            if datetime.now(UTC) < cached.expires_at:
                logger.debug(f"Using cached safety assessment for {lat}, {lng}")
                return cached

        # Use current time if not specified
        if task_time is None:
            task_time = datetime.now(UTC)
        elif task_time.tzinfo is None:
            task_time = task_time.replace(tzinfo=UTC)

        # Generate task ID if not provided
        if task_id is None:
            task_id = f"safety_{hashlib.md5(f'{lat}:{lng}'.encode()).hexdigest()[:8]}"

        # Collect risk factors
        factors: Dict[RiskFactor, float] = {}
        warnings: List[str] = []
        recommendations: List[str] = []

        # 1. Get location risk data
        location_data = await self._get_location_data(lat, lng)

        # 2. Assess crime risk
        crime_score, crime_warnings = await self._assess_crime_risk(location_data)
        factors[RiskFactor.CRIME_RATE] = crime_score
        warnings.extend(crime_warnings)

        # 3. Assess time-of-day risk
        time_score, time_warnings, safe_hours = self.check_time_risk(
            task_time, location_data.area_type
        )
        factors[RiskFactor.TIME_OF_DAY] = time_score
        warnings.extend(time_warnings)

        # 4. Assess private property
        property_score, property_warnings = self._assess_property_risk(location_data)
        factors[RiskFactor.PRIVATE_PROPERTY] = property_score
        warnings.extend(property_warnings)

        # 5. Assess weather (if service available)
        weather_score, weather_warnings = await self._assess_weather_risk(lat, lng)
        factors[RiskFactor.WEATHER] = weather_score
        warnings.extend(weather_warnings)

        # 6. Assess accessibility
        access_score, access_warnings = self._assess_accessibility(location_data)
        factors[RiskFactor.ACCESSIBILITY] = access_score
        warnings.extend(access_warnings)

        # 7. Check incident history
        incident_score, incident_warnings = self._assess_incident_history(lat, lng)
        factors[RiskFactor.INCIDENT_HISTORY] = incident_score
        warnings.extend(incident_warnings)

        # 8. Assess lighting conditions
        lighting_score = self._assess_lighting(location_data, task_time)
        factors[RiskFactor.LIGHTING] = lighting_score

        # 9. Assess emergency service proximity
        emergency_score = self._assess_emergency_access(location_data)
        factors[RiskFactor.EMERGENCY_ACCESS] = emergency_score

        # Calculate overall risk score (weighted average)
        risk_score = self._calculate_overall_risk(factors)
        overall_risk = self._score_to_risk_level(risk_score)

        # Generate recommendations based on assessment
        recommendations = self._generate_recommendations(
            factors, location_data, task_time, overall_risk
        )

        # Determine if approval is required
        requires_approval = overall_risk == SafetyRisk.RESTRICTED
        approval_reason = None
        if requires_approval:
            approval_reason = self._get_approval_reason(factors, warnings)

        # Create assessment
        now = datetime.now(UTC)
        assessment = SafetyAssessment(
            task_id=task_id,
            location=(lat, lng),
            overall_risk=overall_risk,
            risk_score=risk_score,
            factors=factors,
            warnings=warnings,
            recommendations=recommendations,
            safe_hours=safe_hours,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            assessed_at=now,
            expires_at=now + timedelta(hours=ASSESSMENT_VALIDITY_HOURS),
            metadata={
                "area_type": location_data.area_type.value,
                "is_private_property": location_data.is_private_property,
                "incident_count_90d": location_data.incident_count_90d,
            },
        )

        # Cache assessment
        self._assessment_cache[cache_key] = assessment

        logger.info(
            f"Safety assessment for ({lat}, {lng}): "
            f"risk={overall_risk.value}, score={risk_score:.2f}"
        )

        return assessment

    def check_time_risk(
        self,
        task_time: datetime,
        area_type: AreaType = AreaType.UNKNOWN,
    ) -> Tuple[float, List[str], List[Tuple[int, int]]]:
        """
        Check time-of-day risk factors.

        Args:
            task_time: Planned task execution time
            area_type: Type of area for context

        Returns:
            Tuple of (risk_score, warnings, safe_hours_list)
        """
        hour = task_time.hour
        warnings: List[str] = []

        # Check if in high-risk window
        is_high_risk = any(
            start <= hour or hour < end
            for start, end in HIGH_RISK_HOURS
            if start > end  # Handles overnight windows
        ) or any(
            start <= hour < end
            for start, end in HIGH_RISK_HOURS
            if start <= end
        )

        # Calculate base time risk
        if is_high_risk:
            base_risk = 0.6
            multiplier = NIGHT_RISK_MULTIPLIERS.get(area_type, 1.5)
            risk_score = min(1.0, base_risk * multiplier)

            warnings.append(
                f"Task scheduled during high-risk hours ({hour}:00). "
                f"Consider rescheduling to daylight hours."
            )
        else:
            risk_score = 0.1

        # Define safe hours
        safe_hours = [(6, 22)]  # 6am - 10pm by default

        # Adjust for area type
        if area_type == AreaType.INDUSTRIAL:
            safe_hours = [(8, 18)]  # Stricter for industrial
            if hour < 8 or hour >= 18:
                warnings.append(
                    "Industrial areas are safer during business hours (8am-6pm)."
                )
        elif area_type == AreaType.DOWNTOWN:
            safe_hours = [(7, 23)]  # Downtown stays active later

        return risk_score, warnings, safe_hours

    async def _get_location_data(
        self,
        lat: float,
        lng: float,
    ) -> LocationRiskData:
        """Get location risk data from services or defaults."""
        # Try property service first
        if self.property_service:
            try:
                return await self.property_service.check_property(lat, lng)
            except Exception as e:
                logger.warning(f"Property service error: {e}")

        # Return default data
        return LocationRiskData(
            latitude=lat,
            longitude=lng,
            crime_index=0.3,  # Moderate default
            area_type=AreaType.UNKNOWN,
        )

    async def _assess_crime_risk(
        self,
        location_data: LocationRiskData,
    ) -> Tuple[float, List[str]]:
        """Assess crime risk for location."""
        warnings: List[str] = []

        # Get crime index
        crime_index = location_data.crime_index

        # Apply area type multiplier
        multiplier = AREA_CRIME_MULTIPLIERS.get(location_data.area_type, 1.0)
        adjusted_score = min(1.0, crime_index * multiplier)

        # Generate warnings
        if adjusted_score > 0.7:
            warnings.append(
                f"High crime area detected (index: {crime_index:.2f}). "
                "Consider additional precautions or buddy system."
            )
        elif adjusted_score > 0.5:
            warnings.append(
                "Moderate crime rate in this area. Stay aware of surroundings."
            )

        return adjusted_score, warnings

    def _assess_property_risk(
        self,
        location_data: LocationRiskData,
    ) -> Tuple[float, List[str]]:
        """Assess private property access risks."""
        warnings: List[str] = []

        if not location_data.is_private_property:
            return 0.0, warnings

        risk_score = 0.4  # Base risk for private property

        warnings.append(
            "Location is on private property. "
            "Ensure you have proper authorization before entering."
        )

        if location_data.access_requirements:
            warnings.append(
                f"Access requirements: {location_data.access_requirements}"
            )
            risk_score += 0.1

        if location_data.property_owner:
            warnings.append(
                f"Property owner: {location_data.property_owner}. "
                "Consider contacting them before the task."
            )

        return risk_score, warnings

    async def _assess_weather_risk(
        self,
        lat: float,
        lng: float,
    ) -> Tuple[float, List[str]]:
        """Assess weather-related risks."""
        warnings: List[str] = []

        if not self.weather_service:
            return 0.0, warnings

        try:
            weather_risk = await self.weather_service.get_weather_risk(lat, lng)

            risk_scores = {
                WeatherRisk.NONE: 0.0,
                WeatherRisk.RAIN: 0.2,
                WeatherRisk.STORM: 0.7,
                WeatherRisk.EXTREME_HEAT: 0.5,
                WeatherRisk.EXTREME_COLD: 0.5,
                WeatherRisk.SNOW_ICE: 0.6,
                WeatherRisk.FLOODING: 0.8,
            }

            score = risk_scores.get(weather_risk, 0.0)

            if score > 0.3:
                warnings.append(
                    f"Weather alert: {weather_risk.value}. "
                    "Consider postponing or taking appropriate precautions."
                )

            return score, warnings

        except Exception as e:
            logger.warning(f"Weather service error: {e}")
            return 0.0, warnings

    def _assess_accessibility(
        self,
        location_data: LocationRiskData,
    ) -> Tuple[float, List[str]]:
        """Assess physical accessibility challenges."""
        warnings: List[str] = []
        risk_score = 0.0

        # Check for known hazards
        if location_data.known_hazards:
            risk_score += 0.1 * len(location_data.known_hazards)
            for hazard in location_data.known_hazards:
                warnings.append(f"Known hazard: {hazard}")

        # Rural/remote areas
        if location_data.area_type == AreaType.RURAL:
            risk_score += 0.2
            warnings.append(
                "Remote location. Ensure you have reliable communication and "
                "let someone know your plans."
            )

        return min(1.0, risk_score), warnings

    def _assess_incident_history(
        self,
        lat: float,
        lng: float,
    ) -> Tuple[float, List[str]]:
        """Assess historical incident data for location."""
        warnings: List[str] = []

        # Get location key for incident lookup
        location_key = f"{lat:.4f}:{lng:.4f}"
        incidents = self._incident_history.get(location_key, [])

        if not incidents:
            return 0.0, warnings

        # Count recent incidents (last 90 days)
        recent = [
            i for i in incidents
            if (datetime.now(UTC) - i.get("timestamp", datetime.now(UTC))).days <= 90
        ]

        count = len(recent)

        if count > 5:
            risk_score = 0.8
            warnings.append(
                f"Multiple incidents reported at this location ({count} in last 90 days). "
                "Exercise extreme caution."
            )
        elif count > 2:
            risk_score = 0.5
            warnings.append(
                f"Some incidents reported at this location ({count} in last 90 days)."
            )
        elif count > 0:
            risk_score = 0.3
            warnings.append("Previous incident reported at this location.")
        else:
            risk_score = 0.0

        return risk_score, warnings

    def _assess_lighting(
        self,
        location_data: LocationRiskData,
        task_time: datetime,
    ) -> float:
        """Assess lighting conditions risk."""
        hour = task_time.hour
        is_dark = hour < 6 or hour >= 20

        if not is_dark:
            return 0.0

        if location_data.has_street_lighting:
            return 0.2  # Low risk with lighting
        else:
            return 0.5  # Higher risk without lighting

    def _assess_emergency_access(
        self,
        location_data: LocationRiskData,
    ) -> float:
        """Assess proximity to emergency services."""
        police_km = location_data.nearest_police_km
        hospital_km = location_data.nearest_hospital_km

        # Score based on distance
        if police_km > 10 or hospital_km > 15:
            return 0.6  # Remote from emergency services
        elif police_km > 5 or hospital_km > 10:
            return 0.3  # Moderate distance
        else:
            return 0.1  # Good emergency access

    def _calculate_overall_risk(
        self,
        factors: Dict[RiskFactor, float],
    ) -> float:
        """Calculate overall risk score from individual factors."""
        # Define weights for each factor
        weights = {
            RiskFactor.CRIME_RATE: 0.25,
            RiskFactor.TIME_OF_DAY: 0.20,
            RiskFactor.PRIVATE_PROPERTY: 0.10,
            RiskFactor.WEATHER: 0.15,
            RiskFactor.ACCESSIBILITY: 0.05,
            RiskFactor.INCIDENT_HISTORY: 0.15,
            RiskFactor.LIGHTING: 0.05,
            RiskFactor.EMERGENCY_ACCESS: 0.05,
        }

        weighted_sum = sum(
            factors.get(factor, 0.0) * weight
            for factor, weight in weights.items()
        )

        return min(1.0, weighted_sum)

    def _score_to_risk_level(self, score: float) -> SafetyRisk:
        """Convert numeric score to risk level."""
        if score >= RISK_THRESHOLD_HIGH:
            return SafetyRisk.RESTRICTED
        elif score >= RISK_THRESHOLD_MEDIUM:
            return SafetyRisk.HIGH
        elif score >= RISK_THRESHOLD_LOW:
            return SafetyRisk.MEDIUM
        else:
            return SafetyRisk.LOW

    def _generate_recommendations(
        self,
        factors: Dict[RiskFactor, float],
        location_data: LocationRiskData,
        task_time: datetime,
        overall_risk: SafetyRisk,
    ) -> List[str]:
        """Generate actionable safety recommendations."""
        recommendations: List[str] = []

        # General recommendations
        if overall_risk in [SafetyRisk.HIGH, SafetyRisk.RESTRICTED]:
            recommendations.append(
                "Consider using the buddy system - work with another person if possible."
            )
            recommendations.append(
                "Share your location and expected completion time with a trusted contact."
            )

        # Time-specific recommendations
        if factors.get(RiskFactor.TIME_OF_DAY, 0) > 0.4:
            recommendations.append(
                "Consider rescheduling to daylight hours (6am-10pm) if possible."
            )

        # Lighting recommendations
        if factors.get(RiskFactor.LIGHTING, 0) > 0.3:
            recommendations.append(
                "Bring a flashlight or headlamp for visibility."
            )

        # Crime-area recommendations
        if factors.get(RiskFactor.CRIME_RATE, 0) > 0.5:
            recommendations.append(
                "Avoid displaying valuable items. Keep phone secure but accessible."
            )
            recommendations.append(
                "Have a clear exit route planned before starting the task."
            )

        # Private property recommendations
        if location_data.is_private_property:
            recommendations.append(
                "Have documentation ready showing task authorization."
            )
            recommendations.append(
                "Contact property owner/manager before entering if possible."
            )

        # Remote area recommendations
        if location_data.area_type == AreaType.RURAL:
            recommendations.append(
                "Ensure your device is fully charged and you have offline access to task details."
            )
            recommendations.append(
                "Check cell coverage in the area beforehand."
            )

        # Weather recommendations
        if factors.get(RiskFactor.WEATHER, 0) > 0.3:
            recommendations.append(
                "Check weather forecast before heading out. Bring appropriate gear."
            )

        return recommendations

    def _get_approval_reason(
        self,
        factors: Dict[RiskFactor, float],
        warnings: List[str],
    ) -> str:
        """Get reason why approval is required."""
        high_factors = [
            f.value for f, score in factors.items()
            if score >= RISK_THRESHOLD_HIGH
        ]

        if high_factors:
            return f"High risk factors: {', '.join(high_factors)}"
        elif warnings:
            return f"Safety warnings: {warnings[0]}"
        else:
            return "Overall risk score exceeds threshold"

    def _get_cache_key(
        self,
        lat: float,
        lng: float,
        task_time: Optional[datetime],
    ) -> str:
        """Generate cache key for assessment."""
        # Round coordinates to ~100m precision
        lat_rounded = round(lat, 3)
        lng_rounded = round(lng, 3)

        # Include hour for time-sensitive caching
        hour = task_time.hour if task_time else 0

        return f"{lat_rounded}:{lng_rounded}:{hour}"

    def record_incident(
        self,
        lat: float,
        lng: float,
        incident_type: str,
        description: str,
        worker_id: Optional[str] = None,
    ) -> None:
        """
        Record a safety incident at a location.

        Used to build incident history for future assessments.

        Args:
            lat: Incident latitude
            lng: Incident longitude
            incident_type: Type of incident (e.g., "hostile_encounter", "access_denied")
            description: Brief description
            worker_id: Optional worker ID who reported
        """
        location_key = f"{lat:.4f}:{lng:.4f}"

        if location_key not in self._incident_history:
            self._incident_history[location_key] = []

        self._incident_history[location_key].append({
            "timestamp": datetime.now(UTC),
            "type": incident_type,
            "description": description,
            "worker_id": worker_id,
        })

        logger.info(
            f"Incident recorded at ({lat}, {lng}): {incident_type}"
        )

    def clear_cache(self) -> None:
        """Clear assessment cache."""
        self._assessment_cache.clear()

    def clear_incident_history(self, lat: float, lng: float) -> None:
        """Clear incident history for a location (admin only)."""
        location_key = f"{lat:.4f}:{lng:.4f}"
        self._incident_history.pop(location_key, None)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def quick_safety_check(
    lat: float,
    lng: float,
    task_time: Optional[datetime] = None,
) -> SafetyAssessment:
    """
    Quick safety check for a location.

    Convenience function for simple use cases.

    Args:
        lat: Latitude
        lng: Longitude
        task_time: Optional planned task time

    Returns:
        SafetyAssessment
    """
    investigator = SafetyInvestigator()
    return await investigator.assess_location(lat, lng, task_time=task_time)


def is_safe_time(hour: int, area_type: AreaType = AreaType.UNKNOWN) -> bool:
    """
    Quick check if a given hour is considered safe.

    Args:
        hour: Hour of day (0-23)
        area_type: Optional area type for context

    Returns:
        True if generally safe time
    """
    investigator = SafetyInvestigator()
    task_time = datetime.now(UTC).replace(hour=hour, minute=0)
    risk_score, _, _ = investigator.check_time_risk(task_time, area_type)
    return risk_score < RISK_THRESHOLD_MEDIUM
