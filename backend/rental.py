"""
Rental estimate module.

Estimates monthly rent and gross yield from a capital value estimate.

Two approaches (blended):
  1. Gross yield benchmark  — capital value × regional gross yield
  2. Per-bedroom rate       — bedroom-count-adjusted market rate

The blend weight favours approach 1 when a type-specific yield is
available, and approach 2 when the property type is unknown.
"""
from __future__ import annotations

from .constants import DEFAULT_GROSS_YIELD, GROSS_YIELD_BY_TYPE
from .models import PropertyType, SubjectProperty


# ─────────────────────────────────────────────────────────────────────
# Per-bedroom monthly rent benchmarks (London-weighted UK avg, 2024)
# Source: Zoopla Rental Market Report Q4 2024
# ─────────────────────────────────────────────────────────────────────
_MONTHLY_RENT_BY_BEDS_PENCE: dict[int, int] = {
    0: 110_000,    # studio:  £1,100/mo
    1: 135_000,    # 1-bed:   £1,350/mo
    2: 175_000,    # 2-bed:   £1,750/mo
    3: 215_000,    # 3-bed:   £2,150/mo
    4: 285_000,    # 4-bed:   £2,850/mo
    5: 360_000,    # 5-bed:   £3,600/mo
}
_DEFAULT_RENT_PENCE: int = 175_000    # 2-bed fallback


def _yield_based_rent(
    estimated_value: int,
    property_type: PropertyType | None,
) -> tuple[int, float]:
    """
    Returns (monthly_rent_pence, annual_gross_yield_pct).
    """
    gross_yield = GROSS_YIELD_BY_TYPE.get(
        property_type or PropertyType.OTHER,
        DEFAULT_GROSS_YIELD,
    )
    annual_rent  = estimated_value * gross_yield
    monthly_rent = int(annual_rent / 12)
    return monthly_rent, round(gross_yield * 100, 2)


def _bedroom_based_rent(bedrooms: int | None) -> int:
    """
    Returns monthly_rent_pence from per-bedroom benchmarks.
    """
    if bedrooms is None:
        return _DEFAULT_RENT_PENCE
    beds = min(bedrooms, 5)   # cap at 5+ benchmark
    return _MONTHLY_RENT_BY_BEDS_PENCE.get(beds, _DEFAULT_RENT_PENCE)


def estimate_rental(
    subject: SubjectProperty,
    estimated_value: int,
) -> tuple[int, float]:
    """
    Blend yield-based and bedroom-based rent estimates.

    Blend weights:
      - Known type:    70% yield-based, 30% bedroom-based
      - Unknown type:  40% yield-based, 60% bedroom-based

    Returns:
        (monthly_rent_pence, gross_yield_pct)
    """
    yield_rent, gross_yield = _yield_based_rent(estimated_value, subject.property_type)
    bed_rent                = _bedroom_based_rent(subject.bedrooms)

    if subject.property_type and subject.property_type != PropertyType.OTHER:
        w_yield, w_bed = 0.70, 0.30
    else:
        w_yield, w_bed = 0.40, 0.60

    blended_monthly = int(yield_rent * w_yield + bed_rent * w_bed)

    # Recalculate yield from the blended rent
    annual_rent = blended_monthly * 12
    actual_yield = round((annual_rent / estimated_value) * 100, 2) if estimated_value > 0 else gross_yield

    return blended_monthly, actual_yield
