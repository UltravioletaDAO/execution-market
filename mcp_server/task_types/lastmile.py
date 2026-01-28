"""
Chamba Last Mile as a Service (NOW-133)

Implements delivery coordination for the "last mile" problem:
- Package pickup and delivery
- Multi-stop routes
- Real-time tracking
- Proof of delivery
- Delivery windows and SLAs

Use cases:
- Local business deliveries
- Pharmacy prescriptions
- Document courier
- Food delivery overflow
- Returns/exchanges
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4


class DeliveryType(str, Enum):
    """Types of delivery tasks."""
    STANDARD = "standard"        # Normal delivery, 2-4 hour window
    EXPRESS = "express"          # Fast delivery, 1 hour
    SCHEDULED = "scheduled"      # Specific time window
    MULTI_STOP = "multi_stop"    # Multiple deliveries in one trip
    RETURN = "return"            # Return/exchange pickup
    FRAGILE = "fragile"          # Requires special handling
    TEMPERATURE = "temperature"  # Temperature-controlled (food, meds)


class DeliveryStatus(str, Enum):
    """Status of a delivery task."""
    PENDING = "pending"          # Awaiting worker assignment
    ASSIGNED = "assigned"        # Worker assigned
    EN_ROUTE_PICKUP = "en_route_pickup"
    AT_PICKUP = "at_pickup"
    PICKED_UP = "picked_up"
    EN_ROUTE_DELIVERY = "en_route_delivery"
    AT_DELIVERY = "at_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"            # Delivery failed
    RETURNED = "returned"        # Returned to sender


class ProofType(str, Enum):
    """Types of delivery proof."""
    PHOTO = "photo"              # Photo of delivered package
    SIGNATURE = "signature"      # Recipient signature
    PIN_CODE = "pin_code"        # Recipient provides PIN
    ID_VERIFICATION = "id_verification"  # Check recipient ID
    SAFE_LOCATION = "safe_location"      # Photo of safe drop location


@dataclass
class Location:
    """
    A delivery location (pickup or dropoff).

    Attributes:
        address: Full street address
        latitude: GPS latitude
        longitude: GPS longitude
        contact_name: Person to contact
        contact_phone: Phone number
        instructions: Special instructions
        access_code: Building/gate code if needed
    """
    address: str
    latitude: float
    longitude: float
    contact_name: str = ""
    contact_phone: str = ""
    instructions: str = ""
    access_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "instructions": self.instructions,
            "access_code": self.access_code if self.access_code else None,
        }


@dataclass
class DeliveryWindow:
    """
    Time window for delivery.

    Attributes:
        start: Window start time
        end: Window end time
        is_strict: Whether window is strict (SLA penalty if missed)
    """
    start: datetime
    end: datetime
    is_strict: bool = False

    @property
    def duration_minutes(self) -> int:
        """Get window duration in minutes."""
        delta = self.end - self.start
        return int(delta.total_seconds() / 60)

    def is_active(self) -> bool:
        """Check if current time is within window."""
        now = datetime.now(UTC)
        return self.start <= now <= self.end

    def time_until_start(self) -> timedelta:
        """Get time until window starts."""
        now = datetime.now(UTC)
        if now >= self.start:
            return timedelta(0)
        return self.start - now

    def time_remaining(self) -> timedelta:
        """Get time remaining in window."""
        now = datetime.now(UTC)
        if now >= self.end:
            return timedelta(0)
        if now < self.start:
            return self.end - self.start
        return self.end - now

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_minutes": self.duration_minutes,
            "is_strict": self.is_strict,
        }


@dataclass
class PackageInfo:
    """
    Information about the package being delivered.

    Attributes:
        description: What's in the package
        weight_kg: Weight in kilograms
        dimensions: Dimensions string (e.g., "30x20x10 cm")
        value_usd: Declared value
        is_fragile: Requires careful handling
        temperature_requirements: Temp requirements if any
        handling_instructions: Special handling notes
    """
    description: str
    weight_kg: float = 0.0
    dimensions: str = ""
    value_usd: Decimal = Decimal("0")
    is_fragile: bool = False
    temperature_requirements: str = ""
    handling_instructions: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "description": self.description,
            "weight_kg": self.weight_kg,
            "dimensions": self.dimensions,
            "value_usd": str(self.value_usd),
            "is_fragile": self.is_fragile,
            "temperature_requirements": self.temperature_requirements,
            "handling_instructions": self.handling_instructions,
        }


@dataclass
class DeliveryStop:
    """
    A single stop in a delivery route.

    Attributes:
        stop_id: Unique stop identifier
        sequence: Order in route (1, 2, 3...)
        location: Stop location
        stop_type: "pickup" or "delivery"
        package: Package info (for pickup) or reference (for delivery)
        window: Time window for this stop
        proof_required: What proof is needed
        completed_at: When stop was completed
        proof_url: URL to proof image/signature
        notes: Worker notes about this stop
    """
    stop_id: str
    sequence: int
    location: Location
    stop_type: str  # "pickup" or "delivery"
    package: PackageInfo
    window: Optional[DeliveryWindow] = None
    proof_required: List[ProofType] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    proof_url: Optional[str] = None
    notes: str = ""

    def is_completed(self) -> bool:
        """Check if stop is completed."""
        return self.completed_at is not None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "stop_id": self.stop_id,
            "sequence": self.sequence,
            "location": self.location.to_dict(),
            "stop_type": self.stop_type,
            "package": self.package.to_dict(),
            "window": self.window.to_dict() if self.window else None,
            "proof_required": [p.value for p in self.proof_required],
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "proof_url": self.proof_url,
            "notes": self.notes,
        }


@dataclass
class DeliveryTask:
    """
    A last-mile delivery task.

    Attributes:
        id: Unique task identifier
        delivery_type: Type of delivery
        stops: List of stops in order
        status: Current delivery status
        bounty_usd: Base payment
        tip_usd: Optional tip from sender
        distance_km: Estimated total distance
        estimated_duration_minutes: Estimated completion time
        assigned_worker: Worker ID if assigned
        created_at: When task was created
        started_at: When worker started
        completed_at: When delivery completed
        metadata: Additional task data
    """
    id: str
    delivery_type: DeliveryType
    stops: List[DeliveryStop]
    status: DeliveryStatus = DeliveryStatus.PENDING
    bounty_usd: Decimal = Decimal("0")
    tip_usd: Decimal = Decimal("0")
    distance_km: float = 0.0
    estimated_duration_minutes: int = 0
    assigned_worker: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_payment(self) -> Decimal:
        """Total payment including tip."""
        return self.bounty_usd + self.tip_usd

    @property
    def pickup_stops(self) -> List[DeliveryStop]:
        """Get all pickup stops."""
        return [s for s in self.stops if s.stop_type == "pickup"]

    @property
    def delivery_stops(self) -> List[DeliveryStop]:
        """Get all delivery stops."""
        return [s for s in self.stops if s.stop_type == "delivery"]

    def get_current_stop(self) -> Optional[DeliveryStop]:
        """Get the next incomplete stop."""
        for stop in sorted(self.stops, key=lambda s: s.sequence):
            if not stop.is_completed():
                return stop
        return None

    def get_progress(self) -> Dict[str, Any]:
        """Get delivery progress."""
        completed = sum(1 for s in self.stops if s.is_completed())
        return {
            "total_stops": len(self.stops),
            "completed_stops": completed,
            "progress_percent": round((completed / len(self.stops)) * 100, 1) if self.stops else 0,
            "current_stop": self.get_current_stop().stop_id if self.get_current_stop() else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "delivery_type": self.delivery_type.value,
            "stops": [s.to_dict() for s in self.stops],
            "status": self.status.value,
            "bounty_usd": str(self.bounty_usd),
            "tip_usd": str(self.tip_usd),
            "total_payment": str(self.total_payment),
            "distance_km": self.distance_km,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "assigned_worker": self.assigned_worker,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.get_progress(),
            "metadata": self.metadata,
        }


class LastMilePricing:
    """
    Pricing calculator for last-mile deliveries.

    Factors:
    - Base rate per delivery type
    - Distance-based pricing
    - Time-based pricing (rush hour, night)
    - Special handling fees
    - Multi-stop discounts
    """

    # Base rates by delivery type
    BASE_RATES: Dict[DeliveryType, Decimal] = {
        DeliveryType.STANDARD: Decimal("5.00"),
        DeliveryType.EXPRESS: Decimal("10.00"),
        DeliveryType.SCHEDULED: Decimal("7.00"),
        DeliveryType.MULTI_STOP: Decimal("8.00"),  # Base for first stop
        DeliveryType.RETURN: Decimal("6.00"),
        DeliveryType.FRAGILE: Decimal("8.00"),
        DeliveryType.TEMPERATURE: Decimal("12.00"),
    }

    # Per-km rate
    PER_KM_RATE = Decimal("0.50")

    # Per additional stop (after first)
    PER_ADDITIONAL_STOP = Decimal("3.00")

    # Time multipliers
    TIME_MULTIPLIERS = {
        "rush_hour": Decimal("1.3"),      # 7-9am, 5-7pm weekdays
        "night": Decimal("1.2"),           # 9pm-6am
        "weekend": Decimal("1.1"),         # Saturday-Sunday
        "holiday": Decimal("1.5"),         # Major holidays
        "normal": Decimal("1.0"),
    }

    # Special handling fees
    HANDLING_FEES = {
        "fragile": Decimal("2.00"),
        "oversized": Decimal("3.00"),       # > 20kg or large dimensions
        "temperature": Decimal("5.00"),     # Temperature controlled
        "signature": Decimal("1.00"),       # Signature required
        "id_check": Decimal("2.00"),        # ID verification
    }

    @classmethod
    def calculate_bounty(
        cls,
        delivery_type: DeliveryType,
        distance_km: float,
        num_stops: int = 2,  # Default: 1 pickup + 1 delivery
        time_type: str = "normal",
        is_fragile: bool = False,
        is_oversized: bool = False,
        requires_temperature: bool = False,
        requires_signature: bool = False,
        requires_id: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate delivery bounty with breakdown.

        Args:
            delivery_type: Type of delivery
            distance_km: Total route distance
            num_stops: Number of stops (pickup + delivery)
            time_type: Time category (normal, rush_hour, night, etc.)
            is_fragile: Fragile handling required
            is_oversized: Package is oversized
            requires_temperature: Temperature control needed
            requires_signature: Signature required
            requires_id: ID verification required

        Returns:
            Dict with bounty and detailed breakdown
        """
        breakdown = {}

        # Base rate
        base = cls.BASE_RATES[delivery_type]
        breakdown["base_rate"] = str(base)

        # Distance rate
        distance_fee = cls.PER_KM_RATE * Decimal(str(distance_km))
        breakdown["distance_fee"] = str(distance_fee)
        breakdown["distance_km"] = distance_km

        # Additional stops (beyond basic pickup + delivery)
        additional_stops = max(0, num_stops - 2)
        stop_fee = cls.PER_ADDITIONAL_STOP * additional_stops
        if stop_fee > 0:
            breakdown["additional_stops_fee"] = str(stop_fee)

        # Handling fees
        handling_total = Decimal("0")
        handling_breakdown = []

        if is_fragile:
            handling_total += cls.HANDLING_FEES["fragile"]
            handling_breakdown.append({"type": "fragile", "fee": str(cls.HANDLING_FEES["fragile"])})

        if is_oversized:
            handling_total += cls.HANDLING_FEES["oversized"]
            handling_breakdown.append({"type": "oversized", "fee": str(cls.HANDLING_FEES["oversized"])})

        if requires_temperature:
            handling_total += cls.HANDLING_FEES["temperature"]
            handling_breakdown.append({"type": "temperature", "fee": str(cls.HANDLING_FEES["temperature"])})

        if requires_signature:
            handling_total += cls.HANDLING_FEES["signature"]
            handling_breakdown.append({"type": "signature", "fee": str(cls.HANDLING_FEES["signature"])})

        if requires_id:
            handling_total += cls.HANDLING_FEES["id_check"]
            handling_breakdown.append({"type": "id_check", "fee": str(cls.HANDLING_FEES["id_check"])})

        if handling_breakdown:
            breakdown["handling_fees"] = handling_breakdown

        # Subtotal before time multiplier
        subtotal = base + distance_fee + stop_fee + handling_total

        # Time multiplier
        multiplier = cls.TIME_MULTIPLIERS.get(time_type, Decimal("1.0"))
        breakdown["time_multiplier"] = str(multiplier)
        breakdown["time_type"] = time_type

        # Final total
        total = (subtotal * multiplier).quantize(Decimal("0.01"))

        return {
            "bounty_usd": str(total),
            "breakdown": breakdown,
            "delivery_type": delivery_type.value,
        }


