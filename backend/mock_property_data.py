"""
mock_property_data.py
~~~~~~~~~~~~~~~~~~~~~
A drop-in replacement for services/property_data.py that returns seed
data instead of hitting Land Registry and EPC external APIs.

Activate by setting MOCK_EXTERNAL_APIS=true in .env.
The real PropertyDataService is used in production.
"""
from __future__ import annotations

from datetime import date, timedelta

from seeder.uk_property_data import COMPARABLE_SALES, PROPERTIES
from core.logging import get_logger

log = get_logger(__name__)


class MockPropertyDataService:
    """
    Returns seed data for any postcode.

    Falls back to the SE18 dataset if the postcode is not in the seed set.
    """

    async def get_recent_sales(
        self,
        postcode: str,
        max_age_years: int = 3,
        limit: int = 50,
    ) -> list[dict]:
        """Return seed comparable sales, optionally filtered by postcode prefix."""
        cutoff = date.today() - timedelta(days=365 * max_age_years)
        prefix = postcode.strip().upper()[:4]

        # Try exact postcode sector match, then prefix, then everything
        matches = [
            c for c in COMPARABLE_SALES
            if c["postcode"].upper().startswith(prefix)
            and c["date"] >= cutoff
        ]
        if not matches:
            # Prefix fallback (first two chars of postcode)
            fallback_prefix = prefix[:2]
            matches = [
                c for c in COMPARABLE_SALES
                if c["postcode"].upper().startswith(fallback_prefix)
                and c["date"] >= cutoff
            ]
        if not matches:
            # Return all seed comps rather than nothing
            matches = [c for c in COMPARABLE_SALES if c["date"] >= cutoff]

        log.info("mock_sales_fetched", postcode=postcode, count=len(matches[:limit]))

        return [
            {
                "address":          c["address"],
                "postcode":         c["postcode"],
                "price_pence":      c["price_pence"],
                "transaction_date": c["date"],
                "transaction_type": "standard",
                "source":           c.get("source", "land_registry"),
                "source_ref":       f"mock_{i}_{c['postcode'].replace(' ','')}",
            }
            for i, c in enumerate(matches[:limit])
        ]

    async def get_epc_data(self, postcode: str) -> dict | None:
        """Return EPC data from seed properties matching the postcode."""
        prefix = postcode.strip().upper()[:4]
        for record in PROPERTIES:
            if record["address"]["postcode"].upper().startswith(prefix):
                prop = record["property"]
                return {
                    "floor_area_m2": prop.get("floor_area_m2"),
                    "epc_rating":    prop.get("epc_rating"),
                    "property_type": prop.get("property_type"),
                    "inspection_date": "2023-09-01",
                }
        return None

    async def close(self) -> None:
        pass  # No connections to close
