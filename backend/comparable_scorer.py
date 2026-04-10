"""
Comparable scoring module.

Scores each comparable sale against the subject property across five
dimensions, applies per-dimension adjustments to the raw sale price,
and returns a ScoredComparable with full audit trail.
"""
from __future__ import annotations

import math
from datetime import date

from .constants import (
    BEDROOM_ADJUSTMENT,
    BEDROOM_ADJUSTMENT_DEFAULT,
    COMP_WEIGHTS,
    MAX_COMP_AGE_DAYS,
    annual_growth_for,
)
from .models import ComparableSale, PropertyType, ScoredComparable, SubjectProperty


# ─────────────────────────────────────────────────────────────────────
# Individual dimension scores  (each returns 0.0 – 1.0)
# ─────────────────────────────────────────────────────────────────────

def _distance_score(distance_m: int) -> float:
    """
    Exponential decay.  Score = 1.0 at 0m, ~0.5 at 400m, ~0.13 at 1000m.
    Formula: e^(-distance / half_life) where half_life = 400m.
    """
    return math.exp(-distance_m / 400.0)


def _type_score(subject: PropertyType | None, comp: PropertyType | None) -> float:
    """
    Exact match = 1.0.
    Related types (terraced ↔ semi_detached, flat ↔ maisonette) = 0.6.
    Unrelated = 0.2.
    Unknown = 0.5 (neutral).
    """
    if subject is None or comp is None:
        return 0.5

    if subject == comp:
        return 1.0

    _related: dict[PropertyType, set[PropertyType]] = {
        PropertyType.TERRACED:      {PropertyType.SEMI_DETACHED, PropertyType.BUNGALOW},
        PropertyType.SEMI_DETACHED: {PropertyType.TERRACED, PropertyType.DETACHED},
        PropertyType.FLAT:          {PropertyType.MAISONETTE},
        PropertyType.MAISONETTE:    {PropertyType.FLAT},
        PropertyType.DETACHED:      {PropertyType.SEMI_DETACHED, PropertyType.BUNGALOW},
        PropertyType.BUNGALOW:      {PropertyType.DETACHED, PropertyType.TERRACED},
    }
    if comp in _related.get(subject, set()):
        return 0.6

    return 0.2


def _bedroom_score(subject_beds: int | None, comp_beds: int | None) -> float:
    """
    Gaussian decay around zero difference.
    0 diff = 1.0, 1 diff = 0.72, 2 diff = 0.27, 3+ diff = 0.10.
    """
    if subject_beds is None or comp_beds is None:
        return 0.5
    diff = abs(subject_beds - comp_beds)
    return math.exp(-(diff ** 2) / 2.0)


def _size_score(subject_m2: float | None, comp_m2: float | None) -> float:
    """
    Score based on relative size difference.
    0% diff = 1.0, 10% diff = 0.82, 25% diff = 0.53, 50% diff = 0.22.
    """
    if subject_m2 is None or comp_m2 is None:
        return 0.5
    if subject_m2 <= 0 or comp_m2 <= 0:
        return 0.5
    ratio = comp_m2 / subject_m2
    log_ratio = math.log(ratio)
    return math.exp(-(log_ratio ** 2) / 0.15)


def _recency_score(age_days: int) -> float:
    """
    Linear decay from 1.0 (today) to 0.0 at MAX_COMP_AGE_DAYS.
    Clamp to 0 beyond the cutoff.
    """
    return max(0.0, 1.0 - age_days / MAX_COMP_AGE_DAYS)


# ─────────────────────────────────────────────────────────────────────
# Price adjustment  (converts raw comp price → adjusted for subject)
# ─────────────────────────────────────────────────────────────────────

def _bedroom_price_adjustment(
    subject_beds: int | None,
    comp_beds: int | None,
) -> float:
    """
    Returns a multiplier to adjust the comp price for bedroom count.
    E.g. subject=4 beds, comp=3 beds → multiplier ~1.10.
    """
    if subject_beds is None or comp_beds is None:
        return 1.0

    def _adj(beds: int) -> float:
        return BEDROOM_ADJUSTMENT.get(beds, BEDROOM_ADJUSTMENT_DEFAULT)

    # Convert both to their absolute premium vs zero
    # then find the multiplicative ratio
    base_index  = 1.0 + _adj(comp_beds)
    target_index = 1.0 + _adj(subject_beds)
    if base_index <= 0:
        return 1.0
    return target_index / base_index


