import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from api.deps import get_valuation_service
from schemas.schemas import PropertyDetailOut
from services.valuation_service import ValuationService

router = APIRouter(prefix="/property", tags=["Property"])


@router.get(
    "/{property_id}",
    response_model=PropertyDetailOut,
    summary="Retrieve a property record by ID",
)
async def get_property(
    property_id: uuid.UUID,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
) -> PropertyDetailOut:
    """
    Returns the full property record including its nested address.
    404 if the property ID does not exist.
    """
    property_ = await svc.get_property(property_id)
    return PropertyDetailOut.model_validate(property_)
