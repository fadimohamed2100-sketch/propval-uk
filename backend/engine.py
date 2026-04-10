"""
ValuationEngine — public entry point.

Orchestrates:
  1. Score and rank comparables
  2. Run all three valuation methods
  3. Dynamically blend method results
  4. Compute confidence
  5. Derive valuation range
  6. Estimate rental and yield
  7. Return a fully populated ValuationResult
"""
from __future__ import annotations

import statistics
from dataclasses import asdict
from datetime import datetime, timezone

from .comparable_scorer import score_and_rank_comparables
from .confidence import compute_confidence, spread_from_confidence
from .methods import (
    derive_local_price_per_m2,
    method_comparable_sales,
    method_last_sale_growth,
    method_price_per_m2,
)
from .models import (
    ComparableSale,
    MethodResult,
    ScoredComparable,
    SubjectProperty,
    ValuationResult,
)
from .rental import estimate_rental


class InsufficientDataError(ValueError):
    """Raised when the engine cannot produce a reliable estimate."""
    pass


class ValuationEngine:
    """
    Stateless valuation engine.  Instantiate once; call run() per request.

    Parameters
    ----------
    min_comps : int
        Minimum number of eligible comparables required for the
        comparable-sales method.  Defaults to 3.
    top_n_comps : int
        Maximum comparables fed into the engine after scoring/ranking.
    """

    def __init__(self, min_comps: int = 3, top_n_comps: int = 20) -> None:
        self.min_comps   = min_comps
        self.top_n_comps = top_n_comps

    # ─────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────

    def run(
        self,
        subject: SubjectProperty,
        comps: list[ComparableSale],
    ) -> ValuationResult:
        """
        Run a full valuation for *subject* using the provided *comps*.

        Raises
        ------
        InsufficientDataError
            If no valuation method can produce an estimate
            (e.g. too few comps AND no floor area AND no last-sale price).
        """

        # ── Step 1: score and rank comparables ───────────────────────
        scored_comps = score_and_rank_comparables(
            subject, comps, top_n=self.top_n_comps
        )

        # ── Step 2: run all three methods ────────────────────────────
        local_ppm2 = derive_local_price_per_m2(scored_comps)

        comp_result  = method_comparable_sales(scored_comps, min_comps=self.min_comps)
        ppm2_result  = method_price_per_m2(subject, local_ppm2)
        growth_result = method_last_sale_growth(subject)

        available = [r for r in [comp_result, ppm2_result, growth_result] if r is not None]

        if not available:
            raise InsufficientDataError(
                "No valuation method could produce an estimate. "
                "Provide comparable sales, floor area, or a prior sale price."
            )

        # ── Step 3: dynamic blending ─────────────────────────────────
        estimate = self._blend(available)

        # ── Step 4: confidence ───────────────────────────────────────
        confidence = compute_confidence(scored_comps, available)

        # ── Step 5: valuation range ──────────────────────────────────
        spread    = spread_from_confidence(confidence.overall)
        range_low  = int(estimate * (1.0 - spread))
        range_high = int(estimate * (1.0 + spread))

        # ── Step 6: rental and yield ─────────────────────────────────
        rental_monthly, rental_yield = estimate_rental(subject, estimate)

        # ── Step 7: build result ─────────────────────────────────────
        methodology = self._build_methodology(
            subject, available, scored_comps, local_ppm2,
            estimate, spread, confidence.overall,
        )

        return ValuationResult(
            estimated_value = estimate,
            range_low       = range_low,
            range_high      = range_high,
            confidence      = confidence,
            rental_monthly  = rental_monthly,
            rental_yield    = rental_yield,
            method_results  = available,
            scored_comps    = scored_comps,
            methodology     = methodology,
        )

    # ─────────────────────────────────────────────────────────────────
    # Blending
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _blend(methods: list[MethodResult]) -> int:
        """
        Confidence-adjusted weighted average of available method estimates.

        Each method has a base weight (its design weight).  This is then
        multiplied by the method's own confidence score, so high-confidence
        methods pull the blend further toward their estimate.

        Final weights are normalised to sum to 1.0.
        """
        effective_weights = [m.weight * m.confidence for m in methods]
        total = sum(effective_weights)

        if total <= 0:
            # Degenerate fallback: simple average
            return int(statistics.mean(m.estimate for m in methods))

        blended = sum(
            m.estimate * (ew / total)
            for m, ew in zip(methods, effective_weights)
        )
        return int(blended)

    # ─────────────────────────────────────────────────────────────────
    # Methodology audit trail
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_methodology(
        subject: SubjectProperty,
        methods: list[MethodResult],
        scored_comps: list[ScoredComparable],
        local_ppm2: int | None,
        estimate: int,
        spread: float,
        confidence: float,
    ) -> dict:
        return {
            "generated_at":          datetime.now(timezone.utc).isoformat(),
            "methods_available":     [m.method for m in methods],
            "blend_inputs": [
                {
                    "method":     m.method,
                    "estimate_gbp": round(m.estimate / 100, 0),
                    "base_weight":  m.weight,
                    "confidence":   m.confidence,
                    "effective_weight": round(
                        (m.weight * m.confidence)
                        / sum(x.weight * x.confidence for x in methods),
                        4,
                    ),
                }
                for m in methods
            ],
            "final_estimate_gbp":    round(estimate / 100, 0),
            "confidence_overall":    confidence,
            "range_spread_pct":      round(spread * 100, 1),
            "comparables_scored":    len(scored_comps),
            "local_price_per_m2_gbp": round(local_ppm2 / 100, 0) if local_ppm2 else None,
            "subject": {
                "postcode":       subject.postcode,
                "property_type":  subject.property_type.value if subject.property_type else None,
                "bedrooms":       subject.bedrooms,
                "floor_area_m2":  subject.floor_area_m2,
            },
        }
