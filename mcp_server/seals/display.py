"""
Seal Display Formatting (NOW-186)

Handles formatting seals for display in various contexts:
- Worker profile cards
- Task listings (worker has X seals)
- Verification badges
- Mobile-friendly compact views
- API responses

Display Contexts:
1. PROFILE: Full seal display on worker profile
2. CARD: Compact view for worker cards in listings
3. BADGE: Single badge display
4. API: Structured data for frontend rendering
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from dataclasses import dataclass

from .types import (
    Seal,
    SealBundle,
    SealCategory,
    SealStatus,
    get_requirement,
    SEAL_REQUIREMENTS,
)

logger = logging.getLogger(__name__)


@dataclass
class DisplayConfig:
    """Configuration for seal display formatting."""
    locale: str = "es"  # "es" or "en"
    include_expired: bool = False
    max_seals_per_category: int = 10
    show_tier: bool = True
    show_expiration: bool = True
    compact_mode: bool = False


class SealDisplayFormatter:
    """
    Formatter for seal display in various UI contexts.

    Handles localization, formatting, and organizing seals
    for optimal display.

    Example:
        >>> formatter = SealDisplayFormatter()
        >>> profile = formatter.format_profile(bundle)
        >>> print(profile["skill_seals"][0]["display_name"])
        "Verificado: Fotografía"
    """

    # Tier display names
    TIER_NAMES = {
        1: {"en": "Bronze", "es": "Bronce"},
        2: {"en": "Silver", "es": "Plata"},
        3: {"en": "Gold", "es": "Oro"},
        4: {"en": "Platinum", "es": "Platino"},
        5: {"en": "Diamond", "es": "Diamante"},
    }

    # Category display names
    CATEGORY_NAMES = {
        SealCategory.SKILL: {"en": "Skills", "es": "Habilidades"},
        SealCategory.WORK: {"en": "Work History", "es": "Historial de Trabajo"},
        SealCategory.BEHAVIOR: {"en": "Behavior", "es": "Comportamiento"},
    }

    def __init__(self, config: Optional[DisplayConfig] = None):
        """
        Initialize formatter.

        Args:
            config: Display configuration
        """
        self.config = config or DisplayConfig()

    # =========================================================================
    # SINGLE SEAL FORMATTING
    # =========================================================================

    def format_seal(
        self,
        seal: Seal,
        context: str = "profile"
    ) -> Dict[str, Any]:
        """
        Format a single seal for display.

        Args:
            seal: Seal to format
            context: Display context (profile, card, badge, api)

        Returns:
            Dict with formatted seal data
        """
        requirement = get_requirement(seal.seal_type)
        locale = self.config.locale

        # Get localized name and description
        if requirement:
            display_name = (
                requirement.display_name_es if locale == "es"
                else requirement.display_name
            )
            description = (
                requirement.description_es if locale == "es"
                else requirement.description
            )
            icon = requirement.icon
            color = requirement.color
            tier = requirement.tier
        else:
            display_name = seal.seal_type.replace("_", " ").title()
            description = ""
            icon = "badge"
            color = "#78909C"
            tier = 1

        # Base format
        formatted = {
            "seal_type": seal.seal_type,
            "display_name": display_name,
            "category": seal.category.value,
            "status": seal.status.value,
            "is_valid": seal.is_valid,
            "icon": icon,
            "color": color,
        }

        # Add tier info
        if self.config.show_tier:
            formatted["tier"] = tier
            formatted["tier_name"] = self.TIER_NAMES.get(tier, {}).get(
                locale, f"Tier {tier}"
            )

        # Context-specific additions
        if context in ("profile", "api"):
            formatted["description"] = description
            formatted["issued_at"] = seal.issued_at.isoformat() if seal.issued_at else None

            if self.config.show_expiration and seal.expires_at:
                formatted["expires_at"] = seal.expires_at.isoformat()
                formatted["expires_in_days"] = self._days_until(seal.expires_at)
                formatted["expiration_warning"] = self._get_expiration_warning(seal.expires_at)

        if context == "badge":
            # Minimal format for badge display
            formatted = {
                "display_name": display_name,
                "icon": icon,
                "color": color,
                "tier": tier,
            }

        if context == "card" and self.config.compact_mode:
            # Very compact for cards
            formatted = {
                "name": display_name,
                "icon": icon,
                "tier": tier,
            }

        return formatted

    def _days_until(self, dt: datetime) -> int:
        """Calculate days until a datetime."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        delta = dt - datetime.now(UTC)
        return max(0, delta.days)

    def _get_expiration_warning(self, expires_at: datetime) -> Optional[str]:
        """Get expiration warning message if needed."""
        days = self._days_until(expires_at)
        locale = self.config.locale

        if days == 0:
            return "Expira hoy" if locale == "es" else "Expires today"
        elif days <= 7:
            return (
                f"Expira en {days} dias" if locale == "es"
                else f"Expires in {days} days"
            )
        elif days <= 30:
            return (
                f"Expira pronto ({days} dias)" if locale == "es"
                else f"Expiring soon ({days} days)"
            )
        return None

    # =========================================================================
    # PROFILE FORMAT
    # =========================================================================

    def format_profile(
        self,
        bundle: SealBundle,
    ) -> Dict[str, Any]:
        """
        Format seals for a worker's full profile display (NOW-186).

        Args:
            bundle: Worker's seal bundle

        Returns:
            Dict with formatted profile seal data
        """
        locale = self.config.locale

        profile = {
            "holder_id": bundle.holder_id,
            "summary": {
                "total_seals": bundle.total_count,
                "active_seals": bundle.active_count,
            },
            "skill_seals": [],
            "work_seals": [],
            "behavior_seals": [],
            "featured_seals": [],
            "category_names": {
                cat.value: self.CATEGORY_NAMES[cat][locale]
                for cat in SealCategory
            },
        }

        # Format each category
        for seal in self._filter_and_sort(bundle.skill_seals):
            profile["skill_seals"].append(self.format_seal(seal, "profile"))

        for seal in self._filter_and_sort(bundle.work_seals):
            profile["work_seals"].append(self.format_seal(seal, "profile"))

        for seal in self._filter_and_sort(bundle.behavior_seals):
            profile["behavior_seals"].append(self.format_seal(seal, "profile"))

        # Select featured seals (top tier from each category)
        profile["featured_seals"] = self._select_featured(bundle)

        return profile

    def _filter_and_sort(self, seals: List[Seal]) -> List[Seal]:
        """Filter and sort seals for display."""
        # Filter expired if configured
        if not self.config.include_expired:
            seals = [s for s in seals if s.is_valid]

        # Sort by tier (descending), then by issued date (most recent)
        seals.sort(
            key=lambda s: (
                -(get_requirement(s.seal_type).tier if get_requirement(s.seal_type) else 1),
                -(s.issued_at.timestamp() if s.issued_at else 0)
            )
        )

        # Limit per category
        return seals[:self.config.max_seals_per_category]

    def _select_featured(self, bundle: SealBundle) -> List[Dict[str, Any]]:
        """Select featured seals for prominent display."""
        featured = []

        # Get highest tier seal from each category
        for seals in [bundle.skill_seals, bundle.work_seals, bundle.behavior_seals]:
            valid_seals = [s for s in seals if s.is_valid]
            if not valid_seals:
                continue

            # Find highest tier
            best = max(
                valid_seals,
                key=lambda s: (
                    get_requirement(s.seal_type).tier if get_requirement(s.seal_type) else 1
                )
            )
            featured.append(self.format_seal(best, "badge"))

        return featured[:3]  # Max 3 featured

    # =========================================================================
    # CARD FORMAT (COMPACT)
    # =========================================================================

    def format_card(
        self,
        bundle: SealBundle,
        max_display: int = 3,
    ) -> Dict[str, Any]:
        """
        Format seals for a compact worker card.

        Shows just the highlights for listing views.

        Args:
            bundle: Worker's seal bundle
            max_display: Maximum seals to show

        Returns:
            Dict with card-formatted seal data
        """
        locale = self.config.locale

        card = {
            "total_seals": bundle.active_count,
            "seals": [],
            "more_count": 0,
        }

        # Get all valid seals, sorted by tier
        all_seals = [s for s in bundle.all_seals if s.is_valid]
        all_seals.sort(
            key=lambda s: -(
                get_requirement(s.seal_type).tier if get_requirement(s.seal_type) else 1
            )
        )

        # Take top N
        display_seals = all_seals[:max_display]
        card["more_count"] = max(0, len(all_seals) - max_display)

        for seal in display_seals:
            req = get_requirement(seal.seal_type)
            card["seals"].append({
                "icon": req.icon if req else "badge",
                "color": req.color if req else "#78909C",
                "tier": req.tier if req else 1,
                "tooltip": (
                    req.display_name_es if locale == "es" and req
                    else req.display_name if req
                    else seal.seal_type
                ),
            })

        # Generate summary text
        if bundle.active_count == 0:
            card["summary_text"] = (
                "Sin sellos verificados" if locale == "es"
                else "No verified seals"
            )
        elif bundle.active_count == 1:
            card["summary_text"] = (
                "1 sello verificado" if locale == "es"
                else "1 verified seal"
            )
        else:
            card["summary_text"] = (
                f"{bundle.active_count} sellos verificados" if locale == "es"
                else f"{bundle.active_count} verified seals"
            )

        return card

    # =========================================================================
    # BADGE FORMAT
    # =========================================================================

    def format_badge(
        self,
        seal: Seal,
        size: str = "medium",
    ) -> Dict[str, Any]:
        """
        Format a single seal as a displayable badge.

        Args:
            seal: Seal to format
            size: Badge size (small, medium, large)

        Returns:
            Dict with badge display data
        """
        req = get_requirement(seal.seal_type)
        locale = self.config.locale

        badge = {
            "seal_type": seal.seal_type,
            "name": (
                req.display_name_es if locale == "es" and req
                else req.display_name if req
                else seal.seal_type
            ),
            "icon": req.icon if req else "badge",
            "color": req.color if req else "#78909C",
            "tier": req.tier if req else 1,
            "size": size,
            "is_valid": seal.is_valid,
        }

        # Size-specific styling hints
        size_config = {
            "small": {"icon_size": 16, "show_text": False},
            "medium": {"icon_size": 24, "show_text": True},
            "large": {"icon_size": 32, "show_text": True},
        }
        badge.update(size_config.get(size, size_config["medium"]))

        return badge

    # =========================================================================
    # API FORMAT
    # =========================================================================

    def format_api_response(
        self,
        bundle: SealBundle,
    ) -> Dict[str, Any]:
        """
        Format seals for API response.

        Structured format for frontend consumption.

        Args:
            bundle: Worker's seal bundle

        Returns:
            Dict with API-formatted seal data
        """
        return {
            "holder_id": bundle.holder_id,
            "stats": {
                "total": bundle.total_count,
                "active": bundle.active_count,
                "by_category": {
                    "skill": len([s for s in bundle.skill_seals if s.is_valid]),
                    "work": len([s for s in bundle.work_seals if s.is_valid]),
                    "behavior": len([s for s in bundle.behavior_seals if s.is_valid]),
                },
            },
            "seals": [
                self.format_seal(seal, "api")
                for seal in bundle.all_seals
                if seal.is_valid or self.config.include_expired
            ],
            "meta": {
                "locale": self.config.locale,
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }

    # =========================================================================
    # TEXT FORMATTING
    # =========================================================================

    def format_seal_list_text(
        self,
        bundle: SealBundle,
    ) -> str:
        """
        Format seals as readable text (for chat/notifications).

        Args:
            bundle: Worker's seal bundle

        Returns:
            Formatted text string
        """
        locale = self.config.locale
        lines = []

        if locale == "es":
            lines.append(f"Sellos Verificados ({bundle.active_count} activos)")
        else:
            lines.append(f"Verified Seals ({bundle.active_count} active)")

        lines.append("")

        # Group by category
        for category, seals, category_name in [
            (SealCategory.SKILL, bundle.skill_seals, "Habilidades" if locale == "es" else "Skills"),
            (SealCategory.WORK, bundle.work_seals, "Historial" if locale == "es" else "Work History"),
            (SealCategory.BEHAVIOR, bundle.behavior_seals, "Comportamiento" if locale == "es" else "Behavior"),
        ]:
            valid_seals = [s for s in seals if s.is_valid]
            if not valid_seals:
                continue

            lines.append(f"## {category_name}")

            for seal in valid_seals:
                req = get_requirement(seal.seal_type)
                name = (
                    req.display_name_es if locale == "es" and req
                    else req.display_name if req
                    else seal.seal_type
                )
                tier = req.tier if req else 1
                tier_icon = ["", "*", "**", "***", "****", "*****"][tier]

                lines.append(f"  - {name} {tier_icon}")

            lines.append("")

        return "\n".join(lines)

    def format_seal_notification(
        self,
        seal: Seal,
        event: str = "issued",
    ) -> Dict[str, str]:
        """
        Format seal event for notification.

        Args:
            seal: Seal involved in event
            event: Event type (issued, expired, revoked, expiring)

        Returns:
            Dict with title and body for notification
        """
        locale = self.config.locale
        req = get_requirement(seal.seal_type)

        name = (
            req.display_name_es if locale == "es" and req
            else req.display_name if req
            else seal.seal_type
        )

        if event == "issued":
            title = "Nuevo sello obtenido!" if locale == "es" else "New seal earned!"
            body = (
                f"Has obtenido el sello: {name}" if locale == "es"
                else f"You earned the seal: {name}"
            )
        elif event == "expired":
            title = "Sello expirado" if locale == "es" else "Seal expired"
            body = (
                f"Tu sello ha expirado: {name}" if locale == "es"
                else f"Your seal has expired: {name}"
            )
        elif event == "revoked":
            title = "Sello revocado" if locale == "es" else "Seal revoked"
            body = (
                f"Tu sello ha sido revocado: {name}" if locale == "es"
                else f"Your seal has been revoked: {name}"
            )
        elif event == "expiring":
            days = self._days_until(seal.expires_at) if seal.expires_at else 0
            title = "Sello por expirar" if locale == "es" else "Seal expiring soon"
            body = (
                f"Tu sello {name} expira en {days} dias" if locale == "es"
                else f"Your {name} seal expires in {days} days"
            )
        else:
            title = "Actualizacion de sello" if locale == "es" else "Seal update"
            body = name

        return {
            "title": title,
            "body": body,
            "icon": req.icon if req else "badge",
            "color": req.color if req else "#78909C",
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def format_seals_for_profile(
    bundle: SealBundle,
    locale: str = "es"
) -> Dict[str, Any]:
    """
    Convenience function to format seals for profile display.

    Args:
        bundle: Worker's seal bundle
        locale: Language locale

    Returns:
        Formatted profile data
    """
    config = DisplayConfig(locale=locale)
    formatter = SealDisplayFormatter(config)
    return formatter.format_profile(bundle)


def format_seals_for_card(
    bundle: SealBundle,
    locale: str = "es",
    max_display: int = 3
) -> Dict[str, Any]:
    """
    Convenience function to format seals for card display.

    Args:
        bundle: Worker's seal bundle
        locale: Language locale
        max_display: Max seals to show

    Returns:
        Formatted card data
    """
    config = DisplayConfig(locale=locale, compact_mode=True)
    formatter = SealDisplayFormatter(config)
    return formatter.format_card(bundle, max_display)


def get_seal_display_name(
    seal_type: str,
    locale: str = "es"
) -> str:
    """
    Get display name for a seal type.

    Args:
        seal_type: Seal type string
        locale: Language locale

    Returns:
        Localized display name
    """
    req = get_requirement(seal_type)
    if req:
        return req.display_name_es if locale == "es" else req.display_name
    return seal_type.replace("_", " ").title()
