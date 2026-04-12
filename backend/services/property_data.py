"""
Property data service.

Fetches:
  - Recent sales from HM Land Registry Price Paid open data API
  - EPC data (floor area, rating) from the OpenDataCommunities EPC API

Both are free to use with no API key for basic access (EPC requires
a registered email; supply EPC_API_KEY in .env as "email:apikey").
"""
import httpx
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
            headers={
                "Authorization": f"Basic {settings.EPC_API_KEY}",
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
    async def get_epc_data(self, postcode: str) -> dict | None:
        """
        Returns the most recent EPC record for a postcode, or None.
            {floor_area_m2, epc_rating, property_type, inspection_date}
        """
        try:
            resp = await self._epc_client.get(
                "/domestic/search",
                params={"postcode": postcode, "size": 1},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("epc_api_error", status=exc.response.status_code)
            return None  # EPC is best-effort; don't block the valuation

        rows = resp.json().get("rows", [])
        if not rows:
            return None

        row = rows[0]
        return {
            "floor_area_m2": float(row.get("total-floor-area", 0) or 0) or None,
            "epc_rating": (row.get("current-energy-rating") or "")[:1].upper() or None,
            "property_type": row.get("property-type", "").lower().replace(" ", "_"),
            "inspection_date": row.get("inspection-date"),
        }

    async def close(self) -> None:
        await self._lr_client.aclose()
        await self._epc_client.aclose()
