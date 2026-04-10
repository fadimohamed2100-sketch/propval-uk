"""
Valuation engine.

Method: hedonic comparable sales analysis (simplified AVM).

Steps:
  1. Collect recent comparable sales within radius + age window
  2. Score each comparable by property similarity
  3. Compute weighted median as the point estimate
  4. Derive confidence score from sample size and score distribution
  5. Estimate rental yield using regional gross yield benchmarks

This is a robust MVP model. Production upgrade path:
  - Replace with a trained gradient-boosting regression (XGBoost / LightGBM)
  - Add repeat-sales index adjustment for time
  - Integrate Rightmove / Zoopla for live listings
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


# Regional gross rental yields by property type (UK averages, 2024)
_REGIONAL_YIELDS: dict[str, float] = {
    "flat": 0.056,
    "terraced": 0.047,
    "semi_detached": 0.043,
    "detached": 0.038,
    "bungalow": 0.041,
    "maisonette": 0.052,
    "other": 0.045,
}
_DEFAULT_YIELD = 0.045


@dataclass
class ComparableInput:
    address: str
    postcode: str
    sale_price: int           # pence
    sale_date: date
    property_type: str | None = None
    bedrooms: int | None = None
    floor_area_m2: float | None = None
    distance_m: int | None = None
    source: str = "land_registry"


@dataclass
class ValuationResult:
    estimated_value: int       # pence
    range_low: int
    range_high: int
    confidence_score: float    # 0–1
    rental_monthly: int        # pence
    rental_yield: float        # percentage
    comparables_used: list[dict[str, Any]] = field(default_factory=list)
    methodology: dict[str, Any] = field(default_factory=dict)


class ValuationEngine:
    """
    Produces a ValuationResult given a subject property and a list of comps.
    Stateless — instantiate once and reuse.
    """

    MAX_COMP_AGE_YEARS = 3
    MIN_COMPS = 3
    CONFIDENCE_FLOOR = 0.40

    def run(
        self,
        *,
        subject_type: str | None,
        subject_bedrooms: int | None,
        subject_floor_area_m2: float | None,
        comps: list[ComparableInput],
    ) -> ValuationResult:
        scored = self._score_comps(
            subject_type=subject_type,
            subject_bedrooms=subject_bedrooms,
            subject_floor_area_m2=subject_floor_area_m2,
            comps=comps,
        )

        if len(scored) < self.MIN_COMPS:
            raise ValueError(
                f"Only {len(scored)} comparable(s) found "
                f"(minimum {self.MIN_COMPS} required)."
            )

        point_estimate = self._weighted_median(scored)
        confidence = self._confidence(scored)
        spread = self._spread(confidence)

        range_low = int(point_estimate * (1 - spread))
        range_high = int(point_estimate * (1 + spread))

        rental_monthly, rental_yield = self._rental_estimate(
            point_estimate, subject_type
        )

        comps_out = [
            {
                "address_snapshot": c.address,
                "postcode_snapshot": c.postcode,
                "property_type": c.property_type,
                "bedrooms": c.bedrooms,
                "floor_area_m2": c.floor_area_m2,
                "sale_price": c.sale_price,
                "sale_date": c.sale_date.isoformat() if c.sale_date else None,
                "price_per_m2": (
                    int(c.sale_price / c.floor_area_m2)
                    if c.floor_area_m2 else None
                ),
                "distance_m": c.distance_m,
                "similarity_score": round(score, 3),
                "adjustment_pct": None,
                "source": c.source,
            }
            for c, score in scored
        ]

        methodology = {
            "method": "weighted_comparable_median",
            "comps_considered": len(comps),
            "comps_used": len(scored),
            "subject_type": subject_type,
            "subject_bedrooms": subject_bedrooms,
            "subject_floor_area_m2": subject_floor_area_m2,
            "point_estimate_pence": point_estimate,
            "spread_pct": round(spread * 100, 1),
        }

        logger.info(
            "valuation_computed",
            estimate_gbp=point_estimate / 100,
            confidence=confidence,
            comps_used=len(scored),
        )

        return ValuationResult(
            estimated_value=point_estimate,
            range_low=range_low,
            range_high=range_high,
            confidence_score=confidence,
            rental_monthly=rental_monthly,
            rental_yield=rental_yield,
            comparables_used=comps_out,
            methodology=methodology,
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _score_comps(
        self,
        *,
        subject_type: str | None,
        subject_bedrooms: int | None,
        subject_floor_area_m2: float | None,
        comps: list[ComparableInput],
    ) -> list[tuple[ComparableInput, float]]:
        cutoff = date.today() - timedelta(days=365 * self.MAX_COMP_AGE_YEARS)
        scored: list[tuple[ComparableInput, float]] = []

        for c in comps:
            if not c.sale_price or c.sale_price <= 0:
                continue
            sale_date = c.sale_date if isinstance(c.sale_date, date) else (
                date.fromisoformat(str(c.sale_date)) if c.sale_date else None
            )
            if not sale_date or sale_date < cutoff:
                continue

            score = 1.0

            # Type match
            if subject_type and c.property_type:
                if subject_type == c.property_type:
                    score += 0.4
                else:
                    score -= 0.3

            # Bedroom match
            if subject_bedrooms is not None and c.bedrooms is not None:
                bed_diff = abs(subject_bedrooms - c.bedrooms)
                score -= bed_diff * 0.15

            # Size proximity (± 20% floor area → max bonus)
            if subject_floor_area_m2 and c.floor_area_m2:
                ratio = c.floor_area_m2 / subject_floor_area_m2
                score += 0.3 * max(0, 1 - abs(1 - ratio) * 5)

            # Proximity bonus (closer = more similar)
            if c.distance_m is not None:
                if c.distance_m <= 200:
                    score += 0.25
                elif c.distance_m <= 500:
                    score += 0.10

            # Recency bonus
            age_days = (date.today() - sale_date).days
            recency = max(0, 1 - age_days / (365 * self.MAX_COMP_AGE_YEARS))
            score += 0.2 * recency

            scored.append((c, max(score, 0.01)))

        # Sort descending by score, cap at 20 best comps
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:20]

    # ------------------------------------------------------------------
    # Weighted median
    # ------------------------------------------------------------------
    @staticmethod
    def _weighted_median(
        scored: list[tuple[ComparableInput, float]],
    ) -> int:
        """
        Interpolated weighted median of sale prices.
        More reliable than weighted mean for skewed distributions.
        """
        total_weight = sum(s for _, s in scored)
        cumulative = 0.0
        for comp, score in scored:
            cumulative += score / total_weight
            if cumulative >= 0.5:
                return comp.sale_price
        return scored[-1][0].sale_price

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------
    def _confidence(self, scored: list[tuple[ComparableInput, float]]) -> float:
        n = len(scored)
        prices = [c.sale_price for c, _ in scored]

        # Sample-size component (saturates at ~15 comps)
        size_score = min(1.0, n / 15)

        # Dispersion component — lower CV → higher confidence
        if n >= 2:
            mean = statistics.mean(prices)
            std = statistics.stdev(prices)
            cv = std / mean if mean else 1.0
            dispersion_score = max(0, 1 - cv * 2)
        else:
            dispersion_score = 0.3

        # Average similarity score component
        avg_similarity = statistics.mean(s for _, s in scored)
        similarity_score = min(1.0, avg_similarity / 1.5)

        raw = (size_score * 0.4) + (dispersion_score * 0.35) + (similarity_score * 0.25)
        return round(max(self.CONFIDENCE_FLOOR, min(0.97, raw)), 3)

    # ------------------------------------------------------------------
    # Spread (drives valuation range)
    # ------------------------------------------------------------------
    @staticmethod
    def _spread(confidence: float) -> float:
        """Higher confidence → tighter range. Range: ±5% to ±20%."""
        return 0.05 + (1 - confidence) * 0.15

    # ------------------------------------------------------------------
    # Rental estimate
    # ------------------------------------------------------------------
    @staticmethod
    def _rental_estimate(
        estimated_value_pence: int,
        property_type: str | None,
    ) -> tuple[int, float]:
        gross_yield = _REGIONAL_YIELDS.get(property_type or "", _DEFAULT_YIELD)
        annual_rent_pence = estimated_value_pence * gross_yield
        monthly_pence = int(annual_rent_pence / 12)
        yield_pct = round(gross_yield * 100, 2)
        return monthly_pence, yield_pct
