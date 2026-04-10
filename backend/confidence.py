"""
Confidence scoring module.

Produces a ConfidenceBreakdown with four independently computed
sub-scores, then blends them into an overall confidence figure.

Sub-scores:
  1. Sample size     — how many eligible comps are available
  2. Recency         — how fresh the comps are on average
  3. Similarity      — how closely comps match the subject
  4. Method agreement — how closely the three valuation methods agree

The overall score is clamped to [CONFIDENCE_FLOOR, CONFIDENCE_CEILING].
"""
from __future__ import annotations

import math
import statistics

from .models import ConfidenceBreakdown, MethodResult, ScoredComparable


CONFIDENCE_FLOOR   = 0.35
CONFIDENCE_CEILING = 0.96


# ─────────────────────────────────────────────────────────────────────
# Sub-scores
# ─────────────────────────────────────────────────────────────────────

def _sample_size_score(n: int) -> float:
    """
    Logarithmic curve:  0 comps = 0.0,  3 = 0.50,  10 = 0.82,  20+ ≈ 1.0.
    Formula: log(1 + n) / log(1 + 20).
    """
    if n <= 0:
        return 0.0
    return math.log1p(n) / math.log1p(20)


def _recency_score(scored_comps: list[ScoredComparable]) -> float:
    """
    Average normalised recency across comps.
    Very recent sales (< 3 months) score ≈ 1.0.
    Sales at the 3-year boundary score 0.0.
    """
    if not scored_comps:
        return 0.0

    MAX_DAYS = 365 * 3
    scores = [max(0.0, 1.0 - sc.age_days / MAX_DAYS) for sc in scored_comps]
    return statistics.mean(scores)


def _similarity_score(scored_comps: list[ScoredComparable]) -> float:
    """
    Weighted mean similarity across comps — already 0–1.
    Weighted by recency so fresh comps influence confidence more.
    """
    if not scored_comps:
        return 0.0

    max_age = max(sc.age_days for sc in scored_comps) or 1
    total_weight = 0.0
    weighted_sim = 0.0
    for sc in scored_comps:
        # Recency weight: fresher = higher weight
        w = 1.0 - sc.age_days / (max_age + 1)
        weighted_sim  += sc.similarity * w
        total_weight  += w

    return weighted_sim / total_weight if total_weight > 0 else 0.0


def _method_agreement_score(method_results: list[MethodResult]) -> float:
    """
    Measures how closely the available methods agree on the final estimate.

    Uses the coefficient of variation (std / mean) of the estimates.
    CV = 0.0  → perfect agreement → score = 1.0
    CV = 0.10 → 10% spread       → score ≈ 0.80
    CV = 0.25 → 25% spread       → score ≈ 0.50
    CV ≥ 0.50 → large divergence → score → 0.0

    Formula: score = max(0, 1 - 2 × CV)
    """
    if len(method_results) < 2:
        return 0.60   # neutral — only one method available

    estimates = [float(m.estimate) for m in method_results]
    mean = statistics.mean(estimates)
    if mean <= 0:
        return 0.0
    cv = statistics.stdev(estimates) / mean
    return max(0.0, 1.0 - 2.0 * cv)


# ─────────────────────────────────────────────────────────────────────
# Blend weights for sub-scores → overall confidence
# ─────────────────────────────────────────────────────────────────────
_BLEND = {
    "sample_size":      0.30,
    "recency":          0.25,
    "similarity":       0.25,
    "method_agreement": 0.20,
}


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def compute_confidence(
    scored_comps: list[ScoredComparable],
    method_results: list[MethodResult],
) -> ConfidenceBreakdown:
    """
    Compute a full ConfidenceBreakdown given scored comparables
    and all available method results.
    """
    ss  = _sample_size_score(len(scored_comps))
    rec = _recency_score(scored_comps)
    sim = _similarity_score(scored_comps)
    agr = _method_agreement_score(method_results)

    raw = (
        _BLEND["sample_size"]      * ss
        + _BLEND["recency"]          * rec
        + _BLEND["similarity"]       * sim
        + _BLEND["method_agreement"] * agr
    )

    overall = round(
        max(CONFIDENCE_FLOOR, min(CONFIDENCE_CEILING, raw)),
        3,
    )

    return ConfidenceBreakdown(
        sample_size_score  = round(ss,  3),
        recency_score      = round(rec, 3),
        similarity_score   = round(sim, 3),
        method_agreement   = round(agr, 3),
        overall            = overall,
    )


def spread_from_confidence(confidence: float) -> float:
    """
    Convert an overall confidence score into a valuation range half-width.

    High confidence (0.95) → tight range (± 4%)
    Low confidence  (0.35) → wide range  (± 18%)

    Formula: spread = 0.04 + (1 - confidence) × 0.215
    This keeps the range practically useful at both ends.
    """
    return 0.04 + (1.0 - confidence) * 0.215
