"""
Property Valuation API — FastAPI entry point.

Run locally:
    uvicorn main:app --reload --port 8000

Docs:
    http://localhost:8000/docs
    http://localhost:8000/redoc
"""
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1 import address, property, valuation
from core.config import get_settings
from core.logging import setup_logging
from db.session import engine
from models.orm import Base  # noqa: F401 — registers all models with metadata
from schemas.schemas import ErrorResponse, HealthResponse

setup_logging()
settings = get_settings()
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", version=settings.APP_VERSION)
    # In production use Alembic migrations instead of create_all
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("app_shutting_down")
    await engine.dispose()


# ---------------------------------------------------------------
# App instance
# ---------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------
# CORS
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------
# Request ID + latency logging middleware
# ---------------------------------------------------------------
@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    response.headers["X-Request-Id"] = request_id
    return response

# ---------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = "; ".join(
        f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(detail=errors, code="VALIDATION_ERROR").model_dump(),
    )

# ---------------------------------------------------------------
# Routes
# ---------------------------------------------------------------
app.include_router(address.router, prefix=settings.API_PREFIX)
app.include_router(property.router, prefix=settings.API_PREFIX)
app.include_router(valuation.router, prefix=settings.API_PREFIX)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Service health check",
)
async def health():
    return HealthResponse(version=settings.APP_VERSION)
