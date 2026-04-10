"""
Test suite for the valuation engine.
Run with:  pytest test_engine.py -v
"""
from __future__ import annotations

import math
import pytest
from datetime import date, timedelta

from valuation_engine import (
    ComparableSale,
    InsufficientDataError,
    PropertyType,
    SubjectProperty,
    Tenure,
    ValuationEngine,
    ValuationResult,
)
from valuation_engine.comparable_scorer import (
    _bedroom_score,
    _distance_score,
    _recency_score,
    _size_score,
    _type_score,
    score_comparable,
)
from valuation_engine.confidence import (
    _method_agreement_score,
    _sample_size_score,
    compute_confidence,
    spread_from_confidence,
)
from valuation_engine.methods import (
    _weighted_median,
    method_comparable_sales,
    method_last_sale_growth,
    method_price_per_m2,
)
from valuation_engine.models import MethodResult, ScoredComparable
from valuation_engine.rental import estimate_rental


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _days_ago(n: int) -> date:
    return date.today() - timedelta(days=n)


def _comp(
    price: int = 500_000,
    days_ago: int = 180,
    distance_m: int = 300,
    prop_type: PropertyType = PropertyType.TERRACED,
    bedrooms: int = 3,
    floor_area: float | None = 90.0,
) -> ComparableSale:
    return ComparableSale(
        address=f"1 Test Street",
        postcode="SW1A 1AA",
        sale_price=price * 100,
        sale_date=_days_ago(days_ago),
        distance_m=distance_m,
        property_type=prop_type,
        bedrooms=bedrooms,
        floor_area_m2=floor_area,
    )


def _subject(
    prop_type: PropertyType = PropertyType.TERRACED,
    bedrooms: int = 3,
    floor_area: float = 90.0,
    last_price: int | None = None,
    last_date: date | None = None,
) -> SubjectProperty:
    return SubjectProperty(
        postcode="SW1A 1AA",
        property_type=prop_type,
        bedrooms=bedrooms,
        floor_area_m2=floor_area,
        last_sale_price=last_price * 100 if last_price else None,
        last_sale_date=last_date,
    )


def _engine() -> ValuationEngine:
    return ValuationEngine(min_comps=3)


# ─────────────────────────────────────────────────────────────────────
# 1. Comparable scorer — dimension scores
# ─────────────────────────────────────────────────────────────────────

class TestDistanceScore:
    def test_zero_distance_is_one(self):
        assert _distance_score(0) == pytest.approx(1.0)

    def test_400m_is_approx_half(self):
        assert _distance_score(400) == pytest.approx(math.exp(-1), rel=0.01)

    def test_monotonically_decreasing(self):
        scores = [_distance_score(d) for d in [0, 100, 300, 600, 1000]]
        assert scores == sorted(scores, reverse=True)


class TestTypeScore:
    def test_exact_match_is_one(self):
        assert _type_score(PropertyType.FLAT, PropertyType.FLAT) == 1.0

    def test_related_types_score_above_zero_point_five(self):
        assert _type_score(PropertyType.TERRACED, PropertyType.SEMI_DETACHED) == 0.6

    def test_unrelated_types_score_low(self):
        assert _type_score(PropertyType.FLAT, PropertyType.DETACHED) == 0.2

    def test_none_returns_neutral(self):
        assert _type_score(None, PropertyType.FLAT) == 0.5
        assert _type_score(PropertyType.FLAT, None) == 0.5


class TestBedroomScore:
    def test_same_bedrooms_is_one(self):
        assert _bedroom_score(3, 3) == pytest.approx(1.0)

    def test_one_bed_diff_penalised(self):
        s = _bedroom_score(3, 4)
        assert 0.5 < s < 1.0

    def test_three_bed_diff_heavily_penalised(self):
        assert _bedroom_score(1, 4) < 0.2

    def test_none_returns_neutral(self):
        assert _bedroom_score(None, 3) == 0.5


