"""
Time-Based Premium System (NOW-176)

Calculates and applies premiums for work done during:
- Weekends: +15%
- Nights (8pm-6am): +25%
- Holidays: +50%

Premiums can stack (e.g., working Saturday night = +15% + +25% = +40%).

This incentivizes:
- Coverage during unpopular times
- Fair compensation for inconvenient hours
- 24/7 task availability through market mechanics
"""

import logging
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, date, time, timezone, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class PremiumType(str, Enum):
    """Types of time-based premiums."""
    WEEKEND = "weekend"
    NIGHT = "night"
    HOLIDAY = "holiday"
    SURGE = "surge"              # Dynamic demand-based premium
    URGENT = "urgent"            # Short deadline tasks


@dataclass
class PremiumConfig:
    """Configuration for premium calculations."""
    # Base premium percentages
    weekend_premium_pct: float = 15.0
    night_premium_pct: float = 25.0
    holiday_premium_pct: float = 50.0

    # Night hours definition (in worker's local time)
    night_start_hour: int = 20  # 8 PM
    night_end_hour: int = 6     # 6 AM

    # Weekend definition (0=Monday, 6=Sunday)
    weekend_days: Set[int] = field(default_factory=lambda: {5, 6})  # Sat, Sun

    # Stack premiums
    allow_premium_stacking: bool = True
    max_total_premium_pct: float = 100.0  # Cap at 2x

    # Surge pricing
    enable_surge: bool = True
    surge_min_pct: float = 10.0
    surge_max_pct: float = 50.0

    # Urgent task premiums
    urgent_threshold_hours: int = 4
    urgent_premium_pct: float = 20.0


@dataclass
class TimePremium:
    """Calculated premium for a specific time window."""
    base_amount: float
    premium_amount: float
    total_amount: float
    premium_percentage: float
    applied_premiums: List[Dict[str, Any]]
    calculation_time: datetime
    worker_timezone: str

    @property
    def multiplier(self) -> float:
        """Get the premium multiplier (1.0 = no premium)."""
        return 1.0 + (self.premium_percentage / 100)


@dataclass
class HolidayDefinition:
    """Definition of a holiday."""
    name: str
    month: int
    day: int
    country_codes: Optional[List[str]] = None  # None = global
    year: Optional[int] = None  # None = recurring


# Default holidays (major international + country-specific)
DEFAULT_HOLIDAYS = [
    # International/Global
    HolidayDefinition("New Year's Day", 1, 1),
    HolidayDefinition("Christmas Day", 12, 25),

    # US
    HolidayDefinition("Independence Day", 7, 4, ["US"]),
    HolidayDefinition("Thanksgiving", 11, 28, ["US"]),  # Approximation
    HolidayDefinition("Memorial Day", 5, 27, ["US"]),   # Approximation
    HolidayDefinition("Labor Day", 9, 2, ["US"]),       # Approximation

    # Mexico
    HolidayDefinition("Dia de la Independencia", 9, 16, ["MX"]),
    HolidayDefinition("Dia de los Muertos", 11, 2, ["MX"]),
    HolidayDefinition("Cinco de Mayo", 5, 5, ["MX"]),
    HolidayDefinition("Revolucion Mexicana", 11, 20, ["MX"]),

    # Brazil
    HolidayDefinition("Independence Day", 9, 7, ["BR"]),
    HolidayDefinition("Carnival", 2, 25, ["BR"]),       # Approximation

    # Argentina
    HolidayDefinition("Revolucion de Mayo", 5, 25, ["AR"]),
    HolidayDefinition("Independence Day", 7, 9, ["AR"]),

    # Colombia
    HolidayDefinition("Independence Day", 7, 20, ["CO"]),
    HolidayDefinition("Batalla de Boyaca", 8, 7, ["CO"]),

    # UK
    HolidayDefinition("Boxing Day", 12, 26, ["GB"]),
    HolidayDefinition("Bank Holiday", 8, 26, ["GB"]),   # Approximation

    # Germany
    HolidayDefinition("German Unity Day", 10, 3, ["DE"]),

    # France
    HolidayDefinition("Bastille Day", 7, 14, ["FR"]),

    # Spain
    HolidayDefinition("National Day", 10, 12, ["ES"]),

    # India
    HolidayDefinition("Independence Day", 8, 15, ["IN"]),
    HolidayDefinition("Republic Day", 1, 26, ["IN"]),
    HolidayDefinition("Diwali", 11, 1, ["IN"]),         # Approximation

    # Japan
    HolidayDefinition("Golden Week", 5, 3, ["JP"]),
    HolidayDefinition("Culture Day", 11, 3, ["JP"]),

    # China
    HolidayDefinition("Chinese New Year", 2, 10, ["CN"]),  # Approximation
    HolidayDefinition("National Day", 10, 1, ["CN"]),
]


