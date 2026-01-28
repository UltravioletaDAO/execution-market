"""
Worker Categorization System (NOW-177, NOW-178, NOW-179)

Manages worker categorization across multiple dimensions:
- Expertise areas and levels
- Geographic location and coverage
- Work modalities (remote, on-site, hybrid)
- Age demographics (for appropriate task matching)
- Equipment availability

This enables:
- Precise task-worker matching
- Specialized workforce pools
- Compliance with task requirements
- Fair distribution of opportunities
"""

import logging
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ExpertiseLevel(str, Enum):
    """Levels of expertise in a domain."""
    NOVICE = "novice"           # Learning, needs guidance
    INTERMEDIATE = "intermediate"  # Can work independently
    ADVANCED = "advanced"       # Expert level
    SPECIALIST = "specialist"   # Recognized expert, can train others


class Modality(str, Enum):
    """Work modality preferences/capabilities."""
    REMOTE_ONLY = "remote_only"
    ON_SITE_ONLY = "on_site_only"
    HYBRID = "hybrid"
    MOBILE = "mobile"           # Can travel to locations


class EquipmentType(str, Enum):
    """Types of equipment workers may have."""
    SMARTPHONE = "smartphone"
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    CAMERA_DSLR = "camera_dslr"
    CAMERA_PHONE = "camera_phone"
    MICROPHONE = "microphone"
    VEHICLE_CAR = "vehicle_car"
    VEHICLE_MOTORCYCLE = "vehicle_motorcycle"
    VEHICLE_BICYCLE = "vehicle_bicycle"
    TOOLS_BASIC = "tools_basic"
    TOOLS_PROFESSIONAL = "tools_professional"
    PRINTER = "printer"
    SCANNER = "scanner"
    INTERNET_HIGHSPEED = "internet_highspeed"
    INTERNET_BASIC = "internet_basic"


@dataclass
class ExpertiseArea:
    """Definition of an expertise area with specializations."""
    code: str
    name: str
    parent: Optional[str] = None  # For hierarchy
    specializations: List[str] = field(default_factory=list)
    requires_verification: bool = False


# Default expertise areas (hierarchical)
DEFAULT_EXPERTISE_AREAS = [
    # Technology
    ExpertiseArea("tech", "Technology"),
    ExpertiseArea("tech_software", "Software Development", "tech", ["web", "mobile", "backend", "devops"]),
    ExpertiseArea("tech_data", "Data & Analytics", "tech", ["sql", "python", "visualization", "ml"]),
    ExpertiseArea("tech_support", "Technical Support", "tech", ["hardware", "software", "networking"]),

    # Content & Media
    ExpertiseArea("content", "Content Creation"),
    ExpertiseArea("content_writing", "Writing", "content", ["blog", "technical", "copywriting", "translation"]),
    ExpertiseArea("content_photo", "Photography", "content", ["product", "real_estate", "portrait", "event"]),
    ExpertiseArea("content_video", "Video Production", "content", ["editing", "filming", "animation"]),
    ExpertiseArea("content_audio", "Audio Production", "content", ["podcast", "music", "voiceover"]),

    # Field Work
    ExpertiseArea("field", "Field Work"),
    ExpertiseArea("field_inspection", "Inspections", "field", ["real_estate", "vehicle", "construction"], True),
    ExpertiseArea("field_delivery", "Delivery & Logistics", "field", ["same_day", "bulk", "fragile"]),
    ExpertiseArea("field_mystery", "Mystery Shopping", "field", ["retail", "restaurant", "service"]),
    ExpertiseArea("field_survey", "Surveying & Data Collection", "field", ["street", "door_to_door", "observation"]),

    # Professional Services
    ExpertiseArea("professional", "Professional Services"),
    ExpertiseArea("professional_legal", "Legal", "professional", ["notary", "witness", "document_review"], True),
    ExpertiseArea("professional_finance", "Finance", "professional", ["bookkeeping", "tax", "audit"], True),
    ExpertiseArea("professional_translation", "Translation", "professional", ["certified", "technical", "literary"]),

    # Local Services
    ExpertiseArea("local", "Local Services"),
    ExpertiseArea("local_errands", "Errands", "local", ["shopping", "pickup", "waiting_in_line"]),
    ExpertiseArea("local_presence", "Physical Presence", "local", ["queue_holding", "attendance", "monitoring"]),
    ExpertiseArea("local_verification", "Verification", "local", ["address", "business", "person"]),

    # Research & Analysis
    ExpertiseArea("research", "Research & Analysis"),
    ExpertiseArea("research_market", "Market Research", "research", ["competitor", "pricing", "trends"]),
    ExpertiseArea("research_academic", "Academic Research", "research", ["literature_review", "data_collection"]),
    ExpertiseArea("research_ux", "UX Research", "research", ["usability", "interviews", "surveys"]),
]


