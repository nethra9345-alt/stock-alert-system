import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.api.v1.api import api_router
# Import all models to ensure they are registered with Base.metadata
import backend.app.models

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("stockpulse.api")

# Initialize database tables on load
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("StockPulse AI engine starting up... Initializing PostgreSQL tables.")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("StockPulse AI engine shutting down cleanly.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="StockPulse AI - Production Security, Reliability & Deployment Engine (Stage 10)",
    docs_url="/docs" if (not settings.is_production or settings.ENABLE_DOCS_IN_PRODUCTION) else None,
    openapi_url="/openapi.json" if (not settings.is_production or settings.ENABLE_DOCS_IN_PRODUCTION) else None,
    lifespan=lifespan
)


# --- Security & Reliability Middlewares ---

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects standard OWASP defensive headers into every HTTP response."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        if is_https and settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response


class RequestLoggingAndAuditMiddleware(BaseHTTPMiddleware):
    """
    Logs structured telemetry for each request, generates traceable request IDs,
    and enforces maximum payload size limits to mitigate DoS attacks.
    """
    async def dispatch(self, request: Request, call_next):
        # 1. Enforce payload size limit
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": f"Request body exceeds maximum size of {settings.MAX_REQUEST_SIZE_BYTES // (1024*1024)}MB"}
            )

        # 2. Assign unique Request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        try:
            response: Response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id

            # Avoid logging sensitive endpoints passwords/payloads
            path = request.url.path
            logger.info(
                f"req_id={request_id} method={request.method} path={path} "
                f"status={response.status_code} duration_ms={duration_ms}ms"
            )
            return response
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"req_id={request_id} method={request.method} path={request.url.path} "
                f"ERROR={str(exc)} duration_ms={duration_ms}ms"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal server error occurred. Please contact support with the request ID.",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )


# Add custom middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingAndAuditMiddleware)

# CORS Middleware (strict origin control with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-CSRF-Token",
        "X-User-Id",
        "Accept",
        "Origin"
    ],
    expose_headers=["X-Request-ID", "X-CSRF-Token"]
)

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
        "environment": settings.ENVIRONMENT
    }
