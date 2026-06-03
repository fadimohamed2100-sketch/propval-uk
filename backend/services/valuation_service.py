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
        bedrooms: int | None = None,
        bathrooms: int | None = None,
        condition: str | None = None,
        parking: str | None = None,
        outdoor_space: str | None = None,
        property_type: str | None = None,
        tenure: str | None = None,
        lease_years: int | None = None,
    ) -> ValuationReport:
        address, property_ = await self.resolve_address(raw_address)

        # Enrich property from EPC if we have one
        epc = await self._property_data.get_epc_data(address.postcode)

        # Override EPC data with user-provided values if available
        if bedrooms and epc:
            epc["bedrooms"] = bedrooms
        if property_type:
            if epc:
                epc["property_type"] = property_type
            if property_:
                property_.property_type = property_type
        if not property_:
            property_ = await self._create_property(address, epc)
        if property_:
            if bedrooms:
                property_.bedrooms = bedrooms
            elif epc and not property_.bedrooms:
                property_.bedrooms = epc.get("bedrooms")
            if epc and not property_.floor_area_m2:
                property_.floor_area_m2 = epc.get("floor_area_m2")
                property_.epc_rating = epc.get("epc_rating")

        # Return cached valuation unless force_refresh
        effective_bedrooms = bedrooms or property_.bedrooms
        if not force_refresh:
            cached = await self._fresh_valuation(property_.id, bedrooms=effective_bedrooms, property_type=property_.property_type, tenure=tenure)
            if cached:
                logger.info("valuation_cache_hit", property_id=str(property_.id))
                return cached

        # Fetch comparables — PropertyData first, then seeded DB
        pd_type_map = {"flat": "flat", "terraced": "terraced", "semi_detached": "semi-detached", "detached": "detached", "other": "terraced"}
        pd_property_type = pd_type_map.get(property_.property_type or "other", "terraced")
        raw_sales = await self._property_data.get_propertydata_sold_prices(address.postcode, pd_property_type, bedrooms=effective_bedrooms, tenure=tenure)
        if not raw_sales:
            from sqlalchemy import text
            result = await self._db.execute(
                text("""
                    SELECT a.address_norm, a.postcode, st.price_pence, st.transaction_date, p.property_type, st.source
                    FROM sales_transactions st
                    JOIN properties p ON st.property_id = p.id
                    JOIN addresses a ON p.address_id = a.id
                    LIMIT 50
                """)
            )
            raw_sales = [
                {"address": r[0], "postcode": r[1], "price_pence": int(r[2]), "transaction_date": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]), "source": r[5]}
                for r in result.fetchall()
            ]
        comp_inputs = [
            ComparableInput(
                address=s["address"],
                postcode=s["postcode"],
                sale_price=s["price_pence"],
                sale_date=__import__("datetime").date.fromisoformat(str(s["transaction_date"])[:10]) if s["transaction_date"] else None,
                property_type=property_.property_type,
                bedrooms=property_.bedrooms,
                floor_area_m2=property_.floor_area_m2,
                source=s["source"],
            )
            for s in raw_sales
        ]

        # Get PropertyData direct valuation (primary)
        pd_valuation = await self._property_data.get_propertydata_valuation(
            address.postcode, pd_property_type,
            bedrooms=effective_bedrooms or property_.bedrooms,
            floor_area_m2=property_.floor_area_m2,
            bathrooms=bathrooms, condition=condition, parking=parking, outdoor_space=outdoor_space
        )
        pd_rent = await self._property_data.get_propertydata_rent(
            address.postcode, effective_bedrooms or property_.bedrooms
        )

        # Run the engine
        try:
            result = self._engine.run(
                subject_type=property_.property_type,
                subject_bedrooms=effective_bedrooms or property_.bedrooms,
                subject_floor_area_m2=property_.floor_area_m2,
                comps=comp_inputs,
            )
        except ValueError as exc:
            raise ValuationFailedError(str(exc))

        # Apply lease years adjustment if leasehold
        lease_adjustment = 1.0
        if tenure == "leasehold" and lease_years:
            if lease_years >= 90:
                lease_adjustment = 1.0
            elif lease_years >= 80:
                lease_adjustment = 0.95
            elif lease_years >= 70:
                lease_adjustment = 0.90
            elif lease_years >= 60:
                lease_adjustment = 0.85
            elif lease_years >= 50:
                lease_adjustment = 0.75
            else:
                lease_adjustment = 0.60
            result.estimated_value = int(result.estimated_value * lease_adjustment)
            result.range_low = int(result.range_low * lease_adjustment)
            result.range_high = int(result.range_high * lease_adjustment)

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
            source_apis=["propertydata"] + (["epc"] if epc else []),
            status="complete",
        )
        self._db.add(report)
        await self._db.flush()

        # Persist Comparables
        from datetime import date
        for comp_dict in result.comparables_used:
            if comp_dict.get("sale_date") and isinstance(comp_dict["sale_date"], str):
                comp_dict["sale_date"] = date.fromisoformat(comp_dict["sale_date"][:10])
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
    async def _fresh_valuation(self, property_id: uuid.UUID, bedrooms: int | None = None, property_type: str | None = None, tenure: str | None = None) -> ValuationReport | None:
        now = datetime.now(timezone.utc)
        filters = [
            ValuationReport.property_id == property_id,
            ValuationReport.status == "complete",
            ValuationReport.expires_at > now,
        ]
        if bedrooms:
            filters.append(ValuationReport.methodology["subject_bedrooms"].astext == str(bedrooms))
        if property_type:
            filters.append(ValuationReport.methodology["subject_type"].astext == property_type)
        stmt = (
            select(ValuationReport)
            .where(*filters)
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
            bedrooms=(epc or {}).get("bedrooms"),
        )
        self._db.add(property_)
        await self._db.flush()
        return property_
