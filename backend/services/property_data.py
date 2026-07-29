"""
Property data service.

Fetches:
  - Recent sales from HM Land Registry Price Paid open data API
  - EPC data (floor area, rating) from the OpenDataCommunities EPC API

Both are free to use with no API key for basic access (EPC requires
a registered email; supply EPC_API_KEY in .env as "email:apikey").
"""
import asyncio
import httpx
import re
from datetime import date, timedelta
from core.config import get_settings
from core.exceptions import ExternalAPIError
from core.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

settings = get_settings()
logger = get_logger(__name__)


_LR_GENERIC = {
    "flat", "apartment", "apt", "unit", "road", "street", "avenue", "lane",
    "close", "drive", "way", "court", "house", "the", "london",
}
_LR_NUM_RE = re.compile(r"[0-9]+[a-z]?")
_LR_FLAT_RE = re.compile(r"(?:flat|apartment|apt|unit)[\s.]*([0-9]+[a-z]?)", re.I)
_LR_POSTCODE_RE = re.compile(r"[a-z]{1,2}[0-9][0-9a-z]?\s*[0-9][a-z]{2}", re.I)


def _lr_address_parts(line_1: str) -> tuple[set[str], set[str], str | None]:
    """
    Split a target address into the signals used for Land Registry
    matching: all numbers (with optional letter suffix), meaningful street
    words, and the flat/unit number when one is designated.

    Uses explicit character classes rather than word-boundary escapes -
    those are easy to corrupt when this code passes through escaping
    layers, and a silently broken boundary makes every match fail.
    """
    low = (line_1 or "").lower()
    low = _LR_POSTCODE_RE.sub(" ", low)      # postcode digits would pollute
    nums = set(_LR_NUM_RE.findall(low))
    words = set(re.findall(r"[a-z]+", low)) - _LR_GENERIC
    flat_match = _LR_FLAT_RE.search(line_1 or "")
    return nums, words, flat_match.group(1).lower() if flat_match else None


def _lr_match_score(
    target_nums: set[str], target_words: set[str],
    flat_no: str | None, addr_text: str,
) -> int:
    """
    Score a Land Registry address against the target; 0 rejects it.

    Deliberately conservative - printing the WRONG unit's sale price is
    worse than printing none:
      - at least one number must be shared
      - if the target designates a flat/unit, that number must be present
      - if the target has street words, at least one must be shared
    """
    addr_nums = set(_LR_NUM_RE.findall(addr_text))
    shared_nums = target_nums & addr_nums
    if not shared_nums:
        return 0
    if flat_no and flat_no not in addr_nums:
        return 0
    addr_words = set(re.findall(r"[a-z]+", addr_text)) - _LR_GENERIC
    shared_words = target_words & addr_words
    if target_words and not shared_words:
        return 0
    return len(shared_nums) * 10 + len(shared_words)


class PropertyDataService:
    def __init__(self) -> None:
        self._lr_client = httpx.AsyncClient(
            base_url=settings.LAND_REGISTRY_BASE_URL,
            timeout=15.0,
        )
        epc_auth = (
            f"Bearer {settings.EPC_BEARER_TOKEN}"
            if settings.EPC_BEARER_TOKEN
            else "Basic " + __import__("base64").b64encode(
                f"{settings.EPC_API_EMAIL}:{settings.EPC_API_KEY}".encode()
            ).decode()
        )
        self._epc_client = httpx.AsyncClient(
            base_url=settings.EPC_API_BASE_URL,
            http2=False,
            follow_redirects=True,
            headers={
                "Authorization": epc_auth,
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
    @staticmethod
    def _epc_addr_text(row: dict) -> str:
        """Join an EPC search row's address lines into one lowercase string."""
        parts = [
            row.get("addressLine1"), row.get("addressLine2"),
            row.get("addressLine3"), row.get("addressLine4"),
        ]
        return " ".join(str(p) for p in parts if p).lower()

    @staticmethod
    def _addr_match_score(target_line_1: str, candidate_addr: str) -> int:
        """
        Score how well an EPC address matches a target address.
        Returns -1 for no match (house number absent), else the count of
        overlapping street words. Same technique used for Land Registry.
        """
        target_nums, target_words, flat_no = _lr_address_parts(line_1)
        if not target_nums:
            logger.info("land_registry_no_number", line_1=line_1)
            return None

        scored: list[tuple[int, str, int]] = []
        samples: list[str] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            addr = it.get("propertyAddress")
            if not isinstance(addr, dict):
                # Flat dotted-key shape from _properties expansion.
                addr = {
                    "paon": it.get("propertyAddress.paon"),
                    "saon": it.get("propertyAddress.saon"),
                    "street": it.get("propertyAddress.street"),
                }
            addr_text = " ".join(
                str(v) for v in (addr.get("paon"), addr.get("saon"), addr.get("street")) if v
            ).lower()
            if not addr_text:
                continue
            if len(samples) < 4:
                samples.append(addr_text[:60])
            price = it.get("pricePaid")
            date_val = it.get("transactionDate")
            if not (price and date_val):
                continue
            score = _lr_match_score(target_nums, target_words, flat_no, addr_text)
            if score > 0:
                scored.append((score, str(date_val), int(price)))

        matches = []
        if scored:
            # Best score wins, ties broken by most recent. Scoring rather
            # than first-match matters for flats, where both the unit
            # number and the building number can appear - the record
            # matching BOTH is the correct one.
            scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
            best = scored[0][0]
            matches = [(d, p) for sc, d, p in scored if sc == best]

        if not matches:
            # Log what WAS returned, so a genuine absence (unit never sold
            # since 1995) is distinguishable from a matcher failure.
            logger.info(
                "land_registry_no_match", postcode=postcode, line_1=line_1,
                target_nums=sorted(target_nums), flat_no=flat_no,
                candidates=len(samples), sample_addresses=samples,
            )
            return None
        matches.sort(key=lambda m: m[0], reverse=True)
        latest_date, latest_price = matches[0]
        logger.info("land_registry_match_found", postcode=postcode, date=latest_date, price=latest_price)
        return {"price_pence": latest_price * 100, "date": latest_date[:10]}

    async def close(self) -> None:
        await self._lr_client.aclose()
        await self._epc_client.aclose()
