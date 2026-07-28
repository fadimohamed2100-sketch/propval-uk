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

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import ValuationFailedError, ValuationNotFoundError
from core.logging import get_logger
from models.orm import Address, Comparable, Property, ValuationReport
from pathlib import Path

from services.geocoder import GeocoderService
from services.pdf_playwright import PlaywrightPDFService
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
        receptions: int | None = None,
        condition: str | None = None,
        parking: str | None = None,
        outdoor_space: str | None = None,
        property_type: str | None = None,
        tenure: str | None = None,
        lease_years: int | None = None,
        unit_identifier: str | None = None,
        uprn: str | None = None,
    ) -> ValuationReport:
        address, property_ = await self.resolve_address(raw_address)
        # Enrich property: prefer Homedata UPRN lookup (exact match) if available,
        # otherwise fall back to EPC postcode + address-line matching.
        # Homedata results are cached permanently on the Property row (keyed by UPRN)
        # to avoid burning API quota on repeat valuations of the same unit.
        epc = None
        last_sold_price = None
        last_sold_date = None
        cached_external_ids = (property_.external_ids if property_ else {}) or {}
        cached_homedata = cached_external_ids.get("homedata") if uprn and cached_external_ids.get("uprn") == uprn else None
        fresh_homedata_for_create = None
        if uprn and cached_homedata:
            hd = cached_homedata
            epc = {
                "floor_area_m2": hd.get("epc_floor_area") or hd.get("floor_area_sqm"),
                "epc_rating": hd.get("epc_rating") or hd.get("current_energy_rating"),
                "property_type": (hd.get("property_type") or "").lower().replace(" ", "_") or None,
                "bedrooms": hd.get("bedrooms"),
                "bathrooms": hd.get("bathrooms"),
            }
            last_sold_price = hd.get("last_sold_price") or hd.get("price")
            last_sold_date = hd.get("last_sold_date") or hd.get("sold_date")
        elif uprn:
            hd = await self._property_data.get_homedata_property(uprn)
            if hd:
                epc = {
                    "floor_area_m2": hd.get("epc_floor_area") or hd.get("floor_area_sqm"),
                    "epc_rating": hd.get("epc_rating") or hd.get("current_energy_rating"),
                    "property_type": (hd.get("property_type") or "").lower().replace(" ", "_") or None,
                    "bedrooms": hd.get("bedrooms"),
                    "bathrooms": hd.get("bathrooms"),
                }
                last_sold_price = hd.get("last_sold_price") or hd.get("price")
                last_sold_date = hd.get("last_sold_date") or hd.get("sold_date")
                fresh_homedata_for_create = {"uprn": uprn, "homedata": hd}
                if property_:
                    property_.external_ids = {**cached_external_ids, "uprn": uprn, "homedata": hd}
        epc_is_register_source = False
        if not epc:
            epc_match_line = f"{unit_identifier} {address.line_1}" if unit_identifier else address.line_1
            epc = await self._property_data.get_epc_data(address.postcode, line_1=epc_match_line)
            epc_is_register_source = True

        # Override EPC data with user-provided values if available
        if bedrooms and epc:
            epc["bedrooms"] = bedrooms
        if bathrooms and epc:
            epc["bathrooms"] = bathrooms
        if property_type:
            if epc:
                epc["property_type"] = property_type.replace("-", "_") if property_type else property_type
            if property_:
                property_.property_type = property_type.replace("-", "_") if property_type else property_type
        if not property_:
            property_ = await self._create_property(address, epc, external_ids=fresh_homedata_for_create)
        if property_:
            if bedrooms:
                property_.bedrooms = bedrooms
            elif epc and not property_.bedrooms:
                property_.bedrooms = epc.get("bedrooms")
            if bathrooms:
                property_.bathrooms = bathrooms
            elif epc and not property_.bathrooms:
                property_.bathrooms = epc.get("bathrooms")
            if epc and epc.get("floor_area_m2"):
                property_.floor_area_m2 = epc.get("floor_area_m2")
            if epc and epc.get("epc_rating"):
                property_.epc_rating = epc.get("epc_rating")

        # Return cached valuation unless force_refresh
        effective_bedrooms = bedrooms or property_.bedrooms
        if not force_refresh:
            cached = await self._fresh_valuation(
                property_.id,
                bedrooms=effective_bedrooms,
                property_type=property_.property_type,
                bathrooms=bathrooms or property_.bathrooms,
                receptions=receptions,
                condition=condition,
                parking=parking,
                outdoor_space=outdoor_space,
                tenure=tenure,
                lease_years=lease_years,
            )
            if cached:
                logger.info("valuation_cache_hit", property_id=str(property_.id))
                return cached

        # Fetch comparables — PropertyData first, then seeded DB
        pd_type_map = {"flat": "flat", "terraced": "terraced", "semi_detached": "semi-detached", "detached": "detached", "other": "terraced"}
        pd_property_type = pd_type_map.get(property_.property_type or "other", "terraced")
        raw_sales = await self._property_data.get_propertydata_sold_prices(address.postcode, pd_property_type, bedrooms=effective_bedrooms, tenure=tenure)
        used_propertydata_sales = bool(raw_sales)
        if not raw_sales:
            from sqlalchemy import text
            # Restrict the seed-data fallback to the subject's postcode AREA
            # (the outcode, e.g. "DH2" from "DH2 3LT") so a thin/empty real
            # dataset never silently falls back to unrelated sales from
            # wherever the seed data happens to be concentrated.
            outcode = address.postcode.split()[0] if address.postcode else ""
            result = await self._db.execute(
                text("""
                    SELECT a.address_norm, a.postcode, st.price_pence, st.transaction_date, p.property_type, st.source
                    FROM sales_transactions st
                    JOIN properties p ON st.property_id = p.id
                    JOIN addresses a ON p.address_id = a.id
                    WHERE a.postcode LIKE :outcode_pattern
                    LIMIT 50
                """),
                {"outcode_pattern": f"{outcode}%"},
            )
            raw_sales = [
                {"address": r[0], "postcode": r[1], "price_pence": int(r[2]), "transaction_date": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]), "source": r[5]}
                for r in result.fetchall()
            ]
        # Filter comparables to match the selected property type, if known
        if property_.property_type and property_.property_type != "other":
            type_aliases = {
                "terraced": {"terraced", "terrace"},
                "semi_detached": {"semi-detached", "semi_detached", "semi"},
                "detached": {"detached"},
                "flat": {"flat", "apartment", "maisonette"},
            }
            allowed = type_aliases.get(property_.property_type, {property_.property_type})
            filtered_sales = [s for s in raw_sales if (s.get("property_type") or "").lower().replace(" ", "_") in allowed]
            if filtered_sales:
                raw_sales = filtered_sales

        # Check whether the subject property's own historical sale appears in
        # this same official Land Registry sold-prices dataset. If so, it's a
        # confirmed real price+date for THIS property (more reliable than
        # Homedata, which can return a date with no price) - use it, and
        # exclude it from the comparables list since it's the subject itself,
        # not a comparable to it.
        own_sale_price_pence = None
        own_sale_date_iso = None
        num_match = re.search(r"\d+", address.line_1 or "")
        target_num = num_match.group() if num_match else None
        if target_num:
            target_words = set(re.findall(r"[a-zA-Z]+", address.line_1.lower())) - {"road", "street", "avenue", "lane", "close", "drive", "way", "court"}
            own_sale_idx = None
            for i, s in enumerate(raw_sales):
                sale_addr_lower = (s.get("address") or "").lower()
                if not re.search(r"\b" + re.escape(target_num) + r"\b", sale_addr_lower):
                    continue
                sale_words = set(re.findall(r"[a-zA-Z]+", sale_addr_lower)) - {"road", "street", "avenue", "lane", "close", "drive", "way", "court"}
                if target_words & sale_words:
                    own_sale_price_pence = s.get("price_pence")
                    own_sale_date_iso = s.get("transaction_date")
                    own_sale_idx = i
                    break
            if own_sale_idx is not None:
                raw_sales = raw_sales[:own_sale_idx] + raw_sales[own_sale_idx + 1:]

        # Direct Land Registry Price Paid Data lookup takes priority over the
        # above if it finds a match - comprehensive since 1995, no recency
        # cap, always has price+date together (England & Wales only).
        lr_own_sale = await self._property_data.get_land_registry_own_sale(address.postcode, unit_identifier or address.line_1)
        if lr_own_sale:
            own_sale_price_pence = lr_own_sale["price_pence"]
            own_sale_date_iso = lr_own_sale["date"]

        comp_inputs = [
            ComparableInput(
                address=s["address"],
                postcode=s["postcode"],
                sale_price=s["price_pence"],
                sale_date=__import__("datetime").date.fromisoformat(str(s["transaction_date"])[:10]) if s["transaction_date"] else None,
                property_type=s.get("property_type") or property_.property_type,
                bedrooms=property_.bedrooms,
                floor_area_m2=property_.floor_area_m2,
                source=s["source"],
                distance_m=s.get("distance_m"),
                source_url=s.get("source_url"),
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

        # Apply PropertyData rental estimate if available
        if pd_rent:
            weekly = pd_rent.get("data", {}).get("long_let", {}).get("average", 0)
            if weekly:
                result.rental_monthly = int(weekly * 52 / 12) * 100
                if result.estimated_value > 0:
                    result.rental_yield = round((result.rental_monthly * 12 / result.estimated_value) * 100, 1)

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

        # Inject previous sale info (from Homedata UPRN lookup) into methodology, if available.
        # Price and date are stored independently - Homedata sometimes returns one
        # without the other (e.g. a real sold date with a missing price), and a
        # missing price shouldn't cause a perfectly real date to be discarded too.
        methodology = dict(result.methodology)
        if bathrooms:
            methodology["subject_bathrooms"] = bathrooms
        if condition:
            methodology["subject_condition"] = condition
        if parking:
            methodology["subject_parking"] = parking
        if outdoor_space:
            methodology["subject_outdoor_space"] = outdoor_space
        if tenure:
            methodology["subject_tenure"] = tenure
        if lease_years:
            methodology["subject_lease_years"] = lease_years
        if last_sold_price:
            methodology["previous_sale_price_pence"] = int(float(last_sold_price) * 100) if isinstance(last_sold_price, (int, float)) else last_sold_price
        if last_sold_date:
            methodology["previous_sale_date"] = str(last_sold_date)
        if own_sale_price_pence:
            methodology["previous_sale_price_pence"] = int(own_sale_price_pence)
        if own_sale_date_iso:
            methodology["previous_sale_date"] = str(own_sale_date_iso)
        if unit_identifier:
            methodology["unit_identifier"] = unit_identifier
        # Mirror the EPC rating into methodology: the detail API returns
        # property as null, so the results page reads subject_* fields from
        # here (as it already does for type, bedrooms and floor area).
        if property_.epc_rating:
            methodology["subject_epc_rating"] = property_.epc_rating

        # Construction age band & habitable room count, for "year built" and
        # "receptions" in the report. EPC register data already has these
        # directly if that was our enrichment source; otherwise (Homedata
        # matched via UPRN) make one extra lightweight EPC lookup just for
        # this — Homedata doesn't carry construction age band.
        epc_for_enrichment = epc if epc_is_register_source else None
        if not epc_for_enrichment:
            epc_for_enrichment = await self._property_data.get_epc_data(address.postcode, line_1=address.line_1)
        if epc_for_enrichment:
            if epc_for_enrichment.get("construction_age_band"):
                methodology["construction_age_band"] = epc_for_enrichment["construction_age_band"]
            if epc_for_enrichment.get("habitable_rooms"):
                methodology["habitable_rooms"] = epc_for_enrichment["habitable_rooms"]

        # Best-effort area market signals — fetched once here, cached in
        # methodology so the PDF never needs to re-fetch on every download.
        demand = await self._property_data.get_propertydata_demand(address.postcode)
        if demand and demand.get("demand_rating"):
            methodology["market_demand_rating"] = demand["demand_rating"]
        if uprn:
            agent_stats = await self._property_data.get_homedata_agent_stats(uprn)
            if agent_stats:
                if agent_stats.get("avg_time_on_market_days") is not None:
                    methodology["avg_time_on_market_days"] = agent_stats["avg_time_on_market_days"]
                if agent_stats.get("avg_sale_percent") is not None:
                    methodology["avg_sale_percent"] = agent_stats["avg_sale_percent"]

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
            methodology=methodology,
            source_apis=(["propertydata"] if used_propertydata_sales else []) + (["epc"] if epc else []) + (["homedata"] if uprn else []),
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
    # GET /valuation/{id}/report  (PDF — generated on demand, then cached)
    # ------------------------------------------------------------------
    async def get_or_generate_report_pdf(self, valuation_id: uuid.UUID, force: bool = False) -> Path:
        """
        Returns the path to this valuation's PDF, generating it on first
        request and reusing the cached file on every subsequent download.

        Pass force=True to bypass the cache and regenerate from current
        data — e.g. after correcting a data issue on an existing report.

        Comparables are ranked by similarity_score (the same composite
        distance/type/bedroom/size/recency score used during valuation)
        so the report shows the strongest matches, not just the first
        six in whatever order they were saved.
        """
        report = await self.get_valuation(valuation_id)

        ranked_comparables = sorted(
            report.comparables or [],
            key=lambda c: c.similarity_score if c.similarity_score is not None else 0,
            reverse=True,
        )[:6]

        pdf_service = PlaywrightPDFService()
        pdf_path = await pdf_service.generate(report, report.property, ranked_comparables, force=force)

        if report.pdf_path != str(pdf_path):
            report.pdf_path = str(pdf_path)
            await self._db.flush()

        return pdf_path

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
    async def _fresh_valuation(
        self,
        property_id: uuid.UUID,
        bedrooms: int | None = None,
        property_type: str | None = None,
        bathrooms: int | None = None,
        receptions: int | None = None,
        condition: str | None = None,
        parking: str | None = None,
        outdoor_space: str | None = None,
        tenure: str | None = None,
        lease_years: int | None = None,
    ) -> ValuationReport | None:
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
        # These don't feed our own scoring engine, but DO get sent to
        # PropertyData's valuation API as adjustment hints - so a different
        # value here can legitimately produce a different estimate, and a
        # cached report from before the change must not be reused.
        if bathrooms:
            filters.append(ValuationReport.methodology["subject_bathrooms"].astext == str(bathrooms))
        if receptions is not None:
            filters.append(ValuationReport.methodology["subject_receptions"].astext == str(receptions))
        if condition:
            filters.append(ValuationReport.methodology["subject_condition"].astext == condition)
        if parking:
            filters.append(ValuationReport.methodology["subject_parking"].astext == parking)
        if outdoor_space:
            filters.append(ValuationReport.methodology["subject_outdoor_space"].astext == outdoor_space)
        if tenure:
            filters.append(ValuationReport.methodology["subject_tenure"].astext == tenure)
        if lease_years:
            filters.append(ValuationReport.methodology["subject_lease_years"].astext == str(lease_years))
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
        self, address: Address, epc: dict | None, external_ids: dict | None = None
    ) -> Property:
        property_ = Property(
            address_id=address.id,
            property_type=(epc or {}).get("property_type") or "other",
            floor_area_m2=(epc or {}).get("floor_area_m2"),
            epc_rating=(epc or {}).get("epc_rating"),
            bedrooms=(epc or {}).get("bedrooms"),
            bathrooms=(epc or {}).get("bathrooms"),
            external_ids=external_ids or {},
        )
        self._db.add(property_)
        await self._db.flush()
        return property_