class TestSizeScore:
    def test_identical_size_is_one(self):
        assert _size_score(90.0, 90.0) == pytest.approx(1.0, rel=0.01)

    def test_double_size_penalised(self):
        assert _size_score(90.0, 180.0) < 0.5

    def test_symmetric(self):
        assert _size_score(90.0, 120.0) == pytest.approx(
            _size_score(120.0, 90.0), rel=0.05
        )

    def test_none_returns_neutral(self):
        assert _size_score(None, 90.0) == 0.5


class TestRecencyScore:
    def test_today_is_one(self):
        assert _recency_score(0) == pytest.approx(1.0)

    def test_at_cutoff_is_zero(self):
        assert _recency_score(365 * 3) == pytest.approx(0.0)

    def test_beyond_cutoff_clamped_to_zero(self):
        assert _recency_score(365 * 4) == 0.0


# ─────────────────────────────────────────────────────────────────────
# 2. score_comparable — integration
# ─────────────────────────────────────────────────────────────────────

class TestScoreComparable:
    def test_eligible_comp_returns_scored(self):
        s = _subject()
        c = _comp()
        sc = score_comparable(s, c)
        assert sc is not None
        assert 0 < sc.similarity < 1

    def test_stale_comp_returns_none(self):
        s = _subject()
        c = _comp(days_ago=365 * 4)
        assert score_comparable(s, c) is None

    def test_zero_price_comp_returns_none(self):
        s = _subject()
        c = _comp(price=0)
        assert score_comparable(s, c) is None

    def test_identical_comp_scores_near_one(self):
        s = _subject(bedrooms=3, floor_area=90.0)
        c = _comp(days_ago=10, distance_m=50)
        sc = score_comparable(s, c)
        assert sc is not None
        assert sc.similarity > 0.8

    def test_adjustments_recorded(self):
        s = _subject()
        c = _comp()
        sc = score_comparable(s, c)
        assert sc is not None
        assert "time_multiplier"    in sc.adjustments
        assert "bedroom_multiplier" in sc.adjustments
        assert "size_multiplier"    in sc.adjustments

    def test_time_adjustment_increases_older_comp_price(self):
        s = _subject()
        c_old   = _comp(days_ago=700, price=500_000)
        c_fresh = _comp(days_ago=30,  price=500_000)
        sc_old   = score_comparable(s, c_old)
        sc_fresh = score_comparable(s, c_fresh)
        assert sc_old is not None and sc_fresh is not None
        assert sc_old.adjusted_price > sc_fresh.adjusted_price


# ─────────────────────────────────────────────────────────────────────
# 3. Valuation methods
# ─────────────────────────────────────────────────────────────────────

class TestWeightedMedian:
    def test_equal_weights_matches_median(self):
        values  = [100.0, 200.0, 300.0, 400.0, 500.0]
        weights = [1.0] * 5
        result  = _weighted_median(values, weights)
        assert result == pytest.approx(300.0)

    def test_heavy_weight_pulls_toward_value(self):
        values  = [100.0, 900.0]
        weights = [0.1, 0.9]    # 90% weight on 900
        result  = _weighted_median(values, weights)
        assert result == pytest.approx(900.0)

    def test_raises_on_empty(self):
        with pytest.raises(ValueError):
            _weighted_median([], [])


class TestMethodComparableSales:
    def _make_scored(self, prices: list[int]) -> list[ScoredComparable]:
        comps = [_comp(price=p) for p in prices]
        from valuation_engine.comparable_scorer import score_and_rank_comparables
        s = _subject()
        return score_and_rank_comparables(s, comps)

    def test_returns_result_with_enough_comps(self):
        sc = self._make_scored([500_000, 510_000, 490_000, 505_000])
        result = method_comparable_sales(sc, min_comps=3)
        assert result is not None
        assert result.estimate > 0

    def test_returns_none_with_too_few_comps(self):
        sc = self._make_scored([500_000, 510_000])
        result = method_comparable_sales(sc, min_comps=3)
        assert result is None

    def test_confidence_between_zero_and_one(self):
        sc = self._make_scored([500_000] * 10)
        result = method_comparable_sales(sc)
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0


