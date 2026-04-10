"""
schemas/address_schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Request and response models for the address search endpoints.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class AddressSearchRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=300,
                         examples=["Flat 307, Jigger Mast House, Mast Quay, SE18 5NH"])


class AddressSuggestion(BaseModel):
    """Single suggestion returned by GET /address/search."""
    id:            str
    display_line:  str          # e.g. "Flat 307, Jigger Mast House"
    full_address:  str          # e.g. "Flat 307, Jigger Mast House, London, SE18 5NH"
    line_1:        str
    line_2:        str | None
    city:          str
    postcode:      str
    lat:           float | None = None
    lng:           float | None = None
    property_type: str | None  = None
    uprn:          str | None  = None


class AddressSuggestionsResponse(BaseModel):
    """Response from GET /address/search."""
    query:       str
    count:       int
    suggestions: list[AddressSuggestion]
    source:      str = "mock"           # "mock" | "ideal_postcodes" | "getaddress"


# Re-export for convenience — keeps the POST endpoint schema here too
from schemas.schemas import AddressOut, PropertyOut   # noqa: E402


class AddressSearchResponse(BaseModel):
    """Response from POST /address/search (full resolve)."""
    address:  AddressOut
    property: PropertyOut | None = None
    message:  str = "Address resolved successfully."
