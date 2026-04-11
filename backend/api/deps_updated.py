"""
FastAPI dependency injection.

When MOCK_EXTERNAL_APIS=true (set in .env), the mock property data
service is used instead of making real Land Registry / EPC API calls.
This lets you develop and demo the full app with only the seeded database.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from db.session import get_db
from services.geocoder import GeocoderService
from services.valuation_engine import ValuationEngine
from services.valuation_service import ValuationService

settings = get_settings()

# ── Singletons ───────────────────────────────────────────────────
_geocoder = GeocoderService()
_engine   = ValuationEngine()

if settings.MOCK_EXTERNAL_APIS:
    from seeder.mock_property_data import MockPropertyDataService
    _property_data = MockPropertyDataService()
else:
    from services.property_data import PropertyDataService
    _property_data = PropertyDataService()


def get_geocoder() -> GeocoderService:
    return _geocoder


def get_property_data():
    return _property_data


def get_valuation_engine() -> ValuationEngine:
    return _engine


def get_valuation_service(
    db:            Annotated[AsyncSession,     Depends(get_db)],
    geocoder:      Annotated[GeocoderService,  Depends(get_geocoder)],
    property_data: Annotated[object,           Depends(get_property_data)],
    engine:        Annotated[ValuationEngine,  Depends(get_valuation_engine)],
) -> ValuationService:
    return ValuationService(
        db=db,
        geocoder=geocoder,
        property_data=property_data,
        engine=engine,
    )
