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
    # Startup validation: Fail fast if sandbox payments or insecure secrets are enabled in production
    if settings.APP_ENV == "production":
        if settings.ENABLE_SANDBOX_PAYMENTS:
            raise RuntimeError("CRITICAL SECURITY ERROR: Cannot start in production with ENABLE_SANDBOX_PAYMENTS=True")
        if "dev-insecure" in settings.WEBHOOK_SECRET or len(settings.WEBHOOK_SECRET) < 32:
            raise RuntimeError("CRITICAL SECURITY ERROR: Production requires a secure WEBHOOK_SECRET of at least 32 characters")
        if "dev-insecure" in settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
            raise RuntimeError("CRITICAL SECURITY ERROR: Production requires a secure SECRET_KEY of at least 32 characters")

    # In development/testing, ensure database tables exist
    if settings.APP_ENV != "production":
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


docs_url = None if settings.APP_ENV == "production" else f"{settings.API_V1_PREFIX}/docs"
redoc_url = None if settings.APP_ENV == "production" else f"{settings.API_V1_PREFIX}/redoc"
openapi_url = None if settings.APP_ENV == "production" else f"{settings.API_V1_PREFIX}/openapi.json"

app = FastAPI(
    title=settings.APP_NAME,
    description="The Anxiety-Free Household & Family Financial Platform API",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    lifespan=lifespan
)

# CSRF / Origin Verification on mutating requests
@app.middleware("http")
async def verify_origin_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Exclude only the exact payment webhook endpoint which originates from payment provider servers
        if request.url.path != f"{settings.API_V1_PREFIX}/payments/webhook":
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            check_header = origin or referer

            # In production, mutating requests MUST have an Origin or Referer header
            if not check_header:
                if settings.APP_ENV == "production":
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"error": {"code": "FORBIDDEN", "message": "Missing Origin header on mutating request."}}
                    )
            else:
                from urllib.parse import urlparse
                parsed = urlparse(check_header)
                origin_base = f"{parsed.scheme}://{parsed.netloc}"
                allowed = set(settings.CORS_ORIGINS)

                # Test/dev exemptions are STRICTLY non-production only
                if settings.APP_ENV != "production":
                    allowed.update({"http://testserver", "http://test", "http://localhost"})

                if origin_base not in allowed:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"error": {"code": "FORBIDDEN", "message": "Cross-origin request rejected."}}
                    )
    return await call_next(request)

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


HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

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
        status_code=HTTP_422,
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
