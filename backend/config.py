from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "PropertyValuation API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/propval"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production-use-secrets-manager"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # External APIs
    LAND_REGISTRY_BASE_URL: str = "https://use-land-property-data.service.gov.uk/api/v1"
    EPC_API_BASE_URL: str = "https://epc.opendatacommunities.org/api/v1"
    EPC_API_KEY: str = ""
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
    GEOCODE_USER_AGENT: str = "PropertyValuationMVP/1.0"

    # Valuation
    VALUATION_CACHE_DAYS: int = 30
    COMPARABLE_RADIUS_M: int = 1000
    COMPARABLE_MAX_AGE_YEARS: int = 3
    COMPARABLE_MIN_COUNT: int = 3

    # PDF
    REPORTS_DIR: str = "/tmp/reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
