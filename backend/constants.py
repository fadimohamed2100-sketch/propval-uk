"""
Market constants and regional benchmarks (UK, 2024 calibration).

These are the "priors" the engine falls back on when data is thin.
In a production system these would be updated from a market data feed
(e.g. HPI monthly release, Rightmove indices).
"""
from __future__ import annotations
from dataclasses import dataclass
from .models import PropertyType


# ─────────────────────────────────────────────────────────────────────
# ANNUAL HOUSE PRICE GROWTH (HPI, compound)
# Source: ONS UK HPI, trailing 10-year average by region
# ─────────────────────────────────────────────────────────────────────
ANNUAL_HPI_GROWTH: dict[str, float] = {
    # Outward postcode prefix → annual growth rate
    "SW": 0.043, "SE": 0.041, "W":  0.044, "WC": 0.042,
    "EC": 0.040, "E":  0.044, "N":  0.046, "NW": 0.045,
    "EN": 0.039, "HA": 0.037, "UB": 0.036, "TW": 0.038,
    "KT": 0.040, "CR": 0.038, "BR": 0.037, "DA": 0.036,
    "IG": 0.035, "RM": 0.034,
    "M":  0.035, "LS": 0.033, "B":  0.031, "BS": 0.030,
    "CF": 0.028, "EH": 0.036, "G":  0.030,
}
DEFAULT_ANNUAL_GROWTH: float = 0.032   # national fallback


# ─────────────────────────────────────────────────────────────────────
# GROSS RENTAL YIELDS by property type
# Source: Savills / Zoopla rental tracker, Q4 2024
# ─────────────────────────────────────────────────────────────────────
GROSS_YIELD_BY_TYPE: dict[PropertyType, float] = {
    PropertyType.FLAT:          0.056,
    PropertyType.MAISONETTE:    0.053,
    PropertyType.TERRACED:      0.047,
    PropertyType.SEMI_DETACHED: 0.043,
    PropertyType.BUNGALOW:      0.041,
    PropertyType.DETACHED:      0.038,
    PropertyType.OTHER:         0.045,
}
DEFAULT_GROSS_YIELD: float = 0.045


# ─────────────────────────────────────────────────────────────────────
# PRICE PER M² BASELINE (£ pence / m²) by property type
# Derived from Land Registry + EPC dataset median, UK national
# ─────────────────────────────────────────────────────────────────────
PRICE_PER_M2_PENCE: dict[PropertyType, int] = {
    PropertyType.DETACHED:      350_000,    # £3,500/m²
    PropertyType.SEMI_DETACHED: 310_000,    # £3,100/m²
    PropertyType.TERRACED:      295_000,    # £2,950/m²
    PropertyType.FLAT:          380_000,    # £3,800/m² (London premium)
    PropertyType.BUNGALOW:      320_000,    # £3,200/m²
    PropertyType.MAISONETTE:    355_000,    # £3,550/m²
    PropertyType.OTHER:         290_000,
}
DEFAULT_PRICE_PER_M2: int = 295_000


# ─────────────────────────────────────────────────────────────────────
# BEDROOM COUNT ADJUSTMENT — premium/discount vs 3-bed baseline
# ─────────────────────────────────────────────────────────────────────
BEDROOM_ADJUSTMENT: dict[int, float] = {
    0: -0.25,
    1: -0.15,
    2: -0.07,
    3:  0.00,  # baseline
    4: +0.10,
    5: +0.18,
    6: +0.24,
}
BEDROOM_ADJUSTMENT_DEFAULT: float = +0.28  # 7+ beds


# ─────────────────────────────────────────────────────────────────────
# FEATURE PREMIUMS / DISCOUNTS (applied to estimated value)
# ─────────────────────────────────────────────────────────────────────
FEATURE_ADJUSTMENTS: dict[str, float] = {
    "has_garden":   +0.05,
    "has_parking":  +0.03,
    "has_garage":   +0.04,
    "is_new_build": +0.08,
}

# EPC rating adjustments vs "D" baseline
EPC_ADJUSTMENTS: dict[str, float] = {
    "A": +0.04,
    "B": +0.03,
    "C": +0.01,
    "D":  0.00,
    "E": -0.02,
    "F": -0.05,
    "G": -0.08,
}

# Leasehold discount bands
LEASE_DISCOUNTS: list[tuple[int, float]] = [
    (90,  0.00),
    (70,  0.03),
    (60,  0.07),
    (50,  0.12),
    (40,  0.20),
    (0,   0.30),
]


# ─────────────────────────────────────────────────────────────────────
# COMPARABLE SCORING WEIGHTS
# ─────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CompScoringWeights:
    distance:     float = 0.30   # proximity to subject
    type_match:   float = 0.25   # same property type
    bedrooms:     float = 0.20   # bedroom count proximity
    size:         float = 0.15   # floor area proximity
    recency:      float = 0.10   # how recently it sold

COMP_WEIGHTS = CompScoringWeights()

# Recency decay: comps older than this get zero recency score
MAX_COMP_AGE_DAYS: int = 365 * 3    # 3 years

# Method blend weights (adjusted dynamically based on data quality)
@dataclass(frozen=True)
class MethodWeights:
    comparable_sales: float = 0.55
    price_per_m2:     float = 0.25
    last_sale_growth: float = 0.20

DEFAULT_METHOD_WEIGHTS = MethodWeights()


def annual_growth_for(postcode: str) -> float:
    """Return the best-match annual HPI growth rate for a postcode."""
    prefix = postcode.strip().upper()
    for length in (3, 2, 1):
        key = prefix[:length]
        if key in ANNUAL_HPI_GROWTH:
            return ANNUAL_HPI_GROWTH[key]
    return DEFAULT_ANNUAL_GROWTH


def lease_discount(years_remaining: int | None) -> float:
    """Return the leasehold discount fraction for remaining lease years."""
    if years_remaining is None or years_remaining >= 90:
        return 0.0
    for threshold, discount in LEASE_DISCOUNTS:
        if years_remaining >= threshold:
            return discount
    return LEASE_DISCOUNTS[-1][1]
