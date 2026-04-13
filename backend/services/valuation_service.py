"""
ValuationService — the main orchestrator.

Coordinates:
  1. Geocode the address
  2. Upsert Address + Property rows
  3. Check for a fresh cached valuation
  4. Fetch comparable sales from Land Registry
  5. Run the valuation engine
  6. Persist ValuationReport + Comparables
  7. Kick off async PDF generation
"""
from __future__ import annotations
from core.config import get_settings
settings = get_settings()

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import ValuationFailedError, ValuationNotFoundError
from core.logging import get_logger
from models.orm import Address, Comparable, Property, ValuationReport
from services.geocoder import GeocoderService
from services.pdf_generator import build_report_context, generate_report_pdf
from services.property_data import PropertyDataService
from services.valuation_engine import ComparableInput, ValuationEngine

logger = get_logger(__name__)


class ValuationService:
    def __init__(
        self,
        db: AsyncSession,
        geocoder: GeocoderService,
        property_data: PropertyDataService,
        engine: ValuationEngine,
    ) -> None:
        self._db = db
        self._geocoder = geocoder
        self._property_data = property_data
        self._engine = engine

    # ------------------------------------------------------------------
    # POST /address/search
    # ------------------------------------------------------------------
    async def resolve_address(self, raw_address: str) -> tuple[Address, Property | None]:
        """
        Geocodes an address and returns (Address, Property | None).
        Creates an Address row if it doesn't exist yet.
        """
        geo = await self._geocoder.geocode(raw_address)

        # Upsert address by normalised form
        stmt = select(Address).where(Address.address_norm == geo["address_norm"])
        result = await self._db.execute(stmt)
        address = result.scalar_one_or_none()

        if not address:
            address = Address(**geo)
            self._db.add(address)
            await self._db.flush()  # get the id without committing

        # Look for an existing property at this address
        stmt = select(Property).where(Property.address_id == address.id).limit(1)
        result = await self._db.execute(stmt)
        property_ = result.scalar_one_or_none()

        return address, property_

    # ------------------------------------------------------------------
    # POST /valuation/run
    # ------------------------------------------------------------------
    async def run_valuation(
        self,
        raw_address: str,
        user_id: uuid.UUID | None = None,
        force_refresh: bool = False,
    ) -> ValuationReport:
        address, property_ = await self.resolve_address(raw_address)

        # Enrich property from EPC if we have one
        epc = await self._property_data.get_epc_data(address.postcode)

        if not property_:
            property_ = await self._create_property(address, epc)
        elif epc and not property_.floor_area_m2:
            property_.floor_area_m2 = epc.get("floor_area_m2")
            property_.epc_rating = epc.get("epc_rating")

        # Return cached valuation unless force_refresh
        if not force_refresh:
            cached = await self._fresh_valuation(property_.id)
            if cached:
                logger.info("valuation_cache_hit", property_id=str(property_.id))
                return cached

        # Fetch comparables from Land Registry, fall back to DB
        comp_inputs = [
            ComparableInput(
                address=s["address"],
                postcode=s["postcode"],
                sale_price=s["price_pence"],
                sale_date=s["transaction_date"],
                property_type=property_.property_type,
                bedrooms=property_.bedrooms,
                floor_area_m2=property_.floor_area_m2,
                source=s["source"],
            )
            for s in raw_sales
        ]

        # Run the engine
        try:
            result = self._engine.run(
                subject_type=property_.property_type,
                subject_bedrooms=property_.bedrooms,
                subject_floor_area_m2=property_.floor_area_m2,
                comps=comp_inputs,
            )
        except ValueError as exc:
            raise ValuationFailedError(str(exc))

        # Persist ValuationReport
        report = ValuationReport(
            property_id=property_.id,
            user_id=user_id,
            estimated_value=result.estimated_value,
            range_low=result.range_low,
            range_high=result.range_high,
            confidence_score=result.confidence_score,
            rental_monthly=result.rental_monthly,
            rental_yield=result.rental_yield,
            methodology=result.methodology,
            source_apis=["land_registry"] + (["epc"] if epc else []),
            status="complete",
        )
        self._db.add(report)
        await self._db.flush()

        # Persist Comparables
        for comp_dict in result.comparables_used:
            comp = Comparable(
                valuation_id=report.id,
                **comp_dict,
            )
            self._db.add(comp)

        await self._db.flush()

        # Generate PDF (sync for MVP; move to background task in production)
        try:
            context = build_report_context(report, property_, address, [])
            pdf_path = generate_report_pdf(context)
            report.pdf_path = pdf_path
        except Exception as exc:
            logger.warning("pdf_generation_failed", error=str(exc))

        return report

    # ------------------------------------------------------------------
    # GET /valuation/{id}
    # ------------------------------------------------------------------
    async def get_valuation(self, valuation_id: uuid.UUID) -> ValuationReport:
        stmt = (
            select(ValuationReport)
            .where(ValuationReport.id == valuation_id)
            .options(
                selectinload(ValuationReport.comparables),
                selectinload(ValuationReport.property).selectinload(Property.address),
            )
        )
        result = await self._db.execute(stmt)
        report = result.scalar_one_or_none()
        if not report:
            raise ValuationNotFoundError(str(valuation_id))
        return report

    # ------------------------------------------------------------------
    # GET /property/{id}
    # ------------------------------------------------------------------
    async def get_property(self, property_id: uuid.UUID) -> Property:
        from core.exceptions import PropertyNotFoundError
        stmt = (
            select(Property)
            .where(Property.id == property_id)
            .options(selectinload(Property.address))
        )
        result = await self._db.execute(stmt)
        property_ = result.scalar_one_or_none()
        if not property_:
            raise PropertyNotFoundError(str(property_id))
        return property_

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _fresh_valuation(self, property_id: uuid.UUID) -> ValuationReport | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(ValuationReport)
            .where(
                ValuationReport.property_id == property_id,
                ValuationReport.status == "complete",
                ValuationReport.expires_at > now,
            )
            .options(
                selectinload(ValuationReport.comparables),
                selectinload(ValuationReport.property).selectinload(Property.address),
            )
            .order_by(ValuationReport.created_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_property(
        self, address: Address, epc: dict | None
    ) -> Property:
        property_ = Property(
            address_id=address.id,
            property_type=(epc or {}).get("property_type") or "other",
            floor_area_m2=(epc or {}).get("floor_area_m2"),
            epc_rating=(epc or {}).get("epc_rating"),
        )
        self._db.add(property_)
        await self._db.flush()
        return property_