class TestMethodPricePerM2:
    def test_returns_estimate_when_area_known(self):
        s = _subject(floor_area=90.0)
        result = method_price_per_m2(s)
        assert result is not None
        assert result.estimate > 0

    def test_returns_none_when_area_unknown(self):
        s = SubjectProperty(postcode="SW1A 1AA")
        result = method_price_per_m2(s)
        assert result is None

    def test_larger_property_worth_more(self):
        s_small = _subject(floor_area=60.0)
        s_large = _subject(floor_area=120.0)
        r_small = method_price_per_m2(s_small)
        r_large = method_price_per_m2(s_large)
        assert r_small is not None and r_large is not None
        assert r_large.estimate > r_small.estimate

    def test_local_rate_beats_national_confidence(self):
        s = _subject()
        r_national = method_price_per_m2(s, local_price_per_m2=None)
        r_local    = method_price_per_m2(s, local_price_per_m2=350_000)
        assert r_national is not None and r_local is not None
        assert r_local.confidence > r_national.confidence


class TestMethodLastSaleGrowth:
    def test_returns_result_when_data_present(self):
        s = _subject(last_price=400_000, last_date=_days_ago(365 * 2))
        result = method_last_sale_growth(s)
        assert result is not None
        assert result.estimate > 400_000 * 100   # should have grown

    def test_returns_none_without_last_sale(self):
        s = _subject()
        assert method_last_sale_growth(s) is None

    def test_recent_sale_has_high_confidence(self):
        s = _subject(last_price=500_000, last_date=_days_ago(30))
        r = method_last_sale_growth(s)
        assert r is not None
        assert r.confidence > 0.90

    def test_old_sale_has_lower_confidence(self):
        s_recent = _subject(last_price=500_000, last_date=_days_ago(365))
        s_old    = _subject(last_price=500_000, last_date=_days_ago(365 * 8))
        r_recent = method_last_sale_growth(s_recent)
        r_old    = method_last_sale_growth(s_old)
        assert r_recent is not None and r_old is not None
        assert r_recent.confidence > r_old.confidence


# ─────────────────────────────────────────────────────────────────────
# 4. Confidence scoring
# ─────────────────────────────────────────────────────────────────────

class TestSampleSizeScore:
    def test_zero_comps_is_zero(self):
        assert _sample_size_score(0) == 0.0

    def test_twenty_comps_near_one(self):
        assert _sample_size_score(20) == pytest.approx(1.0, rel=0.01)

    def test_monotonically_increasing(self):
        scores = [_sample_size_score(n) for n in [1, 3, 5, 10, 15, 20]]
        assert scores == sorted(scores)


class TestMethodAgreementScore:
    def test_identical_estimates_score_one(self):
        methods = [
            MethodResult("a", 500_000_00, 0.5, 0.8),
            MethodResult("b", 500_000_00, 0.3, 0.7),
        ]
        assert _method_agreement_score(methods) == pytest.approx(1.0)

    def test_diverging_estimates_score_low(self):
        methods = [
            MethodResult("a", 300_000_00, 0.5, 0.8),
            MethodResult("b", 700_000_00, 0.3, 0.7),
        ]
        assert _method_agreement_score(methods) < 0.5

    def test_single_method_returns_neutral(self):
        methods = [MethodResult("a", 500_000_00, 1.0, 0.8)]
        score = _method_agreement_score(methods)
        assert 0.4 < score < 0.8


class TestSpreadFromConfidence:
    def test_high_confidence_tight_range(self):
        assert spread_from_confidence(0.95) < 0.07

    def test_low_confidence_wide_range(self):
        assert spread_from_confidence(0.35) > 0.15

    def test_monotonically_decreasing(self):
        spreads = [spread_from_confidence(c) for c in [0.95, 0.80, 0.65, 0.50, 0.35]]
        assert spreads == sorted(spreads)


# ─────────────────────────────────────────────────────────────────────
# 5. Rental estimation
# ─────────────────────────────────────────────────────────────────────

