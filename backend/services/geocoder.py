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


def _normalise_postcode(raw: str) -> str:
    """
    Canonical UK postcode form: uppercase, exactly one space before the
    final three characters. "ha89dh" / "HA8  9DH" -> "HA8 9DH".
    """
    s = re.sub(r"\s+", "", (raw or "")).upper()
    if len(s) < 5:
        return s
    return f"{s[:-3]} {s[-3:]}"


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

        expected_postcode_match = re.search(
            r"[A-Za-z]{1,2}[0-9][0-9A-Za-z]?\s*[0-9][A-Za-z]{2}", address
        )
        expected_postcode = (
            _normalise_postcode(expected_postcode_match.group(0))
            if expected_postcode_match else None
        )
        expected_outcode = expected_postcode.split()[0] if expected_postcode else None

        def _result_postcode(hit: dict) -> str | None:
            pc = (hit.get("address", {}) or {}).get("postcode", "")
            return _normalise_postcode(pc) if pc else None

        def _result_outcode(hit: dict) -> str | None:
            pc = _result_postcode(hit)
            return pc.split()[0] if pc else None

        # Nominatim frequently returns a NEIGHBOURING postcode on the same
        # street (e.g. HA8 9DH -> HA8 9DJ). The outcode matches, so this
        # slips past an outcode-only check - but every downstream lookup
        # (comparables, Land Registry, EPC) then queries the wrong
        # postcode and returns another property's data. Retry anchored to
        # the postcode to pull coordinates for the right one.
        if (
            results and expected_postcode
            and _result_postcode(results[0]) is not None
            and _result_postcode(results[0]) != expected_postcode
            and _result_outcode(results[0]) == expected_outcode
        ):
            logger.info(
                "geocoding_unit_postcode_mismatch",
                address=address, expected=expected_postcode,
                got=_result_postcode(results[0]),
            )
            retry = await self._query_nominatim(expected_postcode)
            if retry:
                results = retry

        if results and expected_outcode and _result_outcode(results[0]) != expected_outcode:
            # Nominatim matched the free-text query (often the street name)
            # to a result in a completely different postcode area than the
            # one specified - e.g. a same-named street in another city. This
            # would silently value the wrong property with no indication
            # anything went wrong, so we don't trust it: retry anchored
            # strictly to the postcode instead, which we're far more
            # confident is correct (usually picked from a dropdown).
            logger.warning(
                "geocoding_postcode_mismatch",
                address=address,
                expected_outcode=expected_outcode,
                got_postcode=(results[0].get("address", {}) or {}).get("postcode"),
            )
            results = await self._query_nominatim(expected_postcode_match.group(0))
            if results and _result_outcode(results[0]) != expected_outcode:
                # Even an isolated, postcode-only query didn't resolve to the
                # right area - a genuine Nominatim coverage gap for this
                # postcode, not just a free-text mismatch. Don't silently
                # proceed with a location we know is wrong.
                logger.warning(
                    "geocoding_postcode_unresolvable",
                    address=address,
                    expected_outcode=expected_outcode,
                    got_postcode=(results[0].get("address", {}) or {}).get("postcode"),
                )
                raise AddressNotFoundError(address)

        if not results:
            # The full address (often including a flat/building name Nominatim
            # doesn't index) may not resolve. Fall back to just the postcode —
            # this still gives us a usable lat/lng and locality for the area,
            # and the original address string is preserved as line_1 below.
            if expected_postcode_match:
                logger.info(
                    "geocoding_fallback_to_postcode",
                    address=address,
                    postcode=expected_postcode_match.group(0),
                )
                results = await self._query_nominatim(expected_postcode_match.group(0))

        if not results:
            raise AddressNotFoundError(address)

        hit = results[0]
        addr = hit.get("address", {})

        line_1 = " ".join(
            filter(None, [addr.get("house_number"), addr.get("road")])
        ) or address.split(",")[0].strip()

        # The postcode the user supplied (typically chosen from the
        # address dropdown, so authoritative) always wins over Nominatim's
        # best guess. Nominatim is used for coordinates and locality only.
        # This is what keeps comparables, Land Registry and EPC lookups
        # pinned to the property actually being valued.
        resolved = _normalise_postcode(addr.get("postcode", "").strip())
        postcode = expected_postcode or resolved
        if not postcode:
            raise AddressNotFoundError(address)
        if expected_postcode and resolved and resolved != expected_postcode:
            logger.info(
                "geocoding_postcode_overridden",
                used=expected_postcode, nominatim_returned=resolved,
            )

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
