import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime,
    ForeignKey, Integer, Numeric, SmallInteger, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_plus_30d() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)


# ---------------------------------------------------------------
# USERS
# ---------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    valuation_reports: Mapped[list["ValuationReport"]] = relationship(
        back_populates="user", lazy="noload"
    )

    __table_args__ = (
        CheckConstraint("role IN ('user','admin','api')", name="ck_users_role"),
    )


# ---------------------------------------------------------------
# ADDRESSES
# ---------------------------------------------------------------
class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_1: Mapped[str] = mapped_column(Text, nullable=False)
    line_2: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    county: Mapped[str | None] = mapped_column(Text)
    postcode: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(3), nullable=False, default="GBR")
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    address_norm: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    properties: Mapped[list["Property"]] = relationship(
        back_populates="address", lazy="noload"
    )


# ---------------------------------------------------------------
# PROPERTIES
# ---------------------------------------------------------------
class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    address_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False
    )
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    bathrooms: Mapped[int | None] = mapped_column(SmallInteger)
    floor_area_m2: Mapped[float | None] = mapped_column(Numeric(8, 2))
    year_built: Mapped[int | None] = mapped_column(SmallInteger)
    epc_rating: Mapped[str | None] = mapped_column(String(1))
    epc_expiry: Mapped[datetime | None] = mapped_column(Date)
    tenure: Mapped[str | None] = mapped_column(String(30))
    lease_years_remaining: Mapped[int | None] = mapped_column(SmallInteger)
    is_new_build: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    council_tax_band: Mapped[str | None] = mapped_column(String(1))
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    external_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    address: Mapped["Address"] = relationship(back_populates="properties", lazy="joined")
    sales_transactions: Mapped[list["SalesTransaction"]] = relationship(
        back_populates="property", lazy="noload"
    )
    rental_listings: Mapped[list["RentalListing"]] = relationship(
        back_populates="property", lazy="noload"
    )
    valuation_reports: Mapped[list["ValuationReport"]] = relationship(
        back_populates="property", lazy="noload"
    )

    __table_args__ = (
        CheckConstraint(
            "property_type IN ('detached','semi_detached','terraced','flat',"
            "'bungalow','maisonette','other')",
            name="ck_property_type",
        ),
        CheckConstraint("bedrooms >= 0", name="ck_bedrooms_positive"),
        CheckConstraint("floor_area_m2 > 0", name="ck_floor_area_positive"),
    )


# ---------------------------------------------------------------
# SALES TRANSACTIONS
# ---------------------------------------------------------------
class SalesTransaction(Base):
    __tablename__ = "sales_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    price_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    transaction_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="standard"
    )
    is_cash_purchase: Mapped[bool | None] = mapped_column(Boolean)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    property: Mapped["Property"] = relationship(back_populates="sales_transactions")

    __table_args__ = (
        UniqueConstraint("source", "source_ref", name="uq_sales_source_ref"),
        CheckConstraint("price_pence > 0", name="ck_sales_price_positive"),
    )


# ---------------------------------------------------------------
# RENTAL LISTINGS
# ---------------------------------------------------------------
class RentalListing(Base):
    __tablename__ = "rental_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    monthly_rent_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    listed_date: Mapped[datetime | None] = mapped_column(Date)
    let_agreed_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text)
    min_tenancy_months: Mapped[int | None] = mapped_column(SmallInteger)
    deposit_pence: Mapped[int | None] = mapped_column(BigInteger)
    bills_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    furnished: Mapped[str | None] = mapped_column(String(20))
    pets_allowed: Mapped[bool | None] = mapped_column(Boolean)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    property: Mapped["Property"] = relationship(back_populates="rental_listings")

    __table_args__ = (
        UniqueConstraint("source", "source_ref", name="uq_rental_source_ref"),
        CheckConstraint(
            "status IN ('active','let','withdrawn')", name="ck_rental_status"
        ),
    )


# ---------------------------------------------------------------
# VALUATION REPORTS
# ---------------------------------------------------------------
class ValuationReport(Base):
    __tablename__ = "valuation_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    estimated_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    range_low: Mapped[int] = mapped_column(BigInteger, nullable=False)
    range_high: Mapped[int] = mapped_column(BigInteger, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    rental_monthly: Mapped[int | None] = mapped_column(BigInteger)
    rental_yield: Mapped[float | None] = mapped_column(Numeric(5, 2))
    methodology: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_apis: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    pdf_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_plus_30d
    )

    property: Mapped["Property"] = relationship(
        back_populates="valuation_reports", lazy="joined"
    )
    user: Mapped["User | None"] = relationship(
        back_populates="valuation_reports", lazy="noload"
    )
    comparables: Mapped[list["Comparable"]] = relationship(
        back_populates="valuation", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','complete','failed')", name="ck_valuation_status"
        ),
        CheckConstraint(
            "confidence_score BETWEEN 0 AND 1", name="ck_confidence_range"
        ),
        CheckConstraint(
            "range_high >= range_low", name="ck_range_ordering"
        ),
    )


# ---------------------------------------------------------------
# COMPARABLES
# ---------------------------------------------------------------
class Comparable(Base):
    __tablename__ = "comparables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    valuation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("valuation_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL")
    )
    address_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    postcode_snapshot: Mapped[str] = mapped_column(String(10), nullable=False)
    property_type: Mapped[str | None] = mapped_column(String(50))
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    floor_area_m2: Mapped[float | None] = mapped_column(Numeric(8, 2))
    sale_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sale_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    price_per_m2: Mapped[int | None] = mapped_column(BigInteger)
    distance_m: Mapped[int | None] = mapped_column(Integer)
    similarity_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    adjustment_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    valuation: Mapped["ValuationReport"] = relationship(back_populates="comparables")