class TestRentalEstimate:
    def test_returns_positive_rent_and_yield(self):
        s = _subject()
        rent, yld = estimate_rental(s, 500_000 * 100)
        assert rent > 0
        assert yld > 0

    def test_flat_yields_more_than_detached(self):
        s_flat     = _subject(prop_type=PropertyType.FLAT)
        s_detached = _subject(prop_type=PropertyType.DETACHED)
        value = 500_000 * 100
        _, yld_flat     = estimate_rental(s_flat,     value)
        _, yld_detached = estimate_rental(s_detached, value)
        assert yld_flat > yld_detached

    def test_more_bedrooms_more_rent(self):
        s2 = _subject(bedrooms=2)
        s4 = _subject(bedrooms=4)
        value = 500_000 * 100
        rent2, _ = estimate_rental(s2, value)
        rent4, _ = estimate_rental(s4, value)
        assert rent4 > rent2

    def test_yield_recalculated_from_blended_rent(self):
        s = _subject()
        rent, yld = estimate_rental(s, 400_000 * 100)
        expected_yld = round((rent * 12) / (400_000 * 100) * 100, 2)
        assert yld == pytest.approx(expected_yld, rel=0.01)


# ─────────────────────────────────────────────────────────────────────
# 6. Full engine — integration tests
# ─────────────────────────────────────────────────────────────────────

class TestValuationEngine:
    def _run(self, n_comps: int = 8, price: int = 500_000) -> ValuationResult:
        s = _subject()
        comps = [_comp(price=price + i * 1_000, days_ago=30 + i * 10) for i in range(n_comps)]
        return _engine().run(s, comps)

    def test_result_has_correct_fields(self):
        r = self._run()
        assert r.estimated_value > 0
        assert r.range_low < r.estimated_value < r.range_high
        assert 0 < r.confidence.overall <= 1.0
        assert r.rental_monthly > 0
        assert 0 < r.rental_yield < 20

    def test_range_contains_estimate(self):
        r = self._run()
        assert r.range_low <= r.estimated_value <= r.range_high

    def test_more_comps_gives_higher_confidence(self):
        r_few  = self._run(n_comps=3)
        r_many = self._run(n_comps=15)
        assert r_many.confidence.overall >= r_few.confidence.overall

    def test_insufficient_data_raises(self):
        s = SubjectProperty(postcode="SW1A 1AA")  # no area, no last sale
        with pytest.raises(InsufficientDataError):
            _engine().run(s, [_comp()])            # only 1 comp → below min

    def test_methodology_audit_trail_present(self):
        r = self._run()
        m = r.methodology
        for key in ("generated_at", "methods_available", "blend_inputs",
                    "final_estimate_gbp", "confidence_overall", "range_spread_pct"):
            assert key in m

    def test_blend_uses_all_methods_when_data_complete(self):
        s = _subject(last_price=480_000, last_date=_days_ago(365))
        comps = [_comp() for _ in range(8)]
        r = _engine().run(s, comps)
        method_names = {m.method for m in r.method_results}
        assert "comparable_sales" in method_names
        assert "price_per_m2"     in method_names
        assert "last_sale_growth" in method_names

    def test_gbp_accessors_divide_by_100(self):
        r = self._run()
        assert r.estimated_value_gbp == pytest.approx(r.estimated_value / 100, rel=0.001)
        assert r.range_low_gbp       == pytest.approx(r.range_low       / 100, rel=0.001)
        assert r.range_high_gbp      == pytest.approx(r.range_high      / 100, rel=0.001)

    def test_confidence_breakdown_sums_are_in_range(self):
        r = self._run()
        cb = r.confidence
        for score in [cb.sample_size_score, cb.recency_score,
                      cb.similarity_score, cb.method_agreement, cb.overall]:
            assert 0.0 <= score <= 1.0

    def test_stale_comps_excluded_from_scoring(self):
        s = _subject()
        fresh = [_comp(price=500_000, days_ago=60) for _ in range(5)]
        stale = [_comp(price=150_000, days_ago=1500) for _ in range(5)]  # way too old
        r = _engine().run(s, fresh + stale)
        # Stale comps at £150k shouldn't pull estimate near that
        assert r.estimated_value > 40_000_000   # > £400k in pence

    def test_scored_comps_in_result(self):
        r = self._run(n_comps=6)
        assert len(r.scored_comps) == 6
        for sc in r.scored_comps:
            assert sc.similarity > 0
            assert sc.adjusted_price > 0
