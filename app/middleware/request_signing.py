"""Request signing for API security"""

import hashlib
import hmac
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestSigner:
    """Request signature verification"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()

    def generate_signature(self, method: str, path: str, timestamp: str, body: str = "") -> str:
        """Generate request signature"""
        message = f"{method}|{path}|{timestamp}|{body}"
        signature = hmac.new(self.secret_key, message.encode(), hashlib.sha256).hexdigest()
        return signature

    def verify_signature(
        self, method: str, path: str, timestamp: str, signature: str, body: str = ""
    ) -> bool:
        """Verify request signature"""
        expected = self.generate_signature(method, path, timestamp, body)
        return hmac.compare_digest(expected, signature)

    def verify_timestamp(self, timestamp: str, max_age: int = 300) -> bool:
        """Verify timestamp is within acceptable range (default 5 minutes)"""
        try:
            ts = int(timestamp)
            now = int(time.time())
            return abs(now - ts) <= max_age
        except (ValueError, TypeError):
            return False


async def verify_request_signature(request: Request, signer: Optional[RequestSigner] = None):
    """Middleware to verify request signatures"""
    if not signer:
        return  # Skip if signing not configured

    # Get signature headers
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")

    if not signature or not timestamp:
        logger.warning("Missing signature headers")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature headers",
        )

    # Verify timestamp
    if not signer.verify_timestamp(timestamp):
        logger.warning("Invalid or expired timestamp")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired timestamp",
        )

    # Get body
    body = ""
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body_bytes = await request.body()
            body = body_bytes.decode("utf-8")
        except Exception:
            pass

    # Verify signature
    if not signer.verify_signature(
        request.method, str(request.url.path), timestamp, signature, body
    ):
        logger.warning("Invalid request signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request signature",
        )
