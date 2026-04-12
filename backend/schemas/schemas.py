"""
Pydantic v2 schemas.

Convention:
  *Base   — shared fields
  *Create — inbound (POST body)
  *Out    — outbound (response)
  *Detail — outbound with nested relations
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ================================================================
# Shared helpers
# ================================================================
class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _pence_to_pounds(pence: int | None) -> float | None:
    if pence is None:
        return None
    return round(pence / 100, 2)


# ================================================================
# ADDRESS
# ================================================================
class AddressSearchRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=300, examples=["42 Acacia Avenue, London, SW1A 1AA"])


class AddressOut(_OrmBase):
    id: uuid.UUID
    line_1: str
    line_2: str | None
    city: str
    county: str | None
    postcode: str
    country: str
    lat: float | None
    lng: float | None
    created_at: datetime


class AddressSearchResponse(BaseModel):
    """Returned by POST /address/search."""
    address: AddressOut
    property: PropertyOut | None = None
    message: str = "Address resolved successfully."


# ================================================================
# PROPERTY
# ================================================================
class PropertyOut(_OrmBase):
    id: uuid.UUID
    address_id: uuid.UUID
    property_type: str
    bedrooms: int | None
    bathrooms: int | None
    floor_area_m2: float | None
    year_built: int | None
    epc_rating: str | None
    tenure: str | None
    is_new_build: bool
    council_tax_band: str | None
    features: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PropertyDetailOut(_OrmBase):
    """Includes nested address."""
    id: uuid.UUID
    address: AddressOut
    property_type: str
    bedrooms: int | None
    bathrooms: int | None
    floor_area_m2: float | None
    year_built: int | None
    epc_rating: str | None
    tenure: str | None
    lease_years_remaining: int | None
    is_new_build: bool
    council_tax_band: str | None
    features: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ================================================================
# VALUATION
# ================================================================
class ValuationRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=300)
    force_refresh: bool = Field(
        default=False,
        description="Ignore cached valuation and recompute.",
    )


class ComparableOut(_OrmBase):
    id: uuid.UUID
    address_snapshot: str
    postcode_snapshot: str
    property_type: str | None
    bedrooms: int | None
    floor_area_m2: float | None
    sale_price_gbp: float
    sale_date: date
    price_per_m2_gbp: float | None
    distance_m: int | None
    similarity_score: float | None
    adjustment_pct: float | None
    source: str

    @classmethod
    def from_orm_with_pounds(cls, obj: Any) -> "ComparableOut":
        data = {
            **{c.key: getattr(obj, c.key) for c in obj.__table__.columns},
            "sale_price_gbp": _pence_to_pounds(obj.sale_price),
            "price_per_m2_gbp": _pence_to_pounds(obj.price_per_m2),
        }
        return cls.model_validate(data)


class ValuationOut(_OrmBase):
    id: uuid.UUID
    property_id: uuid.UUID
    status: str
    estimated_value_gbp: float | None = None
    range_low_gbp: float | None = None
    range_high_gbp: float | None = None
    confidence_score: float | None = None
    rental_monthly_gbp: float | None = None
    rental_yield: float | None = None
    source_apis: list[str]
    comparables: list[ComparableOut] = []
    pdf_url: str | None = None
    created_at: datetime
    expires_at: datetime


class ValuationDetailOut(ValuationOut):
    property: PropertyDetailOut | None = None
    methodology: dict[str, Any]


# ================================================================
# USERS  (minimal — extend for full auth)
# ================================================================
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=8, max_length=128)


class UserOut(_OrmBase):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


# ================================================================
# GENERIC RESPONSE WRAPPERS
# ================================================================
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