@dataclass
class GeoLocation:
    """Geographic location with coverage area."""
    country_code: str           # ISO 3166-1 alpha-2
    region: Optional[str] = None  # State/Province
    city: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coverage_radius_km: float = 10.0  # How far worker can travel


@dataclass
class AgeRange:
    """Age range specification."""
    min_age: int = 18
    max_age: int = 999
    requires_verification: bool = False


@dataclass
class WorkerCategory:
    """A single category assignment for a worker."""
    category_type: str          # expertise, modality, equipment, etc.
    category_code: str          # Specific code
    level: Optional[ExpertiseLevel] = None
    verified: bool = False
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    endorsements: int = 0       # From agents/other workers
    tasks_completed: int = 0    # In this category


@dataclass
class WorkerProfile:
    """Complete worker profile with all categorizations."""
    worker_id: str
    display_name: str

    # Geographic
    primary_location: Optional[GeoLocation] = None
    additional_locations: List[GeoLocation] = field(default_factory=list)
    willing_to_travel: bool = False
    max_travel_km: float = 50.0

    # Expertise
    expertise: List[WorkerCategory] = field(default_factory=list)

    # Work preferences
    modalities: List[Modality] = field(default_factory=list)
    available_hours_per_week: int = 40
    preferred_task_types: List[str] = field(default_factory=list)
    avoided_task_types: List[str] = field(default_factory=list)

    # Equipment
    equipment: List[EquipmentType] = field(default_factory=list)

    # Demographics
    age_verified: bool = False
    age_range: Optional[AgeRange] = None

    # Languages
    languages: List[Dict[str, str]] = field(default_factory=list)  # [{"code": "es", "level": "native"}]

    # Profile metadata
    profile_completeness: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CategoryFilter:
    """Filter criteria for finding workers."""
    # Location
    country_codes: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    near_location: Optional[tuple[float, float]] = None  # lat, lon
    max_distance_km: Optional[float] = None

    # Expertise
    required_expertise: Optional[List[str]] = None
    min_expertise_level: Optional[ExpertiseLevel] = None
    verified_expertise_only: bool = False

    # Modality
    modalities: Optional[List[Modality]] = None

    # Equipment
    required_equipment: Optional[List[EquipmentType]] = None

    # Demographics
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    age_verification_required: bool = False

    # Languages
    required_languages: Optional[List[str]] = None

    # Availability
    min_hours_available: Optional[int] = None


@dataclass
class MatchResult:
    """Result of matching a worker to criteria."""
    worker_id: str
    match_score: float          # 0.0 - 1.0
    matching_criteria: List[str]
    missing_criteria: List[str]
    partial_matches: Dict[str, float]
    distance_km: Optional[float] = None


