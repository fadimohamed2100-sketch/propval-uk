"""
seed.py
~~~~~~~
Seeds the PropVal PostgreSQL database with realistic UK property data.

Usage:
    # From the backend/ root directory:
    python -m seeder.seed

    # Or directly:
    python seeder/seed.py

    # Force reseed (wipes existing seed data first):
    python seeder/seed.py --reset

Idempotent: re-running without --reset skips records that already exist
(matched on address_norm for addresses, source_ref for transactions).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running from backend/ root
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings
from models.orm import (
    Address, Comparable, Property, RentalListing,
    SalesTransaction, ValuationReport,
)
from seeder.uk_property_data import (
    AREA_PROFILES, COMPARABLE_SALES, PROPERTIES, RENTAL_LISTINGS, VALUATIONS,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("seeder")

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _normalise(address: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace — dedup key."""
    s = address.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _area_profile(postcode_prefix: str):
    for p in AREA_PROFILES:
        if p.postcode_prefix == postcode_prefix:
            return p
    return None


# ─────────────────────────────────────────────────────────────────────
# Seeder
# ─────────────────────────────────────────────────────────────────────

class Seeder:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._property_id_map: dict[int, uuid.UUID] = {}   # idx → DB UUID
        self._address_id_map:  dict[int, uuid.UUID] = {}

    async def run(self, reset: bool = False) -> None:
        if reset:
            await self._wipe()

        log.info("Seeding addresses and properties…")
        await self._seed_properties()

        log.info("Seeding comparable sales…")
        await self._seed_comparables()

        log.info("Seeding rental listings…")
        await self._seed_rentals()

        log.info("Seeding valuations…")
        await self._seed_valuations()

        await self.session.commit()
        log.info("✓ Seed complete.")

    # ── Wipe ──────────────────────────────────────────────────────

    async def _wipe(self) -> None:
        log.warning("⚠  Wiping seed data from all tables…")
        # Order matters — FK constraints
        for Model in [Comparable, ValuationReport, RentalListing,
                      SalesTransaction, Property, Address]:
            await self.session.execute(delete(Model))
        await self.session.flush()
        log.info("   Tables cleared.")

    # ── Properties ────────────────────────────────────────────────

    async def _seed_properties(self) -> None:
        for idx, record in enumerate(PROPERTIES):
            addr_data = record["address"]
            prop_data = record["property"]
            last_sale = record.get("last_sale")

            # 1. Address — upsert on address_norm
            full_address = f"{addr_data['line_1']}, {addr_data['city']}, {addr_data['postcode']}"
            norm         = _normalise(full_address)

            result = await self.session.execute(
                select(Address).where(Address.address_norm == norm)
            )
            address = result.scalar_one_or_none()

            if not address:
                address = Address(
                    line_1       = addr_data["line_1"],
                    line_2       = addr_data.get("line_2"),
                    city         = addr_data["city"],
                    county       = addr_data.get("county"),
                    postcode     = addr_data["postcode"],
                    country      = "GBR",
                    lat          = addr_data.get("lat"),
                    lng          = addr_data.get("lng"),
                    address_norm = norm,
                )
                self.session.add(address)
                await self.session.flush()

            self._address_id_map[idx] = address.id

            # 2. Property — skip if one already exists for this address
            result = await self.session.execute(
                select(Property).where(Property.address_id == address.id).limit(1)
            )
            existing_prop = result.scalar_one_or_none()

            if existing_prop:
                self._property_id_map[idx] = existing_prop.id
                log.info(f"   [skip] property already exists: {addr_data['line_1']}")
                continue

            property_ = Property(
                address_id            = address.id,
                property_type         = prop_data["property_type"],
                bedrooms              = prop_data.get("bedrooms"),
                bathrooms             = prop_data.get("bathrooms"),
                floor_area_m2         = prop_data.get("floor_area_m2"),
                year_built            = prop_data.get("year_built"),
                epc_rating            = prop_data.get("epc_rating"),
                tenure                = prop_data.get("tenure"),
                lease_years_remaining = prop_data.get("lease_years_remaining"),
                is_new_build          = prop_data.get("is_new_build", False),
                council_tax_band      = prop_data.get("council_tax_band"),
                features              = prop_data.get("features", {}),
                external_ids          = prop_data.get("external_ids", {}),
            )
            self.session.add(property_)
            await self.session.flush()
            self._property_id_map[idx] = property_.id

            # 3. Historical sale record for this property
            if last_sale:
                ref = f"seed_{property_.id}_last"
                result = await self.session.execute(
                    select(SalesTransaction).where(SalesTransaction.source_ref == ref)
                )
                if not result.scalar_one_or_none():
                    txn = SalesTransaction(
                        property_id      = property_.id,
                        price_pence      = last_sale["price_pence"],
                        transaction_date = last_sale["date"],
                        transaction_type = last_sale.get("type", "standard"),
                        source           = "land_registry",
                        source_ref       = ref,
                    )
                    self.session.add(txn)

            log.info(f"   + property: {addr_data['line_1']}, {addr_data['postcode']}")

    # ── Comparable sales ──────────────────────────────────────────

    async def _seed_comparables(self) -> None:
        for i, comp in enumerate(COMPARABLE_SALES):
            ref = f"seed_comp_{i}_{comp['postcode'].replace(' ','')}_{comp['date'].isoformat()}"

            result = await self.session.execute(
                select(SalesTransaction).where(SalesTransaction.source_ref == ref)
            )
            if result.scalar_one_or_none():
                continue

            # Find or create an address for this comparable
            norm = _normalise(f"{comp['address']}, {comp['postcode']}")
            result = await self.session.execute(
                select(Address).where(Address.address_norm == norm)
            )
            addr = result.scalar_one_or_none()
            if not addr:
                addr = Address(
                    line_1       = comp["address"],
                    city         = "Unknown",
                    postcode     = comp["postcode"],
                    address_norm = norm,
                )
                self.session.add(addr)
                await self.session.flush()

            # Find or create a property stub
            result = await self.session.execute(
                select(Property).where(Property.address_id == addr.id).limit(1)
            )
            prop = result.scalar_one_or_none()
            if not prop:
                prop = Property(
                    address_id    = addr.id,
                    property_type = comp.get("type", "flat"),
                    bedrooms      = comp.get("bedrooms"),
                    floor_area_m2 = comp.get("floor_area_m2"),
                    is_new_build  = False,
                    features      = {},
                    external_ids  = {},
                )
                self.session.add(prop)
                await self.session.flush()

            txn = SalesTransaction(
                property_id      = prop.id,
                price_pence      = comp["price_pence"],
                transaction_date = comp["date"],
                transaction_type = "standard",
                source           = comp.get("source", "land_registry"),
                source_ref       = ref,
            )
            self.session.add(txn)

        log.info(f"   + {len(COMPARABLE_SALES)} comparable sales")

    # ── Rental listings ───────────────────────────────────────────

    async def _seed_rentals(self) -> None:
        for i, listing in enumerate(RENTAL_LISTINGS):
            prop_idx = listing["property_idx"]
            prop_id  = self._property_id_map.get(prop_idx)
            if not prop_id:
                log.warning(f"   [skip] rental #{i}: property idx {prop_idx} not found")
                continue

            ref = f"seed_rental_{i}_{prop_id}"
            result = await self.session.execute(
                select(RentalListing).where(RentalListing.source_ref == ref)
            )
            if result.scalar_one_or_none():
                continue

            rent = RentalListing(
                property_id        = prop_id,
                monthly_rent_pence = listing["rent_pence"],
                status             = listing.get("status", "let"),
                source             = listing.get("source", "rightmove"),
                source_ref         = ref,
                listed_date        = listing.get("listed_date"),
                let_agreed_date    = listing.get("let_date"),
                min_tenancy_months = listing.get("min_tenancy_months", 12),
                bills_included     = listing.get("bills_included", False),
                furnished          = listing.get("furnished"),
            )
            self.session.add(rent)

        log.info(f"   + {len(RENTAL_LISTINGS)} rental listings")

    # ── Valuations ────────────────────────────────────────────────

    async def _seed_valuations(self) -> None:
        for v in VALUATIONS:
            prop_id = self._property_id_map.get(v["property_idx"])
            if not prop_id:
                continue

            # Skip if a complete valuation already exists for this property
            result = await self.session.execute(
                select(ValuationReport).where(
                    ValuationReport.property_id == prop_id,
                    ValuationReport.status      == "complete",
                ).limit(1)
            )
            if result.scalar_one_or_none():
                log.info(f"   [skip] valuation already exists for property_id={prop_id}")
                continue

            report = ValuationReport(
                property_id     = prop_id,
                estimated_value = v["estimated_value"],
                range_low       = v["range_low"],
                range_high      = v["range_high"],
                confidence_score= v["confidence_score"],
                rental_monthly  = v["rental_monthly"],
                rental_yield    = v["rental_yield"],
                status          = v["status"],
                source_apis     = v["source_apis"],
                methodology     = v["methodology"],
                expires_at      = _now() + timedelta(days=30),
            )
            self.session.add(report)
            await self.session.flush()

            # Attach 6 closest comparables from COMPARABLE_SALES
            await self._attach_comparables(report, prop_id)

            log.info(
                f"   + valuation: £{v['estimated_value']//100:,} "
                f"(conf: {v['confidence_score']:.0%})"
            )

    async def _attach_comparables(
        self,
        report:  ValuationReport,
        prop_id: uuid.UUID,
    ) -> None:
        """
        Link the 6 nearest comparable sales to this valuation report.
        Uses SalesTransaction + Address to build Comparable rows.
        """
        # Fetch 6 recently inserted comparable transactions (by source_ref prefix)
        result = await self.session.execute(
            select(SalesTransaction, Address)
            .join(Property, SalesTransaction.property_id == Property.id)
            .join(Address, Property.address_id == Address.id)
            .where(SalesTransaction.source_ref.like("seed_comp_%"))
            .order_by(SalesTransaction.transaction_date.desc())
            .limit(6)
        )
        rows = result.all()

        for txn, addr in rows:
            # Find matching comp data for floor area
            comp_data = next(
                (c for c in COMPARABLE_SALES if addr.line_1 == c["address"]), {}
            )
            price_per_m2 = None
            if comp_data.get("floor_area_m2") and txn.price_pence:
                price_per_m2 = int(txn.price_pence / comp_data["floor_area_m2"])

            comp = Comparable(
                valuation_id      = report.id,
                address_snapshot  = addr.line_1,
                postcode_snapshot = addr.postcode,
                property_type     = comp_data.get("type"),
                bedrooms          = comp_data.get("bedrooms"),
                floor_area_m2     = comp_data.get("floor_area_m2"),
                sale_price        = txn.price_pence,
                sale_date         = txn.transaction_date,
                price_per_m2      = price_per_m2,
                distance_m        = comp_data.get("distance_m"),
                similarity_score  = round(0.55 + (hash(addr.line_1) % 40) / 100, 3),
                source            = txn.source,
            )
            self.session.add(comp)


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

async def main(reset: bool = False) -> None:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )

    # Auto-create tables if they don't exist (dev convenience)
    from db.session import Base
    import models.orm  # noqa — registers all models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSession_ = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSession_() as session:
        seeder = Seeder(session)
        await seeder.run(reset=reset)

    await engine.dispose()
    log.info("Database connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the PropVal database")
    parser.add_argument("--reset", action="store_true",
                        help="Wipe all existing data before seeding")
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))
