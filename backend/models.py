"""
Data models for the valuation engine.
Pure dataclasses — no ORM, no I/O, fully testable in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class PropertyType(str, Enum):
    DETACHED      = "detached"
    SEMI_DETACHED = "semi_detached"
    TERRACED      = "terraced"
    FLAT          = "flat"
    BUNGALOW      = "bungalow"
    MAISONETTE    = "maisonette"
    OTHER         = "other"


class Tenure(str, Enum):
    FREEHOLD           = "freehold"
    LEASEHOLD          = "leasehold"
    SHARE_OF_FREEHOLD  = "share_of_freehold"


# ─────────────────────────────────────────────────────────────────────
# INPUT MODELS
# ─────────────────────────────────────────────────────────────────────

@dataclass
class SubjectProperty:
    """The property being valued."""
    postcode:         str
    property_type:    PropertyType | None  = None
    bedrooms:         int   | None         = None
    bathrooms:        int   | None         = None
    floor_area_m2:    float | None         = None
    year_built:       int   | None         = None
    epc_rating:       str   | None         = None   # A–G
    tenure:           Tenure | None        = None
    lease_years:      int   | None         = None   # remaining lease
    last_sale_price:  int   | None         = None   # pence
    last_sale_date:   date  | None         = None
    has_garden:       bool                 = False
    has_parking:      bool                 = False
    has_garage:       bool                 = False
    is_new_build:     bool                 = False


@dataclass
class ComparableSale:
    """A nearby sold property used as evidence."""
    address:          str
    postcode:         str
    sale_price:       int            # pence
    sale_date:        date
    distance_m:       int            # metres from subject
    property_type:    PropertyType | None = None
    bedrooms:         int   | None        = None
    floor_area_m2:    float | None        = None
    source:           str                 = "land_registry"
    source_ref:       str | None          = None


# ─────────────────────────────────────────────────────────────────────
# OUTPUT MODELS
# ─────────────────────────────────────────────────────────────────────

@dataclass
class MethodResult:
    """Output from a single valuation method."""
    method:         str
    estimate:       int          # pence
    weight:         float        # 0–1, used in blending
    confidence:     float        # 0–1, method-level confidence
    supporting:     dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoredComparable:
    """A comparable with its computed similarity score."""
    comp:             ComparableSale
    similarity:       float        # 0–1
    age_days:         int
    price_per_m2:     int | None   # pence/m²
    adjusted_price:   int          # pence, after similarity adjustments
    adjustments:      dict[str, float] = field(default_factory=dict)


@dataclass
class ConfidenceBreakdown:
    """Itemised confidence scoring."""
    sample_size_score:   float   # driven by number of comps
    recency_score:       float   # driven by average age of comps
    similarity_score:    float   # driven by average comp similarity
    method_agreement:    float   # how closely the three methods agree
    overall:             float   # final blended score


@dataclass
class ValuationResult:
    """Complete output from the valuation engine."""
    estimated_value:   int              # pence — point estimate
    range_low:         int              # pence
    range_high:        int              # pence
    confidence:        ConfidenceBreakdown
    rental_monthly:    int              # pence
    rental_yield:      float            # gross % (e.g. 4.7)
    method_results:    list[MethodResult]
    scored_comps:      list[ScoredComparable]
    methodology:       dict[str, Any]

    # ── Convenience accessors ──────────────────────────────────────
    @property
    def estimated_value_gbp(self) -> float:
        return round(self.estimated_value / 100, 2)

    @property
    def range_low_gbp(self) -> float:
        return round(self.range_low / 100, 2)

    @property
    def range_high_gbp(self) -> float:
        return round(self.range_high / 100, 2)

    @property
    def rental_monthly_gbp(self) -> float:
        return round(self.rental_monthly / 100, 2)

    @property
    def confidence_score(self) -> float:
        return self.confidence.overall
