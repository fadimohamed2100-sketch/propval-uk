"""
Geocoder service.
Wraps Nominatim (free, no key needed).
Swap the _geocode_nominatim method for Google Maps / HERE if needed.
"""
import re
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import get_settings
from core.exceptions import AddressNotFoundError
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _normalise(address: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for dedup key."""
    s = address.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


class GeocoderService:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.NOMINATIM_BASE_URL,
            headers={"User-Agent": settings.GEOCODE_USER_AGENT},
            timeout=10.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _query_nominatim(self, query: str) -> list[dict]:
        resp = await self._client.get(
            "/search",
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 1,
                "countrycodes": "gb",
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def geocode(self, address: str) -> dict:
        """
        Returns:
            {
                "line_1": str, "line_2": str | None, "city": str,
                "county": str | None, "postcode": str,
                "lat": float, "lng": float, "address_norm": str
            }
        Raises:
            AddressNotFoundError if Nominatim returns no results, even
            after falling back to a postcode-only lookup.
        """
        logger.info("geocoding_address", address=address)
        results = await self._query_nominatim(address)

        if not results:
            # The full address (often including a flat/building name Nominatim
            # doesn't index) may not resolve. Fall back to just the postcode —
            # this still gives us a usable lat/lng and locality for the area,
            # and the original address string is preserved as line_1 below.
            postcode_match = re.search(
                r"[A-Za-z]{1,2}[0-9][0-9A-Za-z]?\s*[0-9][A-Za-z]{2}", address
            )
            if postcode_match:
                logger.info(
                    "geocoding_fallback_to_postcode",
                    address=address,
                    postcode=postcode_match.group(0),
                )
                results = await self._query_nominatim(postcode_match.group(0))

        if not results:
            raise AddressNotFoundError(address)

        hit = results[0]
        addr = hit.get("address", {})

        line_1 = " ".join(
            filter(None, [addr.get("house_number"), addr.get("road")])
        ) or address.split(",")[0].strip()

        postcode = addr.get("postcode", "").upper().strip()
        if not postcode:
            raise AddressNotFoundError(address)

        return {
            "line_1": line_1,
            "line_2": addr.get("suburb") or addr.get("neighbourhood"),
            "city": addr.get("city") or addr.get("town") or addr.get("village") or "",
            "county": addr.get("county"),
            "postcode": postcode,
            "lat": float(hit["lat"]),
            "lng": float(hit["lon"]),
            "address_norm": _normalise(address),
        }

    async def close(self) -> None:
        await self._client.aclose()
