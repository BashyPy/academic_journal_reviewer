import time
from collections import defaultdict, deque
from typing import Dict

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self):
        # Track requests per IP: {ip: deque of timestamps}
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        # Track processing submissions per IP: {ip: set of submission_ids}
        self.processing: Dict[str, set] = defaultdict(set)

    def check_upload_limit(self, client_ip: str, is_cached: bool = False) -> None:
        """Tiered rate limiting: 5 per hour, 15 per day (relaxed for cached)"""
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400

        # Clean old requests
        while self.requests[client_ip] and self.requests[client_ip][0] < day_ago:
            self.requests[client_ip].popleft()

        # Count recent requests
        hour_count = sum(1 for t in self.requests[client_ip] if t >= hour_ago)
        day_count = len(self.requests[client_ip])

        # Relaxed limits for cached results
        if is_cached:
            if hour_count >= 20:  # 4x higher for cached
                raise HTTPException(
                    status_code=429,
                    detail="Cached result limit exceeded. Maximum 20 per hour.",
                )
            if day_count >= 50:  # Higher daily limit for cached
                raise HTTPException(
                    status_code=429,
                    detail="Daily cached limit exceeded. Maximum 50 per day.",
                )
        else:
            if hour_count >= 5:
                raise HTTPException(
                    status_code=429,
                    detail="Hourly limit exceeded. Maximum 5 submissions per hour.",
                )
            if day_count >= 15:
                raise HTTPException(
                    status_code=429,
                    detail="Daily limit exceeded. Maximum 15 submissions per day.",
                )

        self.requests[client_ip].append(now)

    def check_concurrent_processing(self, client_ip: str, submission_id: str) -> None:
        """Allow max 2 concurrent processing per IP"""
        if len(self.processing[client_ip]) >= 2:
            raise HTTPException(
                status_code=429,
                detail="Too many concurrent reviews. Please wait for current reviews to complete.",
            )
        self.processing[client_ip].add(submission_id)

    def release_processing(self, client_ip: str, submission_id: str) -> None:
        """Release processing slot when review completes"""
        self.processing[client_ip].discard(submission_id)


rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting based on endpoint"""
    request.client.host
    path = request.url.path

    # Skip rate limiting for static files and health checks
    if path.startswith(("/static", "/health", "/docs", "/redoc")):
        return await call_next(request)

    # For uploads, we'll check cache status in the route handler
    # No pre-emptive rate limiting here

    response = await call_next(request)
    return response
