"""
Property data service.

Fetches:
  - Recent sales from HM Land Registry Price Paid open data API
  - EPC data (floor area, rating) from the OpenDataCommunities EPC API

Both are free to use with no API key for basic access (EPC requires
a registered email; supply EPC_API_KEY in .env as "email:apikey").
"""
import httpx
import re
from datetime import date, timedelta
from core.config import get_settings
from core.exceptions import ExternalAPIError
from core.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

settings = get_settings()
logger = get_logger(__name__)


class PropertyDataService:
    def __init__(self) -> None:
        self._lr_client = httpx.AsyncClient(
            base_url=settings.LAND_REGISTRY_BASE_URL,
            timeout=15.0,
        )
        self._epc_client = httpx.AsyncClient(
            base_url=settings.EPC_API_BASE_URL,
            http2=False,
            headers={
                "Authorization": "Basic " + __import__("base64").b64encode(f"{settings.EPC_API_EMAIL}:{settings.EPC_API_KEY}".encode()).decode(),
                "Accept": "application/json",
            },
            timeout=15.0,
        )

    # ------------------------------------------------------------------
    # LAND REGISTRY — recent sales in a postcode
    # ------------------------------------------------------------------
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4), reraise=True)
    async def get_recent_sales(
        self,
        postcode: str,
        max_age_years: int = 3,
        limit: int = 50,
    ) -> list[dict]:
        """
        Returns a list of recent sale dicts for a postcode:
            {address, postcode, price_pence, transaction_date,
             transaction_type, source, source_ref}
        """
        cutoff = (date.today() - timedelta(days=365 * max_age_years)).isoformat()
        try:
            resp = await self._lr_client.get(
                "/transactions/england-and-wales/property-transactions",
                params={
                    "postcode": postcode.replace(" ", "").upper(),
                    "limit": limit,
                    "from-date": cutoff,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("land_registry_error", status=exc.response.status_code)
            return []

        rows = resp.json().get("results", [])
        logger.info("land_registry_sales_fetched", postcode=postcode, count=len(rows))

        return [
            {
                "address": f"{r.get('paon', '')} {r.get('street', '')}".strip(),
                "postcode": r.get("postcode", postcode),
                "price_pence": int(float(r.get("amount", 0)) * 100),
                "transaction_date": r.get("transaction-date"),
                "transaction_type": r.get("record-type", "standard").lower(),
                "source": "land_registry",
                "source_ref": r.get("transaction-unique-identifier"),
            }
            for r in rows
            if r.get("amount")
        ]

    # ------------------------------------------------------------------
    # EPC — energy certificate for an address
    # ------------------------------------------------------------------
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4), reraise=True)
    async def get_epc_data(self, postcode: str, line_1: str | None = None) -> dict | None:
        """
        Returns the EPC record for a postcode, matched against line_1 (street/building
        number) where possible, falling back to most recent if no match found.
            {floor_area_m2, epc_rating, property_type, inspection_date}
        """
        try:
            resp = await self._epc_client.get(
                "/domestic/search",
                params={"postcode": postcode, "size": 50},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("epc_api_error", status=exc.response.status_code)
            return None  # EPC is best-effort; don't block the valuation
        try:
            rows = resp.json().get("rows", [])
        except Exception:
            rows = []
        if not rows:
            return None
        row = rows[0]
        if line_1:
            import re as _re
            num_match = _re.search(r"\d+", line_1)
            target_num = num_match.group() if num_match else None
            target_words = set(_re.findall(r"[a-zA-Z]+", line_1.lower())) - {"road", "street", "avenue", "lane", "close", "drive", "way", "court"}
            best = None
            best_score = -1
            if target_num:
                for r in rows:
                    addr = (r.get("address") or "").lower()
                    if not _re.search(r"\b" + target_num + r"\b", addr):
                        continue
                    addr_words = set(_re.findall(r"[a-zA-Z]+", addr)) - {"road", "street", "avenue", "lane", "close", "drive", "way", "court"}
                    score = len(target_words & addr_words)
                    if score > best_score:
                        best_score = score
                        best = r
                if best is not None:
                    row = best
        return {
            "floor_area_m2": float(row.get("total-floor-area", 0) or 0) or None,
            "epc_rating": (row.get("current-energy-rating") or "")[:1].upper() or None,
            "property_type": row.get("property-type", "").lower().replace(" ", "_"),
            "inspection_date": row.get("inspection-date"),
            # NOTE: EPC's "number-habitable-rooms" is bedrooms + receptions + studies
            # combined, NOT a bedroom count. Kept separate (not aliased to
            # "bedrooms") so callers can derive receptions = habitable_rooms - bedrooms
            # using whatever bedroom count is confirmed from elsewhere, rather than
            # silently treating total habitable rooms as if it were the bedroom count.
            "habitable_rooms": int(row.get("number-habitable-rooms", 0) or 0) or None,
            "construction_age_band": row.get("construction-age-band") or None,
        }


    async def get_propertydata_valuation(self, postcode: str, property_type: str, bedrooms: int | None, floor_area_m2: float | None, bathrooms: int | None = None, condition: str | None = None, parking: str | None = None, outdoor_space: str | None = None) -> dict | None:
        """Call PropertyData /valuation-sale endpoint."""
        if not settings.PROPERTYDATA_API_KEY:
            return None
        try:
            params = {
                "key": settings.PROPERTYDATA_API_KEY,
                "postcode": postcode,
                "internal_area": str(int(floor_area_m2)) if floor_area_m2 else None,
                "property_type": property_type,
                "bedrooms": str(bedrooms) if bedrooms else None,
                "bathrooms": str(bathrooms) if bathrooms else None,
                "finish_quality": condition or "average",
                "outdoor_space": outdoor_space or "none",
                "parking": parking or "none",
                "construction_date": "2000",
            }
            params = {k: v for k, v in params.items() if v is not None}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get("https://api.propertydata.co.uk/valuation-sale", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        return data
        except Exception as e:
            logger.warning("propertydata_error", error=str(e))
        return None

    async def get_propertydata_sold_prices(self, postcode: str, property_type: str, bedrooms: int | None = None, tenure: str | None = None) -> list[dict]:
        """Call PropertyData /sold-prices endpoint."""
        if not settings.PROPERTYDATA_API_KEY:
            return []
        try:
            params = {
                "key": settings.PROPERTYDATA_API_KEY,
                "postcode": postcode,
                "max_age": 48,
                "points": 100,
            }
            if bedrooms:
                params["bedrooms"] = bedrooms
            if tenure:
                params["tenure"] = tenure
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get("https://api.propertydata.co.uk/sold-prices", params=params)
                logger.info("propertydata_sold_prices_response", status=resp.status_code, body=resp.text[:200])
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        raw = data.get("data", {}).get("raw_data", [])
                        pd_average = data.get("data", {}).get("average", 0)
                        # Remove new builds
                        no_new_builds = [t for t in raw if t.get("class") != "new_build"]
                        if not no_new_builds:
                            no_new_builds = raw
                        # Apply date filter: within 0.3 miles keep 4 years, beyond keep 18 months
                        from datetime import date, timedelta
                        cutoff_near = date.today() - timedelta(days=365 * 4)
                        cutoff_far = date.today() - timedelta(days=548)
                        def keep_by_date(t):
                            d = t.get("distance", 999)
                            try:
                                dist = float(str(d))
                            except:
                                dist = 999
                            sale_date_str = t.get("date", "")
                            try:
                                sale_date = date.fromisoformat(sale_date_str[:10])
                            except:
                                return True
                            if dist <= 0.3:
                                return sale_date >= cutoff_near
                            else:
                                return sale_date >= cutoff_far
                        no_new_builds = [t for t in no_new_builds if keep_by_date(t)]
                        if not no_new_builds:
                            no_new_builds = raw
                        # Filter by property type if known
                        if property_type and property_type not in ["other", "unknown", ""]:
                            type_map = {"flat": "flat", "terraced": "terraced_house", "semi-detached": "semi-detached_house", "detached": "detached_house"}
                            pd_type = type_map.get(property_type, "")
                            type_filtered = [t for t in no_new_builds if pd_type in t.get("type", "")]
                            if type_filtered:
                                no_new_builds = type_filtered
                        if pd_average:
                            low = pd_average * 0.65
                            high = pd_average * 1.4
                            filtered = [t for t in no_new_builds if t.get("price") and low <= float(str(t.get("price", 0))) <= high]
                            if not filtered:
                                filtered = no_new_builds
                        else:
                            filtered = no_new_builds
                        return [
                            {
                                "address": t.get("address", ""),
                                "postcode": __import__("re").search(r"[A-Z]{1,2}[0-9][0-9A-Z]?\s[0-9][A-Z]{2}", t.get("address", "").upper()) and __import__("re").search(r"[A-Z]{1,2}[0-9][0-9A-Z]?\s[0-9][A-Z]{2}", t.get("address", "").upper()).group() or postcode,
                                "price_pence": int(float(str(t.get("price", 0)))) * 100,
                                "transaction_date": t.get("date", ""),
                                "source": "propertydata",
                                "distance_m": int(float(str(t.get("distance", 0))) * 1609),
                                "property_type": t.get("type", "").replace("_house", "").replace("_", "-"),
                                "source_url": t.get("url", ""),
                            }
                            for t in filtered if t.get("price")
                        ]
        except Exception as e:
            logger.warning("propertydata_sold_prices_error", error=str(e))
        return []

    async def get_propertydata_rent(self, postcode: str, bedrooms: int | None) -> dict | None:
        """Call PropertyData /valuation-rent endpoint."""
        if not settings.PROPERTYDATA_API_KEY:
            return None
        try:
            params = {
                "key": settings.PROPERTYDATA_API_KEY,
                "postcode": postcode,
                "bedrooms": str(bedrooms) if bedrooms else None,
            }
            params = {k: v for k, v in params.items() if v is not None}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get("https://api.propertydata.co.uk/rents", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        return data
        except Exception as e:
            logger.warning("propertydata_rent_error", error=str(e))
        return None

    # ------------------------------------------------------------------
    # Homedata — address lookup (UPRN) and enriched property retrieval
    # ------------------------------------------------------------------
    async def get_homedata_addresses_by_postcode(self, postcode: str) -> list[dict]:
        """List all addresses (with UPRN) at a postcode via Homedata."""
        if not settings.HOMEDATA_API_KEY:
            return []
        try:
            clean_postcode = postcode.replace(" ", "")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"https://api.homedata.co.uk/api/address/postcode/{clean_postcode}/",
                    headers={"Authorization": f"Api-Key {settings.HOMEDATA_API_KEY}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("addresses", [])
                else:
                    logger.warning("homedata_postcode_non_200", status=resp.status_code, body=resp.text[:300])
        except Exception as e:
            logger.warning("homedata_postcode_error", error=str(e))
        return []
    @staticmethod
    def _sap_score_to_epc_band(score) -> str | None:
        """Convert a numeric SAP energy efficiency score (0-100) to an EPC letter band."""
        try:
            score = float(score)
        except (TypeError, ValueError):
            return None
        if score >= 92:
            return "A"
        if score >= 81:
            return "B"
        if score >= 69:
            return "C"
        if score >= 55:
            return "D"
        if score >= 39:
            return "E"
        if score >= 21:
            return "F"
        return "G"
    async def get_homedata_property(self, uprn: str | int) -> dict | None:
        """
        Retrieve enriched property record (EPC, floor area, bedrooms, last sold)
        for an exact UPRN via Homedata's /property/{uprn}/base endpoint.
        """
        if not settings.HOMEDATA_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"https://api.homedata.co.uk/property/{uprn}/base",
                    headers={"Authorization": f"Api-Key {settings.HOMEDATA_API_KEY}"},
                )
                if resp.status_code != 200:
                    logger.warning("homedata_non_200", status=resp.status_code, body=resp.text[:300], uprn=str(uprn))
                    return None
                data = resp.json()
        except Exception as e:
            logger.warning("homedata_retrieve_error", error=str(e))
            return None
        epc_section = data.get("epc") if isinstance(data.get("epc"), dict) else {}
        rooms_section = data.get("rooms") if isinstance(data.get("rooms"), dict) else {}
        last_sold_section = data.get("last_sold") if isinstance(data.get("last_sold"), dict) else {}

        floor_area = data.get("epc_floor_area") or data.get("predicted_floor_area") or epc_section.get("epc_floor_area")
        epc_eff = data.get("current_energy_efficiency") or epc_section.get("current_energy_efficiency")
        epc_rating = self._sap_score_to_epc_band(epc_eff)
        bedrooms = data.get("bedrooms") or data.get("predicted_bedrooms") or rooms_section.get("bedrooms") or rooms_section.get("predicted_bedrooms")
        bathrooms = data.get("bathrooms") if not isinstance(data.get("bathrooms"), dict) else None
        if bathrooms is None:
            bathrooms = rooms_section.get("bathrooms")

        raw_property_type = data.get("property_type")
        if isinstance(raw_property_type, dict):
            raw_property_type = raw_property_type.get("property_type")
        property_type = (raw_property_type or "").lower().replace(" ", "_").replace("-", "_") or None

        last_sold_price = data.get("last_sold_price_gbp")
        if last_sold_price is None:
            last_sold_price = last_sold_section.get("last_sold_price_gbp")
        last_sold_date = data.get("last_sold_date")
        if last_sold_date is None:
            last_sold_date = last_sold_section.get("last_sold_date")

        return {
            "epc_floor_area": floor_area,
            "epc_rating": epc_rating,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "property_type": property_type,
            "last_sold_price": last_sold_price,
            "last_sold_date": last_sold_date,
        }
    async def get_propertydata_demand(self, postcode: str) -> dict | None:
        """
        Call PropertyData's /demand endpoint for local buyer-demand analytics.
        Returns {"demand_rating": "Seller's market" | "Balanced market" | "Buyer's market", ...}
        or None if unavailable. Best-effort — never blocks the valuation.
        """
        if not settings.PROPERTYDATA_API_KEY:
            return None
        try:
            params = {"key": settings.PROPERTYDATA_API_KEY, "postcode": postcode}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get("https://api.propertydata.co.uk/demand", params=params)
                if resp.status_code == 200:
                    body = resp.json()
                    if body.get("status") == "success":
                        return body.get("data", {})
                    logger.warning("propertydata_demand_unsuccessful", body=resp.text[:200])
                else:
                    logger.warning("propertydata_demand_non_200", status=resp.status_code)
        except Exception as e:
            logger.warning("propertydata_demand_error", error=str(e))
        return None

    async def get_homedata_agent_stats(self, uprn: str | int) -> dict | None:
        """
        Call Homedata's /api/agent_stats/{uprn}/ endpoint to get area-level
        estate agent performance — used here for average days-on-market and
        average % of asking price achieved, blended across nearby agents.

        Note: Homedata's docs warn the first call for a new UPRN can take up
        to ~20s (full aggregation, uncached); subsequent calls are cached
        and fast. Best-effort — never blocks the valuation.
        """
        if not settings.HOMEDATA_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(
                    f"https://api.homedata.co.uk/api/agent_stats/{uprn}/",
                    headers={"Authorization": f"Api-Key {settings.HOMEDATA_API_KEY}"},
                )
                if resp.status_code != 200:
                    logger.warning("homedata_agent_stats_non_200", status=resp.status_code, uprn=str(uprn))
                    return None
                payload = resp.json()
        except Exception as e:
            logger.warning("homedata_agent_stats_error", error=str(e))
            return None

        agents = payload if isinstance(payload, list) else (payload.get("results") or [])
        if not agents:
            return None

        weighted_dom_sum = 0.0
        weight_sum = 0.0
        sale_pct_values: list[float] = []
        for agent in agents:
            stats = agent.get("stats", agent) or {}
            weight = stats.get("listing_count") or stats.get("sales_count") or 1
            dom = stats.get("avg_time_on_market")
            if dom is not None:
                weighted_dom_sum += dom * weight
                weight_sum += weight
            pct = stats.get("avg_sale_percent")
            if pct is not None:
                sale_pct_values.append(pct)

        avg_dom_days = round(weighted_dom_sum / weight_sum) if weight_sum else None
        avg_sale_pct = round(sum(sale_pct_values) / len(sale_pct_values), 1) if sale_pct_values else None

        if avg_dom_days is None and avg_sale_pct is None:
            return None
        return {"avg_time_on_market_days": avg_dom_days, "avg_sale_percent": avg_sale_pct}

    async def get_land_registry_own_sale(self, postcode: str, line_1: str) -> dict | None:
        """
        Direct lookup of THIS property'''s own sale history from HM Land
        Registry'''s official Price Paid Data - every residential sale in
        England & Wales since 1995, free, no API key. Unlike PropertyData'''s
        sold-prices wrapper (capped at ~4 years) or Homedata (can return a
        date with a null price), this always has price+date together for
        every real transaction, with no recency limit.

        England & Wales only - Scotland and Northern Ireland have separate
        registries not covered by this dataset.

        Returns the most recent matching transaction as
        {"price_pence": int, "date": "YYYY-MM-DD"}, or None if no match
        or any error - best-effort, never blocks the valuation.
        """
        if not postcode or not line_1:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://landregistry.data.gov.uk/data/ppi/transaction-record.json",
                    params={"propertyAddress.postcode": postcode, "_pageSize": 100, "_view": "basic"},
                    headers={"Accept": "application/json"},
                )
                if resp.status_code != 200:
                    return None
                body = resp.json()
        except Exception as e:
            logger.warning("land_registry_fetch_error", postcode=postcode, error=str(e))
            return None

        items = (body.get("result") or {}).get("items") or body.get("items") or []
        logger.info("land_registry_lookup", postcode=postcode, line_1=line_1, items_returned=len(items))
        if not items:
            return None
        if not any(isinstance(it, dict) and isinstance(it.get("propertyAddress"), dict) for it in items):
            logger.warning("land_registry_unexpected_shape", sample=str(items[0])[:500])

        num_match = re.search(r"\d+", line_1)
        target_num = num_match.group() if num_match else None
        if not target_num:
            return None
        target_words = set(re.findall(r"[a-zA-Z]+", line_1.lower())) - {"flat", "road", "street", "avenue", "lane", "close", "drive", "way", "court"}

        matches = []
        for it in items:
            if not isinstance(it, dict):
                continue
            addr = it.get("propertyAddress")
            if not isinstance(addr, dict):
                addr = {
                    "paon": it.get("propertyAddress.paon"),
                    "saon": it.get("propertyAddress.saon"),
                    "street": it.get("propertyAddress.street"),
                }
            addr_text = " ".join(str(v) for v in (addr.get("paon"), addr.get("saon"), addr.get("street")) if v).lower()
            if not addr_text:
                continue
            if not re.search(r"" + re.escape(target_num) + r"", addr_text):
                continue
            addr_words = set(re.findall(r"[a-zA-Z]+", addr_text)) - {"flat", "road", "street", "avenue", "lane", "close", "drive", "way", "court"}
            if target_words and not (target_words & addr_words):
                continue
            price = it.get("pricePaid")
            date_val = it.get("transactionDate")
            if price and date_val:
                matches.append((str(date_val), int(price)))

        if not matches:
            logger.info("land_registry_no_match", postcode=postcode, line_1=line_1)
            return None
        matches.sort(key=lambda m: m[0], reverse=True)
        latest_date, latest_price = matches[0]
        logger.info("land_registry_match_found", postcode=postcode, date=latest_date, price=latest_price)
        return {"price_pence": latest_price * 100, "date": latest_date[:10]}

    async def close(self) -> None:
        await self._lr_client.aclose()
        await self._epc_client.aclose()