def _size_price_adjustment(
    subject_m2: float | None,
    comp_m2: float | None,
) -> float:
    """
    Adjusts comp price per-m² to subject's floor area.
    We assume a mild diminishing returns curve: price ∝ m²^0.85.
    So multiplier = (subject_m2 / comp_m2) ^ 0.85.
    """
    if subject_m2 is None or comp_m2 is None:
        return 1.0
    if subject_m2 <= 0 or comp_m2 <= 0:
        return 1.0
    return (subject_m2 / comp_m2) ** 0.85


def _time_adjustment(sale_date: date, postcode: str) -> float:
    """
    Adjusts comp price upward for time elapsed since sale.
    Uses compound HPI growth.  multiplier = (1 + r)^(days/365).
    """
    age_days = (date.today() - sale_date).days
    if age_days <= 0:
        return 1.0
    annual_rate = annual_growth_for(postcode)
    return (1.0 + annual_rate) ** (age_days / 365.0)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def score_comparable(
    subject: SubjectProperty,
    comp: ComparableSale,
) -> ScoredComparable | None:
    """
    Score and adjust a single comparable sale against the subject property.

    Returns None if the comp fails basic eligibility checks
    (too old, zero price, future sale date).
    """
    today = date.today()
    age_days = (today - comp.sale_date).days

    # ── Eligibility guard ────────────────────────────────────────
    if age_days < 0:                     # future sale date — data error
        return None
    if age_days > MAX_COMP_AGE_DAYS:     # too old
        return None
    if comp.sale_price <= 0:             # bad data
        return None

    # ── Dimension scores ─────────────────────────────────────────
    d_score = _distance_score(comp.distance_m)
    t_score = _type_score(subject.property_type, comp.property_type)
    b_score = _bedroom_score(subject.bedrooms, comp.bedrooms)
    s_score = _size_score(subject.floor_area_m2, comp.floor_area_m2)
    r_score = _recency_score(age_days)

    weights = COMP_WEIGHTS
    similarity = (
        weights.distance   * d_score
        + weights.type_match * t_score
        + weights.bedrooms   * b_score
        + weights.size       * s_score
        + weights.recency    * r_score
    )

    # ── Price adjustments ────────────────────────────────────────
    time_mult    = _time_adjustment(comp.sale_date, comp.postcode)
    bedroom_mult = _bedroom_price_adjustment(subject.bedrooms, comp.bedrooms)
    size_mult    = _size_price_adjustment(subject.floor_area_m2, comp.floor_area_m2)

    adjusted_price = int(comp.sale_price * time_mult * bedroom_mult * size_mult)

    price_per_m2 = (
        int(comp.sale_price / comp.floor_area_m2)
        if comp.floor_area_m2 and comp.floor_area_m2 > 0
        else None
    )

    return ScoredComparable(
        comp=comp,
        similarity=round(similarity, 4),
        age_days=age_days,
        price_per_m2=price_per_m2,
        adjusted_price=adjusted_price,
        adjustments={
            "time_multiplier":    round(time_mult, 4),
            "bedroom_multiplier": round(bedroom_mult, 4),
            "size_multiplier":    round(size_mult, 4),
            "dimension_scores": {
                "distance": round(d_score, 3),
                "type":     round(t_score, 3),
                "bedrooms": round(b_score, 3),
                "size":     round(s_score, 3),
                "recency":  round(r_score, 3),
            },
        },
    )


def score_and_rank_comparables(
    subject: SubjectProperty,
    comps: list[ComparableSale],
    top_n: int = 20,
) -> list[ScoredComparable]:
    """
    Score every comp, drop ineligible ones, and return the top_n by similarity.
    """
    scored: list[ScoredComparable] = []
    for comp in comps:
        result = score_comparable(subject, comp)
        if result is not None:
            scored.append(result)

    scored.sort(key=lambda x: x.similarity, reverse=True)
    return scored[:top_n]
