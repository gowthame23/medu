from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.errors import MendAppException, ErrorEnvelope, ErrorDetail
from app.core.database import async_engine
from app.models.base import Base
from app.api.v1.api import api_router
from app.repositories.expense import ExpenseRepository
from app.core.database import AsyncSessionLocal


from app.jobs.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables exist and seed system defaults
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        repo = ExpenseRepository(session)
        await repo.seed_system_categories()

    # Start APScheduler jobs
    start_scheduler()

    yield
    # Shutdown
    shutdown_scheduler()
    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="The Anxiety-Free Household & Family Financial Platform API",
    version="1.0.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Health checks
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/ready", tags=["Health"])
async def readiness_check():
    return {"status": "ready"}


# Exception Handlers enforcing uniform Error Envelope
@app.exception_handler(MendAppException)
async def mend_app_exception_handler(request: Request, exc: MendAppException):
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(),
        headers=exc.headers
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "ERROR")
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=str(exc.detail)
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump()
    )


from fastapi.encoders import jsonable_encoder


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid request payload or parameters",
            details=jsonable_encoder(exc.errors())
        )
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope.model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # In production, never leak stack trace or internal message
    message = str(exc) if settings.DEBUG else "An unexpected error occurred. Please try again later."
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message=message
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope.model_dump()
    )
