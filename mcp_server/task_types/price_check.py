"""
Execution Market Price Check Task Type

Task type for price verification tasks:
- Product price verification
- Price comparison across stores
- Sale/promotion verification
- Price trend monitoring

Evidence requirements:
- Product photos showing price tags
- OCR extraction of prices
- Location verification

Validation includes:
- Photo shows clear price tag
- OCR extraction verification
- GPS at store location
- Price format validation
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict, Tuple
import re

from .base import (
    TaskType,
    TaskContext,
    EvidenceSpec,
    EvidenceCategory,
    ValidationResult,
    BountyRecommendation,
    TimeEstimate,
)


class PriceType(str, Enum):
    """Types of prices to capture."""
    REGULAR = "regular"
    SALE = "sale"
    MEMBER = "member"
    CLEARANCE = "clearance"
    UNIT = "unit"


@dataclass
class ProductSpec:
    """
    Specification for a product to price check.

    Attributes:
        name: Product name/description
        sku: Optional SKU/barcode
        expected_price_range: Optional (min, max) expected price
        require_photo: Whether photo is required for this product
        notes: Additional notes about the product
    """
    name: str
    sku: Optional[str] = None
    expected_price_range: Optional[Tuple[Decimal, Decimal]] = None
    require_photo: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "sku": self.sku,
            "expected_price_range": (
                [str(self.expected_price_range[0]), str(self.expected_price_range[1])]
                if self.expected_price_range else None
            ),
            "require_photo": self.require_photo,
            "notes": self.notes,
        }


class PriceCheckEvidence(TypedDict, total=False):
    """Evidence structure for price check tasks."""
    # Product prices
    prices: Dict[str, Dict[str, Any]]  # product_name -> {price, sale_price, photo_url, etc.}

    # Location evidence
    store_name: str
    store_photo_url: Optional[str]
    location_gps_lat: Optional[float]
    location_gps_lng: Optional[float]
    visit_timestamp: str

    # OCR data (if extracted)
    ocr_results: Optional[Dict[str, str]]

    # Notes
    notes: Optional[str]
    unavailable_products: Optional[List[str]]


@dataclass
class PriceCheckConfig:
    """Configuration for price check validation."""
    # Location validation
    require_gps: bool = True
    gps_radius_meters: float = 200.0

    # Price validation
    require_photos: bool = True
    validate_price_format: bool = True
    currency_symbol: str = "$"
    allowed_currencies: List[str] = field(default_factory=lambda: ["$", "USD", "MXN", "EUR"])

    # OCR settings
    require_ocr_verification: bool = False
    min_ocr_confidence: float = 0.8

    # Product settings
    allow_unavailable: bool = True
    require_unavailable_photo: bool = True


class PriceCheckTask(TaskType[PriceCheckEvidence]):
    """
    Task type for price verification.

    Handles validation of price check evidence including photo
    verification, OCR extraction, and price format validation.

    Examples:
    - "Check price of Product X at Store Y"
    - "Compare prices of items across 3 stores"
    - "Verify sale prices match advertisement"
    """

    type_name = "price_check"
    display_name = "Price Check"
    description = "Product price verification with photo evidence and optional OCR"
    category = "physical_presence"

    # Base pricing
    BASE_BOUNTY = Decimal("2.50")
    MAX_BOUNTY = Decimal("20.00")
    PER_PRODUCT_RATE = Decimal("0.75")

    # Time estimates
    BASE_TIME = 15
    PER_PRODUCT_TIME = 3

    def __init__(
        self,
        products: Optional[List[ProductSpec]] = None,
        config: Optional[PriceCheckConfig] = None,
        target_store: Optional[str] = None,
    ):
        """
        Initialize price check task type.

        Args:
            products: List of products to price check
            config: Validation configuration
            target_store: Target store name
        """
        super().__init__()
        self.products = products or []
        self.config = config or PriceCheckConfig()
        self.target_store = target_store

    def add_product(self, product: ProductSpec) -> "PriceCheckTask":
        """Add a product to check (builder pattern)."""
        self.products.append(product)
        return self

    def get_required_evidence(self) -> List[EvidenceSpec]:
        """Get required evidence for price check task."""
        evidence = []

        # Store location verification
        if self.config.require_gps:
            evidence.append(
                EvidenceSpec(
                    category=EvidenceCategory.PHOTO_GEO,
                    required=True,
                    description="Photo of store entrance/sign with GPS",
                    validation_rules={
                        "max_distance_meters": self.config.gps_radius_meters,
                    },
                )
            )

        # Product price photos
        if self.config.require_photos:
            evidence.append(
                EvidenceSpec(
                    category=EvidenceCategory.PHOTO,
                    required=True,
                    description="Photos of products showing price tags clearly",
                    min_count=len(self.products) if self.products else 1,
                    max_count=len(self.products) * 2 if self.products else 20,
                    validation_rules={
                        "show_price_tag": True,
                    },
                )
            )

        # Price data
        evidence.append(
            EvidenceSpec(
                category=EvidenceCategory.NUMERIC_VALUE,
                required=True,
                description="Recorded prices for each product",
                validation_rules={
                    "products": [p.to_dict() for p in self.products],
                },
            )
        )

        return evidence

    def get_optional_evidence(self) -> List[EvidenceSpec]:
        """Get optional evidence for price check task."""
        return [
            EvidenceSpec(
                category=EvidenceCategory.SCREENSHOT,
                required=False,
                description="Screenshot of online price for comparison",
            ),
            EvidenceSpec(
                category=EvidenceCategory.TEXT_RESPONSE,
                required=False,
                description="Notes about pricing, promotions, or availability",
            ),
        ]

    def validate_evidence(
        self,
        evidence: PriceCheckEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """
        Validate price check evidence.

        Checks:
        1. Location verification (GPS)
        2. Price data for all required products
        3. Price format validation
        4. Photo evidence for each product
        5. OCR verification (if enabled)
        """
        result = ValidationResult.success()

        # 1. Validate location
        if self.config.require_gps and context.has_location():
            location_result = self._validate_location(evidence, context)
            result = result.merge(location_result)

        # 2. Validate prices for all products
        prices_result = self._validate_prices(evidence)
        result = result.merge(prices_result)

        # 3. Validate price formats
        if self.config.validate_price_format:
            format_result = self._validate_price_formats(evidence)
            result = result.merge(format_result)

        # 4. Validate OCR (if enabled)
        if self.config.require_ocr_verification:
            ocr_result = self._validate_ocr(evidence)
            result = result.merge(ocr_result)

        return result

    def _validate_location(
        self,
        evidence: PriceCheckEvidence,
        context: TaskContext,
    ) -> ValidationResult:
        """Validate location evidence."""
        lat = evidence.get("location_gps_lat")
        lng = evidence.get("location_gps_lng")

        if lat is None or lng is None:
            return ValidationResult.failure(
                errors=["Location GPS required but not provided"],
            )

        if context.location_lat and context.location_lng:
            distance = self._haversine_distance(
                lat, lng,
                context.location_lat, context.location_lng,
            )

            if distance > self.config.gps_radius_meters:
                return ValidationResult.failure(
                    errors=[
                        f"Location ({distance:.0f}m) outside acceptable radius "
                        f"({self.config.gps_radius_meters}m)"
                    ],
                )

            return ValidationResult.success(
                details={
                    "location_verified": True,
                    "distance_meters": distance,
                    "store_name": evidence.get("store_name"),
                },
            )

        return ValidationResult.success()

    def _validate_prices(
        self,
        evidence: PriceCheckEvidence,
    ) -> ValidationResult:
        """Validate price data for all products."""
        prices = evidence.get("prices", {})
        unavailable = evidence.get("unavailable_products", [])
        errors = []
        warnings = []

        for product in self.products:
            product_name = product.name

            # Check if product is reported as unavailable
            if product_name in unavailable:
                if not self.config.allow_unavailable:
                    errors.append(f"Product '{product_name}' reported unavailable but must be found")
                continue

            # Check price data exists
            if product_name not in prices:
                errors.append(f"Missing price data for: {product_name}")
                continue

            product_data = prices[product_name]

            # Check price value exists
            price = product_data.get("price")
            if price is None:
                errors.append(f"No price recorded for: {product_name}")
                continue

            # Validate price against expected range
            if product.expected_price_range:
                try:
                    price_decimal = Decimal(str(price))
                    min_price, max_price = product.expected_price_range

                    if price_decimal < min_price or price_decimal > max_price:
                        warnings.append(
                            f"Price for '{product_name}' (${price}) outside "
                            f"expected range (${min_price}-${max_price})"
                        )
                except (InvalidOperation, ValueError):
                    errors.append(f"Invalid price value for '{product_name}': {price}")

            # Check photo exists if required
            if product.require_photo and self.config.require_photos:
                if not product_data.get("photo_url"):
                    errors.append(f"Photo required for: {product_name}")

        if errors:
            return ValidationResult.failure(errors=errors)
        elif warnings:
            return ValidationResult.warning(
                warnings=warnings,
                details={"prices_validated": True},
            )

        return ValidationResult.success(
            details={
                "prices_validated": True,
                "products_found": len(prices),
                "products_unavailable": len(unavailable),
            },
        )

    def _validate_price_formats(
        self,
        evidence: PriceCheckEvidence,
    ) -> ValidationResult:
        """Validate price format consistency."""
        prices = evidence.get("prices", {})
        warnings = []

        for product_name, product_data in prices.items():
            price = product_data.get("price")
            if price is None:
                continue

            # Check if price is a valid number
            try:
                price_decimal = Decimal(str(price))

                # Check for reasonable price (not negative, not astronomical)
                if price_decimal < 0:
                    warnings.append(f"Negative price for '{product_name}'")
                elif price_decimal > 100000:
                    warnings.append(f"Unusually high price for '{product_name}': {price}")

            except (InvalidOperation, ValueError):
                warnings.append(f"Invalid price format for '{product_name}': {price}")

        if warnings:
            return ValidationResult.warning(warnings=warnings)

        return ValidationResult.success()

    def _validate_ocr(
        self,
        evidence: PriceCheckEvidence,
    ) -> ValidationResult:
        """Validate OCR-extracted prices match reported prices."""
        ocr_results = evidence.get("ocr_results", {})
        prices = evidence.get("prices", {})
        warnings = []

        if not ocr_results:
            return ValidationResult.warning(
                warnings=["OCR verification requested but no OCR data provided"],
            )

        for product_name, reported_price_data in prices.items():
            reported_price = reported_price_data.get("price")
            ocr_price_str = ocr_results.get(product_name)

            if ocr_price_str:
                # Extract numeric value from OCR string
                ocr_price = self._extract_price_from_string(ocr_price_str)

                if ocr_price is not None and reported_price is not None:
                    try:
                        reported = Decimal(str(reported_price))
                        ocr = Decimal(str(ocr_price))

                        # Allow small difference (rounding, etc.)
                        if abs(reported - ocr) > Decimal("0.10"):
                            warnings.append(
                                f"OCR price (${ocr}) differs from reported price "
                                f"(${reported}) for '{product_name}'"
                            )
                    except (InvalidOperation, ValueError):
                        pass

        if warnings:
            return ValidationResult.warning(
                warnings=warnings,
                details={"ocr_validation": "warnings"},
            )

        return ValidationResult.success(
            details={"ocr_validation": "passed"},
        )

    def _extract_price_from_string(self, price_str: str) -> Optional[float]:
        """Extract numeric price from string (handles currency symbols, etc.)."""
        if not price_str:
            return None

        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[^\d.,]', '', price_str)

        # Handle different decimal separators
        # If comma is last, treat as decimal separator
        if ',' in cleaned and '.' not in cleaned:
            cleaned = cleaned.replace(',', '.')
        elif ',' in cleaned and '.' in cleaned:
            # Remove thousands separator (whichever comes first)
            if cleaned.index(',') < cleaned.index('.'):
                cleaned = cleaned.replace(',', '')
            else:
                cleaned = cleaned.replace('.', '').replace(',', '.')

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance between two points."""
        import math

        R = 6371000

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def get_bounty_recommendation(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> BountyRecommendation:
        """Get bounty recommendation for price check task."""
        base = self.BASE_BOUNTY

        # Per-product bonus
        product_count = len(self.products)
        product_bonus = self.PER_PRODUCT_RATE * Decimal(str(max(0, product_count - 1)))

        # Complexity factor
        complexity_factor = Decimal(str(1 + (complexity - 1) * 0.15))

        # Urgency factor
        urgency_factors = {
            "flexible": Decimal("0.9"),
            "normal": Decimal("1.0"),
            "urgent": Decimal("1.3"),
        }
        urgency_factor = urgency_factors.get(context.urgency, Decimal("1.0"))

        # Location factor
        location_factor = Decimal("1.0")
        if context.metadata.get("location_type") == "rural":
            location_factor = Decimal("1.2")

        suggested = (base + product_bonus) * complexity_factor * urgency_factor * location_factor
        suggested = min(suggested, self.MAX_BOUNTY).quantize(Decimal("0.25"))

        return BountyRecommendation(
            min_usd=base,
            max_usd=self.MAX_BOUNTY,
            suggested_usd=suggested,
            factors={
                "base": base,
                "product_count": Decimal(str(product_count)),
                "product_bonus": product_bonus,
                "complexity": complexity_factor,
                "urgency": urgency_factor,
                "location": location_factor,
            },
            reasoning=f"Base ${base} + {product_count} products at ${self.PER_PRODUCT_RATE}/product",
        )

    def get_time_estimate(
        self,
        context: TaskContext,
        complexity: int = 1,
    ) -> TimeEstimate:
        """Get time estimate for price check task."""
        base = self.BASE_TIME

        # Time per product
        product_count = len(self.products)
        product_time = self.PER_PRODUCT_TIME * product_count

        typical = base + product_time

        # Location factor
        location_factors = {
            "urban_core": 0.8,
            "urban": 1.0,
            "suburban": 1.2,
            "rural": 1.5,
        }
        location_factor = location_factors.get(
            context.metadata.get("location_type", "urban"),
            1.0,
        )

        typical = int(typical * location_factor)

        return TimeEstimate(
            min_minutes=int(typical * 0.5),
            max_minutes=int(typical * 2.5),
            typical_minutes=typical,
            factors={
                "base_minutes": base,
                "product_count": product_count,
                "product_time": product_time,
                "location_type": context.metadata.get("location_type", "urban"),
            },
        )

    def get_instructions_template(self) -> str:
        """Get instruction template for price check task."""
        return """
## Price Check Task

Visit {store_name} and check the prices of the following products.

### Products to Check:
{products_list}

### Instructions:
1. Go to {store_name}
2. For each product:
   - Locate the product
   - Take a clear photo showing the product AND price tag
   - Record the exact price
   - Note if product is on sale or unavailable

### Photo Requirements:
- Photo must clearly show the price tag
- Include the product name/packaging in the photo
- Ensure price numbers are legible

### What to Record:
- Regular price
- Sale price (if applicable)
- Unit price (if displayed)
- Any promotional information

### If Product is Unavailable:
- Take a photo of the empty shelf/area
- Note in comments that product was not found

### Location:
{store_address}

### Deadline:
{deadline}
        """.strip()

    def post_process(
        self,
        evidence: PriceCheckEvidence,
        validation_result: ValidationResult,
        context: TaskContext,
    ) -> Dict[str, Any]:
        """Extract structured data from price check evidence."""
        prices = evidence.get("prices", {})
        unavailable = evidence.get("unavailable_products", [])

        # Calculate statistics
        price_values = []
        for product_data in prices.values():
            price = product_data.get("price")
            if price is not None:
                try:
                    price_values.append(float(price))
                except (ValueError, TypeError):
                    pass

        avg_price = sum(price_values) / len(price_values) if price_values else None
        min_price = min(price_values) if price_values else None
        max_price = max(price_values) if price_values else None

        return {
            "store_name": evidence.get("store_name") or self.target_store,
            "visit_timestamp": evidence.get("visit_timestamp"),
            "products_checked": len(prices),
            "products_unavailable": unavailable,
            "prices": {
                name: data.get("price")
                for name, data in prices.items()
            },
            "sale_prices": {
                name: data.get("sale_price")
                for name, data in prices.items()
                if data.get("sale_price")
            },
            "statistics": {
                "average_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
            },
            "location_verified": validation_result.details.get("location_verified", False),
            "notes": evidence.get("notes"),
        }


# Factory function for common price check scenarios
def create_competitive_price_check(
    products: List[str],
    competitor_store: str,
) -> PriceCheckTask:
    """
    Create a competitive price check task.

    Args:
        products: List of product names to check
        competitor_store: Store to check prices at

    Returns:
        Configured PriceCheckTask
    """
    product_specs = [
        ProductSpec(
            name=product,
            require_photo=True,
        )
        for product in products
    ]

    return PriceCheckTask(
        products=product_specs,
        config=PriceCheckConfig(
            require_gps=True,
            require_photos=True,
        ),
        target_store=competitor_store,
    )


def create_sale_verification_task(
    products: List[Tuple[str, Decimal, Decimal]],  # (name, regular_price, expected_sale_price)
    store_name: str,
) -> PriceCheckTask:
    """
    Create a sale price verification task.

    Args:
        products: List of (name, regular_price, expected_sale_price) tuples
        store_name: Store to verify sale prices at

    Returns:
        Configured PriceCheckTask
    """
    product_specs = [
        ProductSpec(
            name=name,
            expected_price_range=(sale_price * Decimal("0.9"), sale_price * Decimal("1.1")),
            require_photo=True,
            notes=f"Regular price: ${regular_price}, Expected sale: ${sale_price}",
        )
        for name, regular_price, sale_price in products
    ]

    return PriceCheckTask(
        products=product_specs,
        config=PriceCheckConfig(
            require_gps=True,
            require_photos=True,
        ),
        target_store=store_name,
    )
