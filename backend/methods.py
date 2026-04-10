"""
Valuation methods.

Three independent methods — each returns a MethodResult with its own
estimate, confidence, and supporting data.  The engine then blends them.

Method 1 — Comparable sales (hedonic weighted median)
Method 2 — Price per m² baseline
Method 3 — Last sale price + HPI growth
"""
from __future__ import annotations

import math
import statistics
from datetime import date

from .constants import (
    BEDROOM_ADJUSTMENT,
    BEDROOM_ADJUSTMENT_DEFAULT,
    DEFAULT_PRICE_PER_M2,
    EPC_ADJUSTMENTS,
    FEATURE_ADJUSTMENTS,
    LEASE_DISCOUNTS,
    PRICE_PER_M2_PENCE,
    annual_growth_for,
    lease_discount,
)
from .models import MethodResult, PropertyType, ScoredComparable, SubjectProperty


# ─────────────────────────────────────────────────────────────────────
# METHOD 1  —  Comparable Sales  (weighted median)
# ─────────────────────────────────────────────────────────────────────

def _weighted_median(values: list[float], weights: list[float]) -> float:
    """
    True weighted median via sorted interpolation.
    More robust than weighted mean for price distributions with outliers.
    """
    if not values:
        raise ValueError("Cannot compute weighted median of empty list.")

    paired = sorted(zip(values, weights), key=lambda x: x[0])
    total_w = sum(w for _, w in paired)
    cumulative = 0.0
    for value, weight in paired:
        cumulative += weight / total_w
        if cumulative >= 0.5:
            return value

    return paired[-1][0]


def method_comparable_sales(
    scored_comps: list[ScoredComparable],
    min_comps: int = 3,
) -> MethodResult | None:
    """
    Compute a value estimate from scored comparable sales.

    Uses a similarity-weighted median of adjusted comp prices.
    Returns None if fewer than min_comps eligible comps are available.
    """
    if len(scored_comps) < min_comps:
        return None

    prices  = [float(sc.adjusted_price)  for sc in scored_comps]
    weights = [sc.similarity              for sc in scored_comps]

    estimate = int(_weighted_median(prices, weights))

    # Method confidence: driven by count and average similarity
    n = len(scored_comps)
    avg_sim = statistics.mean(weights)

    count_conf  = min(1.0, math.log1p(n) / math.log1p(20))  # saturates at ~20 comps
    sim_conf    = avg_sim                                      # already 0–1

    # Price dispersion: tighter cluster → more confident
    if n >= 2:
        cv = statistics.stdev(prices) / statistics.mean(prices)
        dispersion_conf = max(0.0, 1.0 - cv * 1.8)
    else:
        dispersion_conf = 0.4

    confidence = round(
        count_conf * 0.40
        + sim_conf * 0.35
        + dispersion_conf * 0.25,
        4,
    )

    return MethodResult(
        method="comparable_sales",
        estimate=estimate,
        weight=0.55,
        confidence=confidence,
        supporting={
            "comps_used":          n,
            "average_similarity":  round(avg_sim, 3),
            "price_dispersion_cv": round(statistics.stdev(prices) / statistics.mean(prices), 3) if n >= 2 else None,
            "comp_prices_gbp":     [round(p / 100, 0) for p in sorted(prices)],
        },
    )


# ─────────────────────────────────────────────────────────────────────
# METHOD 2  —  Price per m²
# ─────────────────────────────────────────────────────────────────────

def _feature_premium(subject: SubjectProperty) -> float:
    """
    Returns the total multiplicative adjustment for property features.
    E.g. garden (+5%) + parking (+3%) = 1.08 multiplier.
    """
    total = 0.0
    for attr, adj in FEATURE_ADJUSTMENTS.items():
        if getattr(subject, attr, False):
            total += adj

    epc = (subject.epc_rating or "D").upper()
    total += EPC_ADJUSTMENTS.get(epc, 0.0)

    if subject.tenure and "leasehold" in subject.tenure.value:
        total -= lease_discount(subject.lease_years)

    beds = subject.bedrooms
    if beds is not None:
        bed_adj = BEDROOM_ADJUSTMENT.get(beds, BEDROOM_ADJUSTMENT_DEFAULT)
        total += bed_adj

    return 1.0 + total