class CategoryManager:
    """
    Manages worker categorization and matching.

    Features:
    - Worker profile management
    - Category assignment and verification
    - Task-worker matching
    - Geographic filtering

    Example:
        >>> manager = CategoryManager()
        >>> profile = await manager.get_profile("worker_123")
        >>> await manager.add_expertise(
        ...     "worker_123",
        ...     "content_photo",
        ...     ExpertiseLevel.ADVANCED
        ... )
        >>> matches = await manager.find_workers(CategoryFilter(
        ...     required_expertise=["content_photo"],
        ...     min_expertise_level=ExpertiseLevel.INTERMEDIATE,
        ...     cities=["Mexico City"]
        ... ))
    """

    def __init__(
        self,
        expertise_areas: Optional[List[ExpertiseArea]] = None
    ):
        """Initialize with optional custom expertise areas."""
        self.expertise_areas = {
            area.code: area
            for area in (expertise_areas or DEFAULT_EXPERTISE_AREAS)
        }
        self._profiles: Dict[str, WorkerProfile] = {}

    async def get_profile(
        self,
        worker_id: str,
        db_client: Optional[Any] = None
    ) -> Optional[WorkerProfile]:
        """
        Get worker profile.

        Args:
            worker_id: Worker's unique identifier
            db_client: Optional database client

        Returns:
            WorkerProfile or None
        """
        if worker_id in self._profiles:
            return self._profiles[worker_id]

        if db_client:
            return await self._load_profile(worker_id, db_client)

        return None

    async def create_profile(
        self,
        worker_id: str,
        display_name: str,
        primary_location: Optional[GeoLocation] = None,
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Create new worker profile.

        Args:
            worker_id: Worker's unique identifier
            display_name: Display name
            primary_location: Primary work location
            db_client: Optional database client

        Returns:
            Created WorkerProfile
        """
        profile = WorkerProfile(
            worker_id=worker_id,
            display_name=display_name,
            primary_location=primary_location,
        )

        self._profiles[worker_id] = profile

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(f"Created profile for worker {worker_id}")
        return profile

    async def update_location(
        self,
        worker_id: str,
        location: GeoLocation,
        is_primary: bool = True,
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Update worker's location.

        Args:
            worker_id: Worker's unique identifier
            location: New location
            is_primary: Whether this is primary location
            db_client: Optional database client

        Returns:
            Updated WorkerProfile
        """
        profile = await self.get_profile(worker_id, db_client)
        if not profile:
            raise ValueError(f"Worker {worker_id} not found")

        if is_primary:
            profile.primary_location = location
        else:
            profile.additional_locations.append(location)

        profile.updated_at = datetime.now(timezone.utc)
        self._update_completeness(profile)

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(
            f"Updated location for {worker_id}: "
            f"{location.city}, {location.country_code}"
        )
        return profile

    async def add_expertise(
        self,
        worker_id: str,
        expertise_code: str,
        level: ExpertiseLevel,
        verified: bool = False,
        verified_by: Optional[str] = None,
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Add expertise to worker profile.

        Args:
            worker_id: Worker's unique identifier
            expertise_code: Expertise area code
            level: Expertise level
            verified: Whether verified
            verified_by: Verifier identifier
            db_client: Optional database client

        Returns:
            Updated WorkerProfile
        """
        profile = await self.get_profile(worker_id, db_client)
        if not profile:
            raise ValueError(f"Worker {worker_id} not found")

        if expertise_code not in self.expertise_areas:
            raise ValueError(f"Invalid expertise code: {expertise_code}")

        # Check if already exists
        existing = next(
            (e for e in profile.expertise if e.category_code == expertise_code),
            None
        )

        if existing:
            # Update existing
            existing.level = level
            if verified:
                existing.verified = True
                existing.verified_at = datetime.now(timezone.utc)
                existing.verified_by = verified_by
        else:
            # Add new
            category = WorkerCategory(
                category_type="expertise",
                category_code=expertise_code,
                level=level,
                verified=verified,
                verified_at=datetime.now(timezone.utc) if verified else None,
                verified_by=verified_by,
            )
            profile.expertise.append(category)

        profile.updated_at = datetime.now(timezone.utc)
        self._update_completeness(profile)

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(
            f"Added expertise {expertise_code} ({level.value}) for {worker_id}"
        )
        return profile

    async def set_equipment(
        self,
        worker_id: str,
        equipment: List[EquipmentType],
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Set worker's available equipment.

        Args:
            worker_id: Worker's unique identifier
            equipment: List of equipment types
            db_client: Optional database client

        Returns:
            Updated WorkerProfile
        """
        profile = await self.get_profile(worker_id, db_client)
        if not profile:
            raise ValueError(f"Worker {worker_id} not found")

        profile.equipment = equipment
        profile.updated_at = datetime.now(timezone.utc)
        self._update_completeness(profile)

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(
            f"Updated equipment for {worker_id}: {[e.value for e in equipment]}"
        )
        return profile

    async def set_modalities(
        self,
        worker_id: str,
        modalities: List[Modality],
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Set worker's work modalities.

        Args:
            worker_id: Worker's unique identifier
            modalities: List of modalities
            db_client: Optional database client

        Returns:
            Updated WorkerProfile
        """
        profile = await self.get_profile(worker_id, db_client)
        if not profile:
            raise ValueError(f"Worker {worker_id} not found")

        profile.modalities = modalities
        profile.updated_at = datetime.now(timezone.utc)
        self._update_completeness(profile)

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(
            f"Updated modalities for {worker_id}: {[m.value for m in modalities]}"
        )
        return profile

    async def add_language(
        self,
        worker_id: str,
        language_code: str,
        level: str,  # native, fluent, conversational, basic
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Add language to worker profile.

        Args:
            worker_id: Worker's unique identifier
            language_code: ISO 639-1 language code
            level: Proficiency level
            db_client: Optional database client

        Returns:
            Updated WorkerProfile
        """
        profile = await self.get_profile(worker_id, db_client)
        if not profile:
            raise ValueError(f"Worker {worker_id} not found")

        # Check if already exists
        existing = next(
            (l for l in profile.languages if l["code"] == language_code),
            None
        )

        if existing:
            existing["level"] = level
        else:
            profile.languages.append({"code": language_code, "level": level})

        profile.updated_at = datetime.now(timezone.utc)
        self._update_completeness(profile)

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(f"Added language {language_code} ({level}) for {worker_id}")
        return profile

    async def verify_age(
        self,
        worker_id: str,
        birth_year: int,
        verified_by: str,
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Verify worker's age.

        Args:
            worker_id: Worker's unique identifier
            birth_year: Year of birth
            verified_by: Verifier identifier
            db_client: Optional database client

        Returns:
            Updated WorkerProfile
        """
        profile = await self.get_profile(worker_id, db_client)
        if not profile:
            raise ValueError(f"Worker {worker_id} not found")

        current_year = datetime.now().year
        age = current_year - birth_year

        profile.age_verified = True
        profile.age_range = AgeRange(
            min_age=age,
            max_age=age,
            requires_verification=False,
        )
        profile.updated_at = datetime.now(timezone.utc)
        self._update_completeness(profile)

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(f"Age verified for {worker_id}: {age} years")
        return profile

    async def find_workers(
        self,
        criteria: CategoryFilter,
        limit: int = 50,
        db_client: Optional[Any] = None
    ) -> List[MatchResult]:
        """
        Find workers matching criteria.

        Args:
            criteria: Filter criteria
            limit: Maximum results
            db_client: Optional database client

        Returns:
            List of MatchResult sorted by score
        """
        matches: List[MatchResult] = []

        # Get profiles to search
        if db_client:
            profiles = await self._search_profiles(criteria, limit * 2, db_client)
        else:
            profiles = list(self._profiles.values())

        for profile in profiles:
            match = self._evaluate_match(profile, criteria)
            if match.match_score > 0:
                matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.match_score, reverse=True)

        return matches[:limit]

    async def endorse_expertise(
        self,
        worker_id: str,
        expertise_code: str,
        endorsed_by: str,
        endorser_type: str = "agent",  # agent, worker, admin
        db_client: Optional[Any] = None
    ) -> WorkerProfile:
        """
        Add endorsement to worker's expertise.

        Args:
            worker_id: Worker's unique identifier
            expertise_code: Expertise to endorse
            endorsed_by: Endorser identifier
            endorser_type: Type of endorser
            db_client: Optional database client

        Returns:
            Updated WorkerProfile
        """
        profile = await self.get_profile(worker_id, db_client)
        if not profile:
            raise ValueError(f"Worker {worker_id} not found")

        expertise = next(
            (e for e in profile.expertise if e.category_code == expertise_code),
            None
        )

        if not expertise:
            raise ValueError(
                f"Worker {worker_id} does not have expertise {expertise_code}"
            )

        expertise.endorsements += 1
        profile.updated_at = datetime.now(timezone.utc)

        if db_client:
            await self._save_profile(profile, db_client)

        logger.info(
            f"Endorsement added for {worker_id} in {expertise_code} "
            f"by {endorser_type} {endorsed_by}"
        )
        return profile

    def get_expertise_tree(self) -> Dict[str, Any]:
        """
        Get hierarchical expertise tree for UI.

        Returns:
            Dict with expertise hierarchy
        """
        tree: Dict[str, Any] = {}

        # First pass: add root nodes
        for code, area in self.expertise_areas.items():
            if area.parent is None:
                tree[code] = {
                    "name": area.name,
                    "requires_verification": area.requires_verification,
                    "specializations": area.specializations,
                    "children": {},
                }

        # Second pass: add children
        for code, area in self.expertise_areas.items():
            if area.parent and area.parent in tree:
                tree[area.parent]["children"][code] = {
                    "name": area.name,
                    "requires_verification": area.requires_verification,
                    "specializations": area.specializations,
                }

        return tree

    def _evaluate_match(
        self,
        profile: WorkerProfile,
        criteria: CategoryFilter
    ) -> MatchResult:
        """Evaluate how well a profile matches criteria."""
        matching: List[str] = []
        missing: List[str] = []
        partial: Dict[str, float] = {}
        total_weight = 0
        matched_weight = 0

        # Location matching (weight: 3)
        if criteria.country_codes:
            total_weight += 3
            if profile.primary_location and profile.primary_location.country_code in criteria.country_codes:
                matching.append(f"country:{profile.primary_location.country_code}")
                matched_weight += 3
            else:
                missing.append("country")

        if criteria.cities:
            total_weight += 2
            if profile.primary_location and profile.primary_location.city in criteria.cities:
                matching.append(f"city:{profile.primary_location.city}")
                matched_weight += 2
            else:
                missing.append("city")

        # Distance matching
        if criteria.near_location and criteria.max_distance_km:
            total_weight += 3
            if profile.primary_location and profile.primary_location.latitude:
                distance = self._calculate_distance(
                    criteria.near_location,
                    (profile.primary_location.latitude, profile.primary_location.longitude)
                )
                if distance <= criteria.max_distance_km:
                    matching.append(f"distance:{distance:.1f}km")
                    matched_weight += 3
                    partial["distance"] = 1.0 - (distance / criteria.max_distance_km)
                else:
                    missing.append(f"distance (need <{criteria.max_distance_km}km)")

        # Expertise matching (weight: 4)
        if criteria.required_expertise:
            for exp_code in criteria.required_expertise:
                total_weight += 4
                worker_exp = next(
                    (e for e in profile.expertise if e.category_code == exp_code),
                    None
                )

                if worker_exp:
                    # Check level if required
                    if criteria.min_expertise_level:
                        level_order = [e for e in ExpertiseLevel]
                        worker_level_idx = level_order.index(worker_exp.level) if worker_exp.level else 0
                        required_level_idx = level_order.index(criteria.min_expertise_level)

                        if worker_level_idx >= required_level_idx:
                            # Check verification if required
                            if criteria.verified_expertise_only and not worker_exp.verified:
                                partial[exp_code] = 0.7
                                matched_weight += 2.8
                                missing.append(f"{exp_code}:verification")
                            else:
                                matching.append(f"expertise:{exp_code}:{worker_exp.level.value}")
                                matched_weight += 4
                        else:
                            partial[exp_code] = worker_level_idx / required_level_idx
                            matched_weight += 4 * partial[exp_code]
                            missing.append(f"{exp_code}:level")
                    else:
                        matching.append(f"expertise:{exp_code}")
                        matched_weight += 4
                else:
                    missing.append(f"expertise:{exp_code}")

        # Modality matching (weight: 2)
        if criteria.modalities:
            total_weight += 2
            if any(m in profile.modalities for m in criteria.modalities):
                matching.append("modality")
                matched_weight += 2
            else:
                missing.append("modality")

        # Equipment matching (weight: 2 each)
        if criteria.required_equipment:
            for equip in criteria.required_equipment:
                total_weight += 2
                if equip in profile.equipment:
                    matching.append(f"equipment:{equip.value}")
                    matched_weight += 2
                else:
                    missing.append(f"equipment:{equip.value}")

        # Language matching (weight: 3)
        if criteria.required_languages:
            for lang in criteria.required_languages:
                total_weight += 3
                worker_lang = next(
                    (l for l in profile.languages if l["code"] == lang),
                    None
                )
                if worker_lang:
                    matching.append(f"language:{lang}:{worker_lang['level']}")
                    matched_weight += 3
                else:
                    missing.append(f"language:{lang}")

        # Age matching (weight: 2)
        if criteria.min_age or criteria.max_age:
            total_weight += 2
            if profile.age_range:
                age = profile.age_range.min_age
                age_ok = True

                if criteria.min_age and age < criteria.min_age:
                    age_ok = False
                if criteria.max_age and age > criteria.max_age:
                    age_ok = False

                if age_ok:
                    if criteria.age_verification_required and not profile.age_verified:
                        partial["age"] = 0.8
                        matched_weight += 1.6
                        missing.append("age:verification")
                    else:
                        matching.append("age")
                        matched_weight += 2
                else:
                    missing.append("age:range")
            else:
                missing.append("age:unknown")

        # Availability matching
        if criteria.min_hours_available:
            total_weight += 1
            if profile.available_hours_per_week >= criteria.min_hours_available:
                matching.append("availability")
                matched_weight += 1
            else:
                missing.append("availability")

        # Calculate final score
        score = matched_weight / total_weight if total_weight > 0 else 1.0

        return MatchResult(
            worker_id=profile.worker_id,
            match_score=round(score, 3),
            matching_criteria=matching,
            missing_criteria=missing,
            partial_matches=partial,
        )

    def _calculate_distance(
        self,
        point1: tuple[float, float],
        point2: tuple[float, float]
    ) -> float:
        """Calculate distance between two points in km (Haversine formula)."""
        import math

        lat1, lon1 = point1
        lat2, lon2 = point2

        R = 6371  # Earth's radius in km

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _update_completeness(self, profile: WorkerProfile):
        """Update profile completeness score."""
        total_fields = 10
        filled = 0

        if profile.primary_location:
            filled += 1
        if profile.expertise:
            filled += 1
        if profile.modalities:
            filled += 1
        if profile.equipment:
            filled += 1
        if profile.languages:
            filled += 1
        if profile.age_verified:
            filled += 1
        if profile.available_hours_per_week > 0:
            filled += 1
        if profile.preferred_task_types:
            filled += 1
        if profile.additional_locations:
            filled += 1
        if profile.display_name:
            filled += 1

        profile.profile_completeness = filled / total_fields

    async def _save_profile(
        self,
        profile: WorkerProfile,
        db_client: Any
    ):
        """Save profile to database."""
        data = {
            "worker_id": profile.worker_id,
            "display_name": profile.display_name,
            "primary_location": (
                {
                    "country_code": profile.primary_location.country_code,
                    "region": profile.primary_location.region,
                    "city": profile.primary_location.city,
                    "postal_code": profile.primary_location.postal_code,
                    "latitude": profile.primary_location.latitude,
                    "longitude": profile.primary_location.longitude,
                    "coverage_radius_km": profile.primary_location.coverage_radius_km,
                }
                if profile.primary_location else None
            ),
            "expertise": [
                {
                    "code": e.category_code,
                    "level": e.level.value if e.level else None,
                    "verified": e.verified,
                    "endorsements": e.endorsements,
                    "tasks_completed": e.tasks_completed,
                }
                for e in profile.expertise
            ],
            "modalities": [m.value for m in profile.modalities],
            "equipment": [e.value for e in profile.equipment],
            "languages": profile.languages,
            "age_verified": profile.age_verified,
            "available_hours_per_week": profile.available_hours_per_week,
            "profile_completeness": profile.profile_completeness,
            "updated_at": profile.updated_at.isoformat(),
        }

        db_client.table("worker_profiles").upsert(data).execute()

    async def _load_profile(
        self,
        worker_id: str,
        db_client: Any
    ) -> Optional[WorkerProfile]:
        """Load profile from database."""
        result = db_client.table("worker_profiles").select("*").eq(
            "worker_id", worker_id
        ).single().execute()

        if not result.data:
            return None

        data = result.data

        # Reconstruct profile
        profile = WorkerProfile(
            worker_id=data["worker_id"],
            display_name=data["display_name"],
        )

        # Location
        if data.get("primary_location"):
            loc = data["primary_location"]
            profile.primary_location = GeoLocation(
                country_code=loc["country_code"],
                region=loc.get("region"),
                city=loc.get("city"),
                postal_code=loc.get("postal_code"),
                latitude=loc.get("latitude"),
                longitude=loc.get("longitude"),
                coverage_radius_km=loc.get("coverage_radius_km", 10.0),
            )

        # Expertise
        for exp in data.get("expertise", []):
            profile.expertise.append(WorkerCategory(
                category_type="expertise",
                category_code=exp["code"],
                level=ExpertiseLevel(exp["level"]) if exp.get("level") else None,
                verified=exp.get("verified", False),
                endorsements=exp.get("endorsements", 0),
                tasks_completed=exp.get("tasks_completed", 0),
            ))

        # Modalities
        profile.modalities = [Modality(m) for m in data.get("modalities", [])]

        # Equipment
        profile.equipment = [EquipmentType(e) for e in data.get("equipment", [])]

        # Languages
        profile.languages = data.get("languages", [])

        # Other fields
        profile.age_verified = data.get("age_verified", False)
        profile.available_hours_per_week = data.get("available_hours_per_week", 40)
        profile.profile_completeness = data.get("profile_completeness", 0.0)

        self._profiles[worker_id] = profile
        return profile

    async def _search_profiles(
        self,
        criteria: CategoryFilter,
        limit: int,
        db_client: Any
    ) -> List[WorkerProfile]:
        """Search profiles in database with initial filters."""
        query = db_client.table("worker_profiles").select("*")

        # Apply database-level filters
        if criteria.country_codes:
            query = query.in_(
                "primary_location->>country_code",
                criteria.country_codes
            )

        result = query.limit(limit).execute()

        profiles = []
        for data in result.data or []:
            # Cache and return
            profile = await self._load_profile(data["worker_id"], db_client)
            if profile:
                profiles.append(profile)

        return profiles
