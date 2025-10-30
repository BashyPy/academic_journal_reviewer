import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger()

app = FastAPI(
    title="Academic Journal Reviewer (AARIS)",
    description="Agentic AI system for academic journal review",
    version="0.1.0",
)


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log incoming request
    logger.log_api_request(
        endpoint=str(request.url.path),
        method=request.method,
        status_code=0,  # Will be updated after response
        additional_info={
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        },
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log response
        logger.log_api_request(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            additional_info={
                "process_time": f"{process_time:.4f}s",
                "client_ip": request.client.host if request.client else "unknown",
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
            },
        )
        raise


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


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
    from app.services.disclaimer_service import disclaimer_service

    return {
        "system_disclaimer": disclaimer_service.get_system_disclaimer(),
        **disclaimer_service.get_api_disclaimer(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
