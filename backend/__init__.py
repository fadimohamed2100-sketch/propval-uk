"""
seeder/__init__.py
~~~~~~~~~~~~~~~~~~
Also exports a mock data lookup layer so the valuation service can
return seed data instead of hitting external APIs in development.
"""
from __future__ import annotations

from .uk_property_data import (
    AREA_PROFILES,
    COMPARABLE_SALES,
    PROPERTIES,
    RENTAL_LISTINGS,
    VALUATIONS,
    AreaProfile,
)


def get_area_profile(postcode: str) -> AreaProfile | None:
    """Return the AreaProfile whose prefix matches a postcode."""
    prefix = postcode.strip().upper()
    # Try longest match first
    for length in (4, 3, 2):
        candidate = prefix[:length].rstrip()
        for profile in AREA_PROFILES:
            if profile.postcode_prefix == candidate:
                return profile
    return None


def get_mock_market_data(postcode: str) -> dict:
    """
    Return market stats dict for a postcode.
    Used by the valuation service when MOCK_MODE=true.
    """
    profile = get_area_profile(postcode)
    if not profile:
        return {}
    return {
        "area":             profile.area,
        "asking_price_pct": profile.asking_price_pct,
        "weeks_on_market":  profile.weeks_on_market,
        "searches":         f"{profile.annual_searches:,}",
        "search_area":      profile.postcode_prefix,
        "postcode_sector":  profile.postcode_prefix,
        "hpi_5yr_pct":      profile.hpi_5yr_pct,
        "gross_yield":      profile.gross_yield,
    }


__all__ = [
    "AREA_PROFILES",
    "COMPARABLE_SALES",
    "PROPERTIES",
    "RENTAL_LISTINGS",
    "VALUATIONS",
    "AreaProfile",
    "get_area_profile",
    "get_mock_market_data",
]
