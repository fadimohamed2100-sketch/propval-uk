"""
Unit tests for the valuation engine and core service logic.
Run with: pytest tests/ -v
"""
import pytest
from datetime import date, timedelta
from services.valuation_engine import ComparableInput, ValuationEngine


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------
@pytest.fixture
def engine():
    return ValuationEngine()


def _make_comp(
    price: int,
    days_ago: int = 180,
    prop_type: str = "terraced",
    bedrooms: int = 3,
    floor_area: float = 90.0,
    distance_m: int = 300,
) -> ComparableInput:
    return ComparableInput(
        address=f"Test Street, London",
        postcode="SW1A 1AA",
        sale_price=price * 100,       # convert to pence
        sale_date=date.today() - timedelta(days=days_ago),
        property_type=prop_type,
        bedrooms=bedrooms,
        floor_area_m2=floor_area,
        distance_m=distance_m,
        source="land_registry",
    )


# ---------------------------------------------------------------
# Valuation engine — happy path
# ---------------------------------------------------------------
def test_engine_returns_result_with_enough_comps(engine):
    comps = [_make_comp(500_000 + i * 1_000) for i in range(5)]
    result = engine.run(
        subject_type="terraced",
        subject_bedrooms=3,
        subject_floor_area_m2=90.0,
        comps=comps,
    )
    assert result.estimated_value > 0
    assert result.range_low < result.estimated_value < result.range_high
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.rental_monthly > 0


def test_engine_raises_with_too_few_comps(engine):
    comps = [_make_comp(500_000)]  # only 1 comp
    with pytest.raises(ValueError, match="minimum"):
        engine.run(
            subject_type="terraced",
            subject_bedrooms=3,
            subject_floor_area_m2=90.0,
            comps=comps,
        )


def test_engine_excludes_stale_comps(engine):
    fresh = [_make_comp(500_000 + i * 1_000) for i in range(4)]
    stale = [_make_comp(200_000, days_ago=1500)]  # over 3 years old
    result = engine.run(
        subject_type="terraced",
        subject_bedrooms=3,
        subject_floor_area_m2=90.0,
        comps=fresh + stale,
    )
    # Stale comp should not pull estimate down to 200k
    assert result.estimated_value > 40_000_000  # > £400k in pence


def test_engine_confidence_increases_with_more_comps(engine):
    few = [_make_comp(500_000 + i * 500) for i in range(3)]
    many = [_make_comp(500_000 + i * 500) for i in range(15)]

    r_few = engine.run(
        subject_type="terraced", subject_bedrooms=3,
        subject_floor_area_m2=90.0, comps=few,
    )
    r_many = engine.run(
        subject_type="terraced", subject_bedrooms=3,
        subject_floor_area_m2=90.0, comps=many,
    )
    assert r_many.confidence_score >= r_few.confidence_score


def test_engine_type_mismatch_penalises_comp(engine):
    matched = [_make_comp(500_000, prop_type="terraced") for _ in range(5)]
    mismatched = [_make_comp(800_000, prop_type="detached") for _ in range(5)]
    comps = matched + mismatched

    result = engine.run(
        subject_type="terraced",
        subject_bedrooms=3,
        subject_floor_area_m2=90.0,
        comps=comps,
    )
    # Estimate should be pulled toward the matched comps (£500k)
    assert result.estimated_value < 65_000_000  # < £650k in pence


def test_engine_rental_estimate_plausible(engine):
    comps = [_make_comp(400_000 + i * 1_000) for i in range(5)]
    result = engine.run(
        subject_type="terraced",
        subject_bedrooms=3,
        subject_floor_area_m2=90.0,
        comps=comps,
    )
    # Gross yield for terraced ~4.7% → monthly ~£1,567 on £400k
    assert 100_000 < result.rental_monthly < 500_000   # £1k – £5k/mo in pence
    assert 2.0 < result.rental_yield < 12.0


def test_engine_methodology_contains_expected_keys(engine):
    comps = [_make_comp(500_000 + i * 1_000) for i in range(5)]
    result = engine.run(
        subject_type="terraced",
        subject_bedrooms=3,
        subject_floor_area_m2=90.0,
        comps=comps,
    )
    for key in ("method", "comps_used", "comps_considered", "spread_pct"):
        assert key in result.methodology


# ---------------------------------------------------------------
# Geocoder normalisation (pure function, no network)
# ---------------------------------------------------------------
def test_address_normalisation():
    from services.geocoder import _normalise
    assert _normalise("42 Acacia Avenue, London, SW1A 1AA") == \
           _normalise("  42 ACACIA AVENUE,  LONDON,  SW1A 1AA  ")