def method_price_per_m2(
    subject: SubjectProperty,
    local_price_per_m2: int | None = None,
) -> MethodResult | None:
    """
    Estimate value as (floor_area × price_per_m²) × feature adjustments.

    Uses local_price_per_m2 derived from comps if available; falls back
    to the national type-based baseline.

    Returns None if floor_area_m2 is unknown.
    """
    if not subject.floor_area_m2 or subject.floor_area_m2 <= 0:
        return None

    # Prefer locally derived rate; fall back to type baseline
    if local_price_per_m2 and local_price_per_m2 > 0:
        base_rate = local_price_per_m2
        rate_source = "local_comps"
        confidence_base = 0.75
    else:
        prop_type = subject.property_type or PropertyType.OTHER
        base_rate = PRICE_PER_M2_PENCE.get(prop_type, DEFAULT_PRICE_PER_M2)
        rate_source = "national_baseline"
        confidence_base = 0.50

    raw_estimate  = int(subject.floor_area_m2 * base_rate)
    feature_mult  = _feature_premium(subject)
    estimate      = int(raw_estimate * feature_mult)

    return MethodResult(
        method="price_per_m2",
        estimate=estimate,
        weight=0.25,
        confidence=confidence_base,
        supporting={
            "floor_area_m2":     subject.floor_area_m2,
            "price_per_m2_pence": base_rate,
            "price_per_m2_gbp":  round(base_rate / 100, 0),
            "feature_multiplier": round(feature_mult, 4),
            "rate_source":        rate_source,
            "raw_estimate_gbp":   round(raw_estimate / 100, 0),
        },
    )


# ─────────────────────────────────────────────────────────────────────
# METHOD 3  —  Last Sale + HPI Growth
# ─────────────────────────────────────────────────────────────────────

def method_last_sale_growth(
    subject: SubjectProperty,
) -> MethodResult | None:
    """
    Forward-project the subject's last known sale price using local HPI.

    Estimate = last_sale_price × (1 + annual_rate) ^ (years_elapsed).

    Returns None if last_sale_price or last_sale_date is unknown.
    """
    if not subject.last_sale_price or not subject.last_sale_date:
        return None
    if subject.last_sale_price <= 0:
        return None

    today = date.today()
    age_days = (today - subject.last_sale_date).days
    if age_days < 0:
        return None

    years_elapsed = age_days / 365.25
    annual_rate   = annual_growth_for(subject.postcode)
    growth_factor = (1.0 + annual_rate) ** years_elapsed
    estimate      = int(subject.last_sale_price * growth_factor)

    # Confidence decays with age: very recent = high confidence, 10+ years = low
    age_confidence = max(0.20, 1.0 - years_elapsed / 12.0)

    return MethodResult(
        method="last_sale_growth",
        estimate=estimate,
        weight=0.20,
        confidence=round(age_confidence, 4),
        supporting={
            "last_sale_price_gbp": round(subject.last_sale_price / 100, 0),
            "last_sale_date":      subject.last_sale_date.isoformat(),
            "years_elapsed":       round(years_elapsed, 2),
            "annual_hpi_rate":     annual_rate,
            "growth_factor":       round(growth_factor, 4),
        },
    )


# ─────────────────────────────────────────────────────────────────────
# LOCAL PRICE PER M²  (derived from comps — feeds into method 2)
# ─────────────────────────────────────────────────────────────────────

def derive_local_price_per_m2(
    scored_comps: list[ScoredComparable],
    min_with_area: int = 3,
) -> int | None:
    """
    Compute a similarity-weighted median price per m² from comps that
    have known floor area.  Returns None if fewer than min_with_area comps
    have area data.
    """
    with_area = [
        sc for sc in scored_comps
        if sc.price_per_m2 is not None and sc.price_per_m2 > 0
    ]

    if len(with_area) < min_with_area:
        return None

    prices  = [float(sc.price_per_m2) for sc in with_area]
    weights = [sc.similarity           for sc in with_area]

    return int(_weighted_median(prices, weights))