class LastMileFactory:
    """
    Factory for creating last-mile delivery tasks.
    """

    @classmethod
    def create_standard_delivery(
        cls,
        pickup_location: Location,
        delivery_location: Location,
        package: PackageInfo,
        pickup_window: Optional[DeliveryWindow] = None,
        delivery_window: Optional[DeliveryWindow] = None,
        proof_required: Optional[List[ProofType]] = None,
        tip_usd: Decimal = Decimal("0"),
    ) -> DeliveryTask:
        """
        Create a standard single-pickup, single-delivery task.

        Args:
            pickup_location: Where to pick up package
            delivery_location: Where to deliver
            package: Package information
            pickup_window: Time window for pickup
            delivery_window: Time window for delivery
            proof_required: Proof types needed
            tip_usd: Optional tip

        Returns:
            Configured DeliveryTask
        """
        # Default windows if not provided
        now = datetime.now(UTC)
        if not pickup_window:
            pickup_window = DeliveryWindow(
                start=now,
                end=now + timedelta(hours=2),
            )
        if not delivery_window:
            delivery_window = DeliveryWindow(
                start=now + timedelta(hours=1),
                end=now + timedelta(hours=4),
            )

        # Default proof
        if proof_required is None:
            proof_required = [ProofType.PHOTO]

        # Estimate distance (in real implementation, use routing API)
        # Placeholder: straight-line distance * 1.3 for road distance
        import math
        lat_diff = delivery_location.latitude - pickup_location.latitude
        lon_diff = delivery_location.longitude - pickup_location.longitude
        straight_line_km = math.sqrt(lat_diff**2 + lon_diff**2) * 111  # Rough km conversion
        estimated_distance = straight_line_km * 1.3

        # Calculate bounty
        pricing = LastMilePricing.calculate_bounty(
            delivery_type=DeliveryType.STANDARD,
            distance_km=estimated_distance,
            is_fragile=package.is_fragile,
            requires_temperature=bool(package.temperature_requirements),
        )

        stops = [
            DeliveryStop(
                stop_id=str(uuid4()),
                sequence=1,
                location=pickup_location,
                stop_type="pickup",
                package=package,
                window=pickup_window,
                proof_required=[ProofType.PHOTO],  # Photo at pickup
            ),
            DeliveryStop(
                stop_id=str(uuid4()),
                sequence=2,
                location=delivery_location,
                stop_type="delivery",
                package=package,
                window=delivery_window,
                proof_required=proof_required,
            ),
        ]

        return DeliveryTask(
            id=str(uuid4()),
            delivery_type=DeliveryType.STANDARD,
            stops=stops,
            bounty_usd=Decimal(pricing["bounty_usd"]),
            tip_usd=tip_usd,
            distance_km=round(estimated_distance, 2),
            estimated_duration_minutes=int(30 + estimated_distance * 3),  # 30 min base + 3 min/km
            metadata={
                "pricing_breakdown": pricing["breakdown"],
            }
        )

    @classmethod
    def create_express_delivery(
        cls,
        pickup_location: Location,
        delivery_location: Location,
        package: PackageInfo,
        deadline_minutes: int = 60,
        proof_required: Optional[List[ProofType]] = None,
        tip_usd: Decimal = Decimal("0"),
    ) -> DeliveryTask:
        """
        Create an express delivery with tight deadline.

        Args:
            pickup_location: Where to pick up
            delivery_location: Where to deliver
            package: Package information
            deadline_minutes: Minutes to complete delivery
            proof_required: Proof types needed
            tip_usd: Optional tip

        Returns:
            Configured DeliveryTask with EXPRESS type
        """
        now = datetime.now(UTC)

        pickup_window = DeliveryWindow(
            start=now,
            end=now + timedelta(minutes=15),
            is_strict=True,
        )

        delivery_window = DeliveryWindow(
            start=now + timedelta(minutes=15),
            end=now + timedelta(minutes=deadline_minutes),
            is_strict=True,
        )

        if proof_required is None:
            proof_required = [ProofType.PHOTO, ProofType.SIGNATURE]

        # Same distance calculation as standard
        import math
        lat_diff = delivery_location.latitude - pickup_location.latitude
        lon_diff = delivery_location.longitude - pickup_location.longitude
        straight_line_km = math.sqrt(lat_diff**2 + lon_diff**2) * 111
        estimated_distance = straight_line_km * 1.3

        # Express pricing
        pricing = LastMilePricing.calculate_bounty(
            delivery_type=DeliveryType.EXPRESS,
            distance_km=estimated_distance,
            is_fragile=package.is_fragile,
            requires_signature=ProofType.SIGNATURE in proof_required,
        )

        stops = [
            DeliveryStop(
                stop_id=str(uuid4()),
                sequence=1,
                location=pickup_location,
                stop_type="pickup",
                package=package,
                window=pickup_window,
                proof_required=[ProofType.PHOTO],
            ),
            DeliveryStop(
                stop_id=str(uuid4()),
                sequence=2,
                location=delivery_location,
                stop_type="delivery",
                package=package,
                window=delivery_window,
                proof_required=proof_required,
            ),
        ]

        return DeliveryTask(
            id=str(uuid4()),
            delivery_type=DeliveryType.EXPRESS,
            stops=stops,
            bounty_usd=Decimal(pricing["bounty_usd"]),
            tip_usd=tip_usd,
            distance_km=round(estimated_distance, 2),
            estimated_duration_minutes=deadline_minutes,
            metadata={
                "pricing_breakdown": pricing["breakdown"],
                "deadline_minutes": deadline_minutes,
                "is_express": True,
            }
        )

    @classmethod
    def create_multi_stop_delivery(
        cls,
        pickups: List[Tuple[Location, PackageInfo]],
        deliveries: List[Tuple[Location, str]],  # Location + package_id to deliver
        overall_window: Optional[DeliveryWindow] = None,
        proof_required: Optional[List[ProofType]] = None,
        tip_usd: Decimal = Decimal("0"),
    ) -> DeliveryTask:
        """
        Create a multi-stop delivery route.

        Args:
            pickups: List of (Location, PackageInfo) tuples for pickups
            deliveries: List of (Location, package_description) tuples for deliveries
            overall_window: Time window for entire route
            proof_required: Proof types needed at delivery stops
            tip_usd: Optional tip

        Returns:
            Configured DeliveryTask with multiple stops
        """
        now = datetime.now(UTC)

        if not overall_window:
            overall_window = DeliveryWindow(
                start=now,
                end=now + timedelta(hours=4),
            )

        if proof_required is None:
            proof_required = [ProofType.PHOTO]

        stops = []
        sequence = 1

        # Add pickup stops
        for location, package in pickups:
            stops.append(DeliveryStop(
                stop_id=str(uuid4()),
                sequence=sequence,
                location=location,
                stop_type="pickup",
                package=package,
                proof_required=[ProofType.PHOTO],
            ))
            sequence += 1

        # Add delivery stops
        for location, package_desc in deliveries:
            stops.append(DeliveryStop(
                stop_id=str(uuid4()),
                sequence=sequence,
                location=location,
                stop_type="delivery",
                package=PackageInfo(description=package_desc),
                window=overall_window,
                proof_required=proof_required,
            ))
            sequence += 1

        # Estimate total distance (simplified)
        total_distance = len(stops) * 3.0  # Rough estimate: 3km between stops

        # Multi-stop pricing
        pricing = LastMilePricing.calculate_bounty(
            delivery_type=DeliveryType.MULTI_STOP,
            distance_km=total_distance,
            num_stops=len(stops),
        )

        return DeliveryTask(
            id=str(uuid4()),
            delivery_type=DeliveryType.MULTI_STOP,
            stops=stops,
            bounty_usd=Decimal(pricing["bounty_usd"]),
            tip_usd=tip_usd,
            distance_km=round(total_distance, 2),
            estimated_duration_minutes=30 + len(stops) * 15,  # 30 base + 15 min/stop
            metadata={
                "pricing_breakdown": pricing["breakdown"],
                "num_pickups": len(pickups),
                "num_deliveries": len(deliveries),
            }
        )


