"""Permission checking middleware"""

from fastapi import Depends, HTTPException, status

from app.middleware.auth import get_api_key
from app.models.roles import Permission, has_permission

AUTH_REQUIRED_DETAIL = "Authentication required"


def check_permission(user: dict, permission: str) -> bool:
    """Check if user has permission"""
    if not user or not isinstance(user, dict):
        return False
    user_role = user.get("role", "author")
    return has_permission(user_role, permission)


def require_permission(permission: Permission):
    """Dependency factory for requiring a specific permission."""

    def check_permission(user: dict = Depends(get_api_key)):
        if not user or not isinstance(user, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AUTH_REQUIRED_DETAIL,
            )
        user_role = user.get("role", "author")
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return user

    return check_permission


def require_any_permission(permissions: list[Permission]):
    """Dependency factory for requiring any of a list of permissions."""

    def check_permissions(user: dict = Depends(get_api_key)):
        if not user or not isinstance(user, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AUTH_REQUIRED_DETAIL,
            )
        user_role = user.get("role", "author")
        if not any(has_permission(user_role, perm) for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return check_permissions


def require_role(roles: list[str]):
    """Dependency factory for requiring a specific role."""

    def check_role(user: dict = Depends(get_api_key)):
        if not user or not isinstance(user, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AUTH_REQUIRED_DETAIL,
            )
        user_role = user.get("role", "author")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {', '.join(roles)}",
            )
        return user

    return check_role


def has_role(user: dict, role: str) -> bool:
    """Check if user has role"""
    if not user or not isinstance(user, dict):
        return False
    return user.get("role") == role
