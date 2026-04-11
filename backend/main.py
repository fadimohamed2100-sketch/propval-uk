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
from models.orm import Base
from schemas.schemas import ErrorResponse, HealthResponse

setup_logging()
settings = get_settings()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", version=settings.APP_VERSION)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    except Exception as e:
        logger.warning("db_init_warning", error=str(e))
    yield
    await engine.dispose()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = "; ".join(f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors())
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=ErrorResponse(detail=errors, code="VALIDATION_ERROR").model_dump())

app.include_router(address.router, prefix=settings.API_PREFIX)
app.include_router(property.router, prefix=settings.API_PREFIX)
app.include_router(valuation.router, prefix=settings.API_PREFIX)

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    return HealthResponse(version=settings.APP_VERSION)