class DeliveryTracker:
    """
    Tracks delivery progress and generates status updates.
    """

    @staticmethod
    def update_stop_completed(
        task: DeliveryTask,
        stop_id: str,
        proof_url: str,
        notes: str = "",
    ) -> DeliveryTask:
        """
        Mark a stop as completed.

        Args:
            task: The delivery task
            stop_id: Stop ID to mark complete
            proof_url: URL to proof evidence
            notes: Worker notes

        Returns:
            Updated task
        """
        for stop in task.stops:
            if stop.stop_id == stop_id:
                stop.completed_at = datetime.now(UTC)
                stop.proof_url = proof_url
                stop.notes = notes
                break

        # Update overall status based on progress
        all_pickups_done = all(
            s.is_completed() for s in task.stops if s.stop_type == "pickup"
        )
        all_deliveries_done = all(
            s.is_completed() for s in task.stops if s.stop_type == "delivery"
        )

        if all_deliveries_done:
            task.status = DeliveryStatus.DELIVERED
            task.completed_at = datetime.now(UTC)
        elif all_pickups_done:
            task.status = DeliveryStatus.EN_ROUTE_DELIVERY
        else:
            task.status = DeliveryStatus.EN_ROUTE_PICKUP

        return task

    @staticmethod
    def get_eta(
        task: DeliveryTask,
        current_lat: float,
        current_lon: float,
    ) -> Dict[str, Any]:
        """
        Calculate ETA to next stop.

        Args:
            task: The delivery task
            current_lat: Worker's current latitude
            current_lon: Worker's current longitude

        Returns:
            Dict with ETA information
        """
        current_stop = task.get_current_stop()
        if not current_stop:
            return {"status": "complete", "eta_minutes": 0}

        # Calculate distance to next stop
        import math
        lat_diff = current_stop.location.latitude - current_lat
        lon_diff = current_stop.location.longitude - current_lon
        distance_km = math.sqrt(lat_diff**2 + lon_diff**2) * 111 * 1.3

        # Estimate time (assuming 20 km/h average in city)
        eta_minutes = int((distance_km / 20) * 60) + 5  # +5 for stop time

        return {
            "next_stop": current_stop.stop_id,
            "stop_type": current_stop.stop_type,
            "distance_km": round(distance_km, 2),
            "eta_minutes": eta_minutes,
            "address": current_stop.location.address,
        }


