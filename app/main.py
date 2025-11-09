import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin_dashboard_routes import router as admin_dashboard_router
from app.api.admin_user_routes import router as admin_user_router
from app.api.auth_routes import router as auth_router
from app.api.author_dashboard_routes import router as author_dashboard_router
from app.api.cache_routes import router as cache_router
from app.api.download_routes import router as download_router
from app.api.editor_dashboard_routes import router as editor_dashboard_router
from app.api.reviewer_dashboard_routes import router as reviewer_dashboard_router
from app.api.roles_routes import router as roles_router
from app.api.routes import router
from app.api.super_admin_routes import router as super_admin_router
from app.services.disclaimer_service import disclaimer_service
from app.services.init_admin import create_default_admin
from app.services.otp_cleanup_service import otp_cleanup_service
from app.services.security_monitor import security_monitor
from app.services.vector_store_validator import vector_store_validator
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger()

app = FastAPI(
    title="Academic Journal Reviewer (AARIS)",
    description="Agentic AI system for academic journal review",
    version="0.1.0",
    docs_url="/docs",  # Explicit docs URL
    redoc_url="/redoc",  # Explicit redoc URL
)


class RateLimiter:
    """A simple in-memory rate limiter."""

    def __init__(self, max_requests: int, window_minutes: int):
        self.storage = defaultdict(list)
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)

    def is_rate_limited(self, client_ip: str) -> bool:
        """Check if a client is rate-limited."""
        now = datetime.now()
        # Clean old entries
        self.storage[client_ip] = [
            timestamp for timestamp in self.storage[client_ip] if now - timestamp < self.window
        ]
        # Check rate limit
        return len(self.storage[client_ip]) >= self.max_requests

    def record_request(self, client_ip: str):
        """Record a new request from a client."""
        self.storage[client_ip].append(datetime.now())


# Rate limiting instance
rate_limiter = RateLimiter(max_requests=100, window_minutes=15)


@app.on_event("startup")
async def startup_event():
    """Initialize default admin and start background tasks on startup"""
    try:
        logger.info("Starting admin initialization...")
        admin = await create_default_admin()
        if admin:
            logger.info("✅ Admin setup complete")
        else:
            logger.warning("⚠️ Admin setup failed or incomplete")
    except Exception as e:
        logger.error(f"❌ Admin initialization error: {e}")

    # Validate vector store for RAG functionality
    try:
        logger.info("Validating vector store...")
        vector_status = await vector_store_validator.validate_vector_store()
        if vector_status.get("available"):
            logger.info("✅ Vector store validated - RAG enabled")
        else:
            logger.warning(
                f"⚠️ Vector store not available: {vector_status.get('error')} - "
                "RAG features disabled"
            )
    except Exception as e:
        logger.error(f"❌ Vector store validation error: {e}")

    # Start background tasks
    try:
        logger.info("Starting background tasks...")
        _ = asyncio.create_task(otp_cleanup_background_task())
        _ = asyncio.create_task(embedding_cache_cleanup_task())
        logger.info("✅ Background tasks started")
    except Exception as e:
        logger.error(f"❌ Failed to start background tasks: {e}")


async def otp_cleanup_background_task():
    """Background task to clean up expired OTPs every hour"""
    while True:
        try:
            await otp_cleanup_service.cleanup_expired_otps()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(e, additional_info={"task": "otp_cleanup"})

        # Wait 1 hour before next cleanup
        await asyncio.sleep(3600)


async def embedding_cache_cleanup_task():
    """Background task to clean up expired embedding caches"""
    while True:
        try:
            from app.services.embedding_cache_service import embedding_cache_service

            await embedding_cache_service.cleanup_expired()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(e, additional_info={"task": "embedding_cache_cleanup"})

        # Wait 1 day before next cleanup
        await asyncio.sleep(86400)


