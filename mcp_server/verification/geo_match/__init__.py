"""
Geographic Matching module for Execution Market verification.

Hybrid resolver that answers: "does a submission's GPS lat/lng match the
task's location hint (or fixed lat/lng/radius)?"

Resolution order: cache (future) -> static US ZIP CSV -> static GeoNames
cities -> Nominatim (OSM) fallback.

Public API:
    from mcp_server.verification.geo_match import GeoMatcher, MatchMode, MatchResult

    matcher = GeoMatcher()
    result = matcher.match(
        submission_lat=25.97022,
        submission_lng=-80.19489,
        mode=MatchMode.CITY,
        location_hint="Miami, FL, USA",
    )

See the master plan (`docs/planning/MASTER_PLAN_GEO_MATCHING_2026_04_16.md`)
for context and design rationale.
"""

from .resolver import GeoMatcher, MatchMode, MatchResult

__all__ = ["GeoMatcher", "MatchMode", "MatchResult"]
