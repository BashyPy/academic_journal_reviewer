import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin_routes import router as admin_router
from app.api.admin_user_routes import router as admin_user_router
from app.api.auth_routes import router as auth_router
from app.api.cache_routes import router as cache_router
from app.api.roles_routes import router as roles_router
from app.api.routes import router
from app.middleware.rate_limiter import rate_limit_middleware
from app.middleware.waf import waf_middleware
from app.services.security_monitor import security_monitor
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

# Rate limiting storage
rate_limit_storage = defaultdict(list)


# Apply security middleware in order: WAF -> Rate Limiting
app.middleware("http")(waf_middleware)
app.middleware("http")(rate_limit_middleware)


# Security middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # Check if IP is blocked
    if security_monitor.is_blocked(client_ip):
        logger.warning(f"Blocked IP attempted access: {client_ip}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Access denied"},
        )

    # Rate limiting
    now = datetime.now()
    rate_limit_window = timedelta(minutes=15)
    max_requests = 100  # 100 requests per 15 minutes

    # Clean old entries
    rate_limit_storage[client_ip] = [
        timestamp
        for timestamp in rate_limit_storage[client_ip]
        if now - timestamp < rate_limit_window
    ]

    # Check rate limit
    if len(rate_limit_storage[client_ip]) >= max_requests:
        logger.warning(
            f"Rate limit exceeded for IP: {client_ip}",
            additional_info={
                "ip": client_ip,
                "requests": len(rate_limit_storage[client_ip]),
            },
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": "900"},  # 15 minutes
        )

    # Add current request to rate limit storage
    rate_limit_storage[client_ip].append(now)

    # Input validation for common attack patterns
    user_agent = request.headers.get("user-agent", "")
    if any(
        pattern in user_agent.lower()
        for pattern in ["<script", "javascript:", "vbscript:"]
    ):
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
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:"
        )
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

app.include_router(router, prefix="/api/v1")
app.include_router(cache_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(admin_user_router, prefix="/api/v1")


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
    return {"status": "healthy"}


@app.get("/disclaimer")
async def get_disclaimer():
    try:
        from app.services.disclaimer_service import disclaimer_service

        return {
            "system_disclaimer": disclaimer_service.get_system_disclaimer(),
            **disclaimer_service.get_api_disclaimer(),
        }
    except Exception as e:
        logger.error(e, additional_info={"endpoint": "disclaimer"})
        return {
            "system_disclaimer": "Human oversight required for all AI-generated reviews.",
            "disclaimer": "This system provides preliminary AI analysis only.",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
