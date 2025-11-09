"""Authentication and Authorization middleware"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthService:
    def __init__(self):
        self.collection = None

    async def initialize(self):
        """Initialize auth collection"""
        if self.collection is None:
            try:
                db = await mongodb_service.get_database()
                self.collection = db["api_keys"]
                await self.collection.create_index("key", unique=True)
                await self.collection.create_index("expires_at")
            except Exception as e:
                logger.error(f"Failed to initialize auth collection: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize authentication service",
                )

    async def create_api_key(self, name: str, role: str = "user", expires_days: int = 365) -> dict:
        """Generate new API key"""
        await self.initialize()
        try:
            key = f"aaris_{secrets.token_urlsafe(32)}"
            expires_at = datetime.now() + timedelta(days=expires_days)

            doc = {
                "key": key,
                "name": name,
                "role": role,
                "created_at": datetime.now(),
                "expires_at": expires_at,
                "active": True,
                "usage_count": 0,
            }
            await self.collection.insert_one(doc)
            logger.info(f"API key created: {name}")
            return {"api_key": key, "expires_at": expires_at}
        except Exception as e:
            logger.error(f"Failed to create API key for {name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API key"
            )

    async def validate_api_key(self, api_key: str) -> Optional[dict]:
        """Validate API key and return user info"""
        await self.initialize()
        doc = await self.collection.find_one({"key": api_key, "active": True})

        if not doc:
            return None

        if doc["expires_at"] < datetime.now():
            logger.warning(f"Expired API key used: {doc['name']}")
            return None

        await self.collection.update_one({"_id": doc["_id"]}, {"$inc": {"usage_count": 1}})
        return doc

    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key"""
        await self.initialize()
        if self.collection is None:
            logger.error("Auth service collection not initialized.")
            return False
        result = await self.collection.update_one({"key": api_key}, {"$set": {"active": False}})
        if result.modified_count > 0:
            logger.info(f"API key associated with key starting with {api_key[:8]} revoked.")
            return True
        logger.warning(
            f"Attempted to revoke non-existent or already inactive API key starting with {api_key[:8]}."
        )
        return False


auth_service = AuthService()


async def get_api_key(api_key: str = Security(api_key_header)) -> dict:
    """Dependency for API key authentication"""
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")

    # Try new user system first
    from app.services.user_service import user_service

    user = await user_service.get_user_by_api_key(api_key)
    if user:
        # Remove sensitive fields before returning
        user.pop("password", None)
        return user

    # Fallback to old API key system
    user = await auth_service.validate_api_key(api_key)
    if not user:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )

    return user


def require_admin(user: dict = Security(get_api_key)) -> dict:
    """Require admin role"""
    try:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )
        if not isinstance(user, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user data"
            )
        if user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )
        return user
    except HTTPException as e:
        logger.error(f"Authorization error in require_admin: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in require_admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
