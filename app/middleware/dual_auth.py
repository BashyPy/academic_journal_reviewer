"""Dual authentication: JWT or API Key"""

from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.middleware.auth import auth_service
from app.middleware.jwt_auth import decode_access_token
from app.services.user_service import user_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def _prepare_user(user: dict) -> dict:
    """Ensure user_id is set from _id for consistency."""
    user["user_id"] = str(user.get("_id", ""))
    return user


async def get_current_user(
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> dict:
    """Get current user from either JWT token or API key"""
    # Try JWT token first
    if credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            if payload:
                user = await user_service.get_user_by_email(payload["email"])
                if user and user.get("active", True):
                    return _prepare_user(user)
        except Exception:
            # Invalid token, proceed to check API key
            pass

    # Try API key next
    if api_key:
        # Try new user system
        user = await user_service.get_user_by_api_key(api_key)
        if user:
            return _prepare_user(user)

        # Fallback to old API key system
        user = await auth_service.validate_api_key(api_key)
        if user:
            return user

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_role: str):
    """Dependency factory for role-based access"""

    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{required_role} access required",
            )
        return user

    return role_checker


# Convenience dependencies
require_super_admin = require_role("super_admin")
require_admin = require_role("admin")
require_editor = require_role("editor")