# Convenience functions
def create_delivery(
    pickup_location: Location,
    delivery_location: Location,
    package: PackageInfo,
    delivery_type: DeliveryType = DeliveryType.STANDARD,
    **kwargs,
) -> DeliveryTask:
    """
    Create a delivery task using appropriate factory method.

    Args:
        pickup_location: Pickup location
        delivery_location: Delivery location
        package: Package information
        delivery_type: Type of delivery
        **kwargs: Additional arguments

    Returns:
        Configured DeliveryTask
    """
    if delivery_type == DeliveryType.EXPRESS:
        return LastMileFactory.create_express_delivery(
            pickup_location, delivery_location, package, **kwargs
        )
    else:
        return LastMileFactory.create_standard_delivery(
            pickup_location, delivery_location, package, **kwargs
        )


def estimate_delivery_price(
    distance_km: float,
    delivery_type: DeliveryType = DeliveryType.STANDARD,
    **kwargs,
) -> Dict[str, Any]:
    """
    Quick estimate of delivery price.

    Args:
        distance_km: Estimated distance
        delivery_type: Type of delivery
        **kwargs: Additional pricing factors

    Returns:
        Pricing information
    """
    return LastMilePricing.calculate_bounty(
        delivery_type=delivery_type,
        distance_km=distance_km,
        **kwargs,
    )
