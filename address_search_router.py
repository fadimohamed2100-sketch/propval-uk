"""
api/v1/address_search.py
~~~~~~~~~~~~~~~~~~~~~~~~
GET  /address/search?q=...        — typeahead suggestions (≥ 2 chars)
POST /address/search              — existing full-address resolve endpoint (unchanged)

The GET endpoint powers the frontend autocomplete.
The POST endpoint is unchanged from the original implementation.

Swap `_mock_search()` for a real provider call (Ideal Postcodes,
GetAddress.io, OS Places) by replacing the body of `_lookup()`.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.deps import get_valuation_service
from schemas.address_schemas import (
    AddressSearchRequest,
    AddressSearchResponse,
    AddressSuggestion,
    AddressSuggestionsResponse,
)
from services.valuation_service import ValuationService

from .address_search_data import MOCK_ADDRESSES

router = APIRouter(prefix="/address", tags=["Address"])


# ─────────────────────────────────────────────────────────────────────
# Search logic
# ─────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace and punctuation."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _postcode_clean(pc: str) -> str:
    """Normalise postcode: uppercase, strip spaces, collapse."""
    return re.sub(r"\s+", "", pc.upper())


def _score(query: str, address: dict) -> float:
    """
    Return a relevance score 0.0–1.0 for an address vs. a search query.

    Scoring priority (highest → lowest):
      1.  Exact postcode match                        → 1.00
      2.  Postcode prefix match (first 4 chars)       → 0.80
      3.  Street line starts with query               → 0.70
      4.  Street line contains all query tokens       → 0.55
      5.  Any field contains the query                → 0.35
      0.  No match                                    → 0.00
    """
    q = _clean(query)
    q_tokens = q.split()

    full_address = _clean(
        " ".join(filter(None, [
            address.get("line_1", ""),
            address.get("line_2", ""),
            address.get("city", ""),
            address.get("postcode", ""),
        ]))
    )
    line1  = _clean(address.get("line_1", ""))
    pc_raw = _postcode_clean(address.get("postcode", ""))
    q_pc   = _postcode_clean(query)

    # Exact postcode
    if q_pc and pc_raw == q_pc:
        return 1.00
    # Postcode prefix
    if q_pc and pc_raw.startswith(q_pc[:4]):
        return 0.80
    # Street starts-with query
    if line1.startswith(q):
        return 0.70
    # All tokens present in full address
    if all(tok in full_address for tok in q_tokens):
        return 0.55
    # Any token in full address (partial)
    if any(tok in full_address for tok in q_tokens if len(tok) >= 2):
        return 0.35
    return 0.0


def _mock_search(query: str, limit: int = 8) -> list[dict]:
    """
    Search MOCK_ADDRESSES and return up to `limit` results ranked by score.

    This function is the only thing that changes when switching to a real API.
    """
    if len(query.strip()) < 2:
        return []

    scored = [
        (addr, _score(query, addr))
        for addr in MOCK_ADDRESSES
    ]
    filtered = [(a, s) for a, s in scored if s > 0]
    filtered.sort(key=lambda x: x[1], reverse=True)
    return [a for a, _ in filtered[:limit]]


def _format_suggestion(addr: dict) -> AddressSuggestion:
    """Convert a raw address dict to the API response model."""
    parts = list(filter(None, [addr.get("line_1"), addr.get("line_2")]))
    display_line = ", ".join(parts)
    full = f"{display_line}, {addr['city']}, {addr['postcode']}"

    return AddressSuggestion(
        id            = addr["id"],
        display_line  = display_line,
        full_address  = full,
        line_1        = addr["line_1"],
        line_2        = addr.get("line_2"),
        city          = addr["city"],
        postcode      = addr["postcode"],
        lat           = addr.get("lat"),
        lng           = addr.get("lng"),
        property_type = addr.get("property_type"),
        uprn          = addr.get("uprn"),
    )


# ─────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=AddressSuggestionsResponse,
    summary="Typeahead address suggestions",
    description=(
        "Returns up to 8 ranked address suggestions for a query string. "
        "Minimum 2 characters. Swap `_mock_search()` for a real provider."
    ),
)
async def get_suggestions(
    q:     str = Query(..., min_length=2, max_length=200, description="Search query"),
    limit: int = Query(default=8, ge=1, le=20, description="Max results"),
) -> AddressSuggestionsResponse:
    results = _mock_search(q, limit=limit)
    suggestions = [_format_suggestion(a) for a in results]
    return AddressSuggestionsResponse(
        query=q,
        count=len(suggestions),
        suggestions=suggestions,
        source="mock",
    )


@router.post(
    "/search",
    response_model=AddressSearchResponse,
    summary="Resolve a full address string",
)
async def search_address(
    body: AddressSearchRequest,
    svc:  Annotated[ValuationService, Depends(get_valuation_service)],
) -> AddressSearchResponse:
    """
    Full address resolve — geocodes, upserts Address row, returns any
    linked Property. Used by the valuation flow after the user picks
    a suggestion from the typeahead.
    """
    from schemas.schemas import AddressOut, PropertyOut
    address, property_ = await svc.resolve_address(body.address)
    return AddressSearchResponse(
        address  = AddressOut.model_validate(address),
        property = PropertyOut.model_validate(property_) if property_ else None,
    )