class PremiumCalculator:
    """
    Calculates time-based premiums for task payments.

    Features:
    - Weekend premiums
    - Night shift premiums
    - Holiday premiums
    - Surge pricing based on demand
    - Premium stacking

    Example:
        >>> calc = PremiumCalculator()
        >>> premium = calc.calculate_premium(
        ...     base_amount=100.0,
        ...     work_time=datetime(2026, 1, 25, 22, 0),  # Saturday 10pm
        ...     worker_timezone="America/Mexico_City",
        ...     worker_country="MX"
        ... )
        >>> print(f"Total: ${premium.total_amount:.2f} (+{premium.premium_percentage}%)")
        Total: $140.00 (+40%)
    """

    def __init__(
        self,
        config: Optional[PremiumConfig] = None,
        holidays: Optional[List[HolidayDefinition]] = None
    ):
        """
        Initialize premium calculator.

        Args:
            config: Premium configuration
            holidays: List of holiday definitions (uses defaults if None)
        """
        self.config = config or PremiumConfig()
        self.holidays = holidays or DEFAULT_HOLIDAYS

    def calculate_premium(
        self,
        base_amount: float,
        work_time: Optional[datetime] = None,
        worker_timezone: str = "UTC",
        worker_country: Optional[str] = None,
        deadline_hours: Optional[int] = None,
        demand_multiplier: float = 1.0
    ) -> TimePremium:
        """
        Calculate total premium for a task.

        Args:
            base_amount: Base payment amount in USD
            work_time: Time work is performed (default: now)
            worker_timezone: Worker's IANA timezone
            worker_country: Worker's ISO country code for holidays
            deadline_hours: Hours until deadline (for urgency premium)
            demand_multiplier: Current demand level (1.0 = normal)

        Returns:
            TimePremium with breakdown of applied premiums
        """
        if work_time is None:
            work_time = datetime.now(timezone.utc)

        # Convert to worker's local time
        try:
            local_tz = ZoneInfo(worker_timezone)
            local_time = work_time.astimezone(local_tz)
        except Exception:
            logger.warning(f"Invalid timezone {worker_timezone}, using UTC")
            local_time = work_time
            worker_timezone = "UTC"

        applied_premiums: List[Dict[str, Any]] = []
        total_pct = 0.0

        # Check weekend
        if self._is_weekend(local_time):
            applied_premiums.append({
                "type": PremiumType.WEEKEND.value,
                "percentage": self.config.weekend_premium_pct,
                "reason": f"Weekend ({local_time.strftime('%A')})",
            })
            total_pct += self.config.weekend_premium_pct

        # Check night
        if self._is_night(local_time):
            applied_premiums.append({
                "type": PremiumType.NIGHT.value,
                "percentage": self.config.night_premium_pct,
                "reason": f"Night hours ({local_time.strftime('%H:%M')})",
            })
            total_pct += self.config.night_premium_pct

        # Check holiday
        holiday = self._check_holiday(local_time.date(), worker_country)
        if holiday:
            applied_premiums.append({
                "type": PremiumType.HOLIDAY.value,
                "percentage": self.config.holiday_premium_pct,
                "reason": f"Holiday: {holiday.name}",
            })
            total_pct += self.config.holiday_premium_pct

        # Check urgency
        if deadline_hours is not None and deadline_hours <= self.config.urgent_threshold_hours:
            applied_premiums.append({
                "type": PremiumType.URGENT.value,
                "percentage": self.config.urgent_premium_pct,
                "reason": f"Urgent task ({deadline_hours}h deadline)",
            })
            total_pct += self.config.urgent_premium_pct

        # Check surge
        if self.config.enable_surge and demand_multiplier > 1.0:
            surge_pct = min(
                (demand_multiplier - 1.0) * 20.0,  # 20% per 1.0 demand increase
                self.config.surge_max_pct
            )
            if surge_pct >= self.config.surge_min_pct:
                applied_premiums.append({
                    "type": PremiumType.SURGE.value,
                    "percentage": surge_pct,
                    "reason": f"High demand (x{demand_multiplier:.1f})",
                })
                total_pct += surge_pct

        # Apply stacking rules
        if not self.config.allow_premium_stacking and len(applied_premiums) > 1:
            # Take only highest premium
            highest = max(applied_premiums, key=lambda p: p["percentage"])
            total_pct = highest["percentage"]
            applied_premiums = [highest]
            applied_premiums[0]["note"] = "Other premiums not stacked"

        # Cap total premium
        if total_pct > self.config.max_total_premium_pct:
            original_pct = total_pct
            total_pct = self.config.max_total_premium_pct
            applied_premiums.append({
                "type": "cap",
                "percentage": -(original_pct - total_pct),
                "reason": f"Premium capped at {self.config.max_total_premium_pct}%",
            })

        # Calculate amounts
        premium_amount = base_amount * (total_pct / 100)
        total_amount = base_amount + premium_amount

        return TimePremium(
            base_amount=base_amount,
            premium_amount=round(premium_amount, 2),
            total_amount=round(total_amount, 2),
            premium_percentage=round(total_pct, 1),
            applied_premiums=applied_premiums,
            calculation_time=work_time,
            worker_timezone=worker_timezone,
        )

    def estimate_premium_for_period(
        self,
        base_amount: float,
        start_time: datetime,
        end_time: datetime,
        worker_timezone: str = "UTC",
        worker_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate average premium for a time period.

        Useful for:
        - Tasks with flexible completion times
        - Showing workers expected earnings
        - Planning task publication timing

        Args:
            base_amount: Base payment amount
            start_time: Period start
            end_time: Period end
            worker_timezone: Worker's timezone
            worker_country: Worker's country

        Returns:
            Dict with min, max, average premiums and breakdown
        """
        # Sample at hourly intervals
        premiums = []
        current = start_time

        while current <= end_time:
            premium = self.calculate_premium(
                base_amount=base_amount,
                work_time=current,
                worker_timezone=worker_timezone,
                worker_country=worker_country,
            )
            premiums.append(premium)
            current += timedelta(hours=1)

        if not premiums:
            return {
                "min_amount": base_amount,
                "max_amount": base_amount,
                "avg_amount": base_amount,
                "min_premium_pct": 0.0,
                "max_premium_pct": 0.0,
                "avg_premium_pct": 0.0,
                "samples": 0,
            }

        min_premium = min(premiums, key=lambda p: p.total_amount)
        max_premium = max(premiums, key=lambda p: p.total_amount)
        avg_amount = sum(p.total_amount for p in premiums) / len(premiums)
        avg_pct = sum(p.premium_percentage for p in premiums) / len(premiums)

        return {
            "min_amount": min_premium.total_amount,
            "max_amount": max_premium.total_amount,
            "avg_amount": round(avg_amount, 2),
            "min_premium_pct": min_premium.premium_percentage,
            "max_premium_pct": max_premium.premium_percentage,
            "avg_premium_pct": round(avg_pct, 1),
            "samples": len(premiums),
            "best_time": max_premium.calculation_time.isoformat(),
        }

    def get_premium_schedule(
        self,
        worker_timezone: str = "UTC",
        worker_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get premium schedule for a worker's week.

        Returns:
            Dict with premium rates by day/hour
        """
        schedule = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for day_idx, day_name in enumerate(days):
            schedule[day_name] = {
                "hours": {},
                "is_weekend": day_idx in self.config.weekend_days,
            }

            for hour in range(24):
                # Create a sample datetime for this day/hour
                sample_time = datetime(2026, 1, 20 + day_idx, hour, 0, tzinfo=timezone.utc)

                premium = self.calculate_premium(
                    base_amount=100.0,
                    work_time=sample_time,
                    worker_timezone=worker_timezone,
                    worker_country=worker_country,
                )

                schedule[day_name]["hours"][hour] = {
                    "premium_pct": premium.premium_percentage,
                    "types": [p["type"] for p in premium.applied_premiums],
                }

        return schedule

    def get_upcoming_holidays(
        self,
        country: Optional[str] = None,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming holidays for planning.

        Args:
            country: Filter by country code
            days_ahead: Days to look ahead

        Returns:
            List of upcoming holidays with premium info
        """
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        upcoming = []

        for holiday in self.holidays:
            # Check country filter
            if country and holiday.country_codes and country not in holiday.country_codes:
                continue

            # Check if holiday falls in range (for current and next year)
            for year in [today.year, today.year + 1]:
                if holiday.year and holiday.year != year:
                    continue

                try:
                    holiday_date = date(year, holiday.month, holiday.day)
                except ValueError:
                    continue  # Invalid date (e.g., Feb 30)

                if today <= holiday_date <= end_date:
                    upcoming.append({
                        "name": holiday.name,
                        "date": holiday_date.isoformat(),
                        "day_of_week": holiday_date.strftime("%A"),
                        "premium_pct": self.config.holiday_premium_pct,
                        "countries": holiday.country_codes or ["GLOBAL"],
                    })

        # Sort by date
        upcoming.sort(key=lambda h: h["date"])

        return upcoming

    def _is_weekend(self, dt: datetime) -> bool:
        """Check if datetime falls on a weekend."""
        return dt.weekday() in self.config.weekend_days

    def _is_night(self, dt: datetime) -> bool:
        """Check if datetime falls during night hours."""
        hour = dt.hour
        if self.config.night_start_hour > self.config.night_end_hour:
            # Night spans midnight (e.g., 20:00 - 06:00)
            return hour >= self.config.night_start_hour or hour < self.config.night_end_hour
        else:
            # Night doesn't span midnight
            return self.config.night_start_hour <= hour < self.config.night_end_hour

    def _check_holiday(
        self,
        check_date: date,
        country: Optional[str] = None
    ) -> Optional[HolidayDefinition]:
        """Check if date is a holiday."""
        for holiday in self.holidays:
            # Check year if specified
            if holiday.year and holiday.year != check_date.year:
                continue

            # Check date
            if holiday.month != check_date.month or holiday.day != check_date.day:
                continue

            # Check country
            if holiday.country_codes:
                if country is None or country not in holiday.country_codes:
                    continue

            return holiday

        return None


# Convenience function
def calculate_task_premium(
    base_amount: float,
    worker_timezone: str = "UTC",
    worker_country: Optional[str] = None,
    deadline_hours: Optional[int] = None
) -> TimePremium:
    """
    Quick premium calculation for a task.

    Args:
        base_amount: Base payment amount
        worker_timezone: Worker's timezone
        worker_country: Worker's country code
        deadline_hours: Hours until deadline

    Returns:
        TimePremium with calculated amounts
    """
    calc = PremiumCalculator()
    return calc.calculate_premium(
        base_amount=base_amount,
        worker_timezone=worker_timezone,
        worker_country=worker_country,
        deadline_hours=deadline_hours,
    )
