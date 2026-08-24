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
    source_url: str | None = None
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


import decimal

def _clean_decimals(obj):
    if isinstance(obj, dict):
        return {k: _clean_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_decimals(v) for v in obj]
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    return obj

class ValuationEngine:
    """
    Produces a ValuationResult given a subject property and a list of comps.
    Stateless — instantiate once and reuse.
    """

    MAX_COMP_AGE_YEARS = 3
    # Exponent for size adjustment: value ~ area ** 0.85. Below 1.0 because
    # larger properties trade at a lower rate per square metre.
    SIZE_EXPONENT: float = 0.85

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
        # Sort by distance first, keep closest 10 if distances available
        comps_with_dist = [c for c in comps if c.distance_m is not None]
        comps_without_dist = [c for c in comps if c.distance_m is None]
        if comps_with_dist:
            comps_with_dist.sort(key=lambda c: c.distance_m)
            comps = comps_with_dist[:10] + comps_without_dist[:5]
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

        # Size-adjusted (£/m2) estimate where we have real comparable
        # floor areas; raw-price median otherwise.
        point_estimate = self._weighted_median_price_per_m2(scored, subject_floor_area_m2)
        valuation_basis = "weighted_median_price_per_m2"
        if point_estimate is None or point_estimate <= 0:
            point_estimate = self._weighted_median(scored)
            valuation_basis = "weighted_median_price"
        confidence = self._confidence(scored)
        spread = self._spread(confidence)

        range_low = int(point_estimate * (1 - spread))
        range_high = int(point_estimate * (1 + spread))

        rental_monthly, rental_yield = self._rental_estimate(
            point_estimate, subject_type
        )

        # Order display list by proximity (closest first); unmatched distance goes last
        scored_for_display = sorted(
            scored,
            key=lambda x: (x[0].distance_m if x[0].distance_m is not None else float("inf"))
        )
        comps_out = [
            {
                "address_snapshot": c.address,
                "postcode_snapshot": c.postcode,
                "property_type": c.property_type,
                "bedrooms": c.bedrooms,
                "floor_area_m2": c.floor_area_m2,
                "sale_price": c.sale_price,
                "sale_date": c.sale_date.isoformat() if hasattr(c.sale_date, "isoformat") else c.sale_date,
                "price_per_m2": (
                    int(c.sale_price / c.floor_area_m2)
                    if c.floor_area_m2 else None
                ),
                "distance_m": c.distance_m,
                "similarity_score": round(score, 3),
                "adjustment_pct": None,
                "source": c.source,
                "source_url": getattr(c, "source_url", None),
            }
            for c, score in scored_for_display
        ]

        methodology = {
            "method": valuation_basis,
            "comps_with_floor_area": sum(
                1 for cc, _ in scored if cc.floor_area_m2 and float(cc.floor_area_m2) > 0
            ),
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
            basis=valuation_basis,
        )

        return ValuationResult(
            estimated_value=point_estimate,
            range_low=range_low,
            range_high=range_high,
            confidence_score=confidence,
            rental_monthly=rental_monthly,
            rental_yield=rental_yield,
            comparables_used=comps_out,
            methodology=_clean_decimals(methodology),
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
                score += 0.3 * max(0, 1 - abs(1 - float(ratio)) * 5)

            # Proximity bonus (closer = more similar) - heavily weighted
            if c.distance_m is not None:
                if c.distance_m <= 200:
                    score += 0.8
                elif c.distance_m <= 500:
                    score += 0.5
                elif c.distance_m <= 800:
                    score += 0.3
                elif c.distance_m <= 1600:
                    score += 0.1
            # Recency bonus - less weight than proximity
            age_days = (date.today() - sale_date).days
            recency = max(0, 1 - age_days / (365 * self.MAX_COMP_AGE_YEARS))
            score += 0.15 * recency
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
    def _weighted_median_price_per_m2(
        scored: list[tuple[ComparableInput, float]],
        subject_floor_area_m2: float,
    ) -> int | None:
        """
        Size-adjusted estimate: weighted median of comparable £/m2, scaled
        to the subject's floor area.

        The raw-price median below ignores size entirely, so a large house
        among smaller neighbours lands on THEIR price - a 2,174 sqft
        six-bed was valued at the price of an 1,100 sqft semi. Valuing on
        £/m2 is also how professional AVMs work.

        Returns None when too few comparables have a real floor area, so
        the caller falls back to the raw-price median rather than
        extrapolating from one or two data points.
        """
        usable = [
            (c, s) for c, s in scored
            if c.floor_area_m2 and float(c.floor_area_m2) > 0 and c.sale_price > 0
        ]
        if len(usable) < ValuationEngine.MIN_COMPS or not subject_floor_area_m2:
            return None

        # Value scales SUB-LINEARLY with floor area. Straight £/m2 x area
        # assumes a 200 m2 house is worth exactly twice a 100 m2 one, which
        # overprices large properties: on a Brixton semi it produced
        # £782/sqft where the comparables themselves supported ~£724/sqft.
        # Smaller homes trade at a higher rate per square metre, so scaling
        # their rate up to a bigger subject systematically overshoots.
        #
        # Each comparable is instead projected onto the subject using a
        # power curve, then the weighted median of those projections is
        # taken. SIZE_EXPONENT of 0.85 is the standard valuation
        # convention: doubling floor area adds ~80% to value, not 100%.
        subject_area = float(subject_floor_area_m2)
        projected: list[tuple[int, float]] = []
        for comp, score in usable:
            comp_area = float(comp.floor_area_m2)
            ratio = subject_area / comp_area
            # Clamp: beyond a 3x size difference the comparable is not
            # really comparable and the curve stops being trustworthy.
            ratio = max(0.33, min(ratio, 3.0))
            implied = comp.sale_price * (ratio ** ValuationEngine.SIZE_EXPONENT)
            projected.append((int(implied), score))

        projected.sort(key=lambda x: x[0])
        total_weight = sum(s for _, s in projected)
        if total_weight <= 0:
            return projected[len(projected) // 2][0]
        cumulative = 0.0
        chosen = projected[-1][0]
        for value, score in projected:
            cumulative += score / total_weight
            if cumulative >= 0.5:
                chosen = value
                break
        return chosen

    @staticmethod
    def _weighted_median(
        scored: list[tuple[ComparableInput, float]],
    ) -> int:
        """
        Weighted median of sale prices: sorts comparables by PRICE first,
        then walks the cumulative weight to find the 50% crossing point.
        """
        if not scored:
            return 0
        by_price = sorted(scored, key=lambda x: x[0].sale_price)
        total_weight = sum(s for _, s in by_price)
        if total_weight <= 0:
            return by_price[len(by_price) // 2][0].sale_price
        cumulative = 0.0
        for comp, score in by_price:
            cumulative += score / total_weight
            if cumulative >= 0.5:
                return comp.sale_price
        return by_price[-1][0].sale_price

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
            mean = statistics.mean(prices) if prices else 0
            std = statistics.stdev(prices) if len(prices) > 1 else 0
            cv = std / mean if mean else 1.0
            dispersion_score = max(0, 1 - cv * 2)
        else:
            dispersion_score = 0.3

        # Average similarity score component
        avg_similarity = statistics.mean(s for _, s in scored) if scored else 0
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
