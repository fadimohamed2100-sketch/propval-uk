from typing import Annotated
from fastapi import APIRouter, Depends
from api.deps import get_valuation_service
from schemas.schemas import AddressSearchRequest, AddressSearchResponse, AddressOut, PropertyOut
from services.valuation_service import ValuationService
from services.property_data import PropertyDataService

router = APIRouter(prefix="/address", tags=["Address"])


def get_property_data_service() -> PropertyDataService:
    return PropertyDataService()


@router.get(
    "/units",
    summary="List all addressable units (flats/houses) at a postcode, with UPRN",
)
async def list_units(
    postcode: str,
    pd: Annotated[PropertyDataService, Depends(get_property_data_service)],
) -> dict:
    """
    Returns every address registered at a postcode (via Homedata), so the
    frontend can present a dropdown for the user to pick their specific flat.
    """
    addresses = await pd.get_homedata_addresses_by_postcode(postcode)
    return {"postcode": postcode, "count": len(addresses), "addresses": addresses}


@router.post(
    "/search",
    response_model=AddressSearchResponse,
    summary="Geocode an address and look up any existing property record",
)
async def search_address(
    body: AddressSearchRequest,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
) -> AddressSearchResponse:
    """
    Resolves a free-text UK address via Nominatim, normalises it,
    upserts an Address row, and returns any linked Property if one
    already exists.

    Use this endpoint first to confirm the address before calling
    `POST /valuation/run`.
    """
    address, property_ = await svc.resolve_address(body.address)

    return AddressSearchResponse(
        address=AddressOut.model_validate(address),
        property=PropertyOut.model_validate(property_) if property_ else None,
    )