@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
    """Middleware for security, rate limiting, and logging."""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # Security Monitor
    if security_monitor.is_blocked(client_ip):
        logger.warning(
            f"Blocked IP tried to connect: {client_ip}",
            additional_info={"ip": client_ip},
        )
        return JSONResponse(
            status_code=403,
            content={"detail": "Access denied"},
        )

    # Rate limiting
    if rate_limiter.is_rate_limited(client_ip):
        logger.warning(
            f"Rate limit exceeded for IP: {client_ip}",
            additional_info={
                "ip": client_ip,
                "requests": len(rate_limiter.storage.get(client_ip, [])),
            },
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": "900"},  # 15 minutes
        )

    # Record current request
    rate_limiter.record_request(client_ip)

    # Input validation for common attack patterns
    user_agent = request.headers.get("user-agent", "")
    if any(pattern in user_agent.lower() for pattern in ["<script", "javascript:", "vbscript:"]):
        logger.warning(f"Suspicious user agent detected: {user_agent}")
        return JSONResponse(status_code=400, content={"detail": "Invalid request"})

    # Log incoming request
    logger.log_api_request(
        endpoint=str(request.url.path),
        method=request.method,
        status_code=0,
        additional_info={
            "client_ip": client_ip,
            "user_agent": user_agent[:100],  # Limit logged user agent length
        },
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Content Security Policy
        csp = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        csp += "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:"
        response.headers["Content-Security-Policy"] = csp
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Log response
        logger.log_api_request(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            additional_info={
                "process_time": f"{process_time:.4f}s",
                "client_ip": client_ip,
            },
        )

        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            e,
            additional_info={
                "endpoint": str(request.url.path),
                "method": request.method,
                "process_time": f"{process_time:.4f}s",
                "client_ip": client_ip,
            },
        )
        raise


# Secure CORS configuration
allowed_origins = [
    "http://localhost:3000",  # Development frontend
    "https://yourdomain.com",  # Production frontend - UPDATE THIS
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Restricted methods
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "X-Timezone",
        "Authorization",
    ],  # Specific headers only
    max_age=600,  # Cache preflight for 10 minutes
)

# Define API prefix constant to avoid duplicated literals
API_V1_PREFIX = "/api/v1"

app.include_router(router, prefix=API_V1_PREFIX)
app.include_router(cache_router)
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(roles_router, prefix=API_V1_PREFIX)

app.include_router(admin_dashboard_router, prefix=API_V1_PREFIX)
app.include_router(admin_user_router, prefix=API_V1_PREFIX)
app.include_router(author_dashboard_router, prefix=API_V1_PREFIX)
app.include_router(editor_dashboard_router, prefix=API_V1_PREFIX)
app.include_router(reviewer_dashboard_router, prefix=API_V1_PREFIX)
app.include_router(super_admin_router, prefix=API_V1_PREFIX)
app.include_router(download_router, prefix=API_V1_PREFIX)


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "Academic Journal Reviewer (AARIS) API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check with vector store status."""
    vector_status = await vector_store_validator.validate_vector_store()
    return {
        "status": "healthy",
        "rag_enabled": vector_status.get("rag_enabled", False),
        "vector_store": vector_status,
    }


@app.get("/disclaimer")
async def get_disclaimer():
    try:
        return {
            "system_disclaimer": disclaimer_service.get_system_disclaimer(),
            **disclaimer_service.get_api_disclaimer(),
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(e, additional_info={"endpoint": "disclaimer"})
        return {
            "system_disclaimer": "Human oversight required for all AI-generated reviews.",
            "disclaimer": "This system provides preliminary AI analysis only.",
        }


@app.get("/api/v1/system/rag-metrics")
async def get_rag_metrics():
    """Get RAG effectiveness metrics."""
    try:
        from app.services.langchain_service import langchain_service

        metrics = langchain_service.get_rag_metrics()
        vector_status = await vector_store_validator.validate_vector_store()

        return {
            "rag_metrics": metrics,
            "vector_store_status": vector_status,
            "status": "operational" if vector_status.get("available") else "degraded",
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(e, additional_info={"endpoint": "rag-metrics"})
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to retrieve RAG metrics.", "status": "error"},
        )


@app.get("/api/v1/system/enhancement-metrics")
async def get_enhancement_metrics():
    """Get enhancement features metrics."""
    try:
        from app.services.mongodb_service import mongodb_service
        from app.services.vector_security_service import vector_security_service

        # Get checkpoint and cache counts concurrently
        checkpoint_count_task = mongodb_service.db["workflow_checkpoints"].count_documents({})
        cache_count_task = mongodb_service.db["embedding_cache"].count_documents({})
        checkpoint_count, cache_count = await asyncio.gather(
            checkpoint_count_task, cache_count_task
        )

        # Get security stats
        security_stats = vector_security_service.get_security_stats()

        return {
            "checkpoints": {
                "active_count": checkpoint_count,
                "enabled": True,
            },
            "embedding_cache": {
                "cached_count": cache_count,
                "ttl_days": 30,
                "enabled": True,
            },
            "vector_security": {
                **security_stats,
                "enabled": True,
            },
            "status": "operational",
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(e, additional_info={"endpoint": "enhancement-metrics"})
        return {"error": str(e), "status": "error"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
