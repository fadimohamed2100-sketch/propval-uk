"""
FastAPI dependencies.
All route handlers receive services via Depends() — never instantiate
services directly inside routes.
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.geocoder import GeocoderService
from services.property_data import PropertyDataService
from services.valuation_engine import ValuationEngine
from services.valuation_service import ValuationService


# Singletons — created once at module import time
_geocoder = GeocoderService()
_property_data = PropertyDataService()
_engine = ValuationEngine()


def get_geocoder() -> GeocoderService:
    return _geocoder


def get_property_data() -> PropertyDataService:
    return _property_data


def get_valuation_engine() -> ValuationEngine:
    return _engine


def get_valuation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    geocoder: Annotated[GeocoderService, Depends(get_geocoder)],
    property_data: Annotated[PropertyDataService, Depends(get_property_data)],
    engine: Annotated[ValuationEngine, Depends(get_valuation_engine)],
) -> ValuationService:
    return ValuationService(
        db=db,
        geocoder=geocoder,
        property_data=property_data,
        engine=engine,
    )
