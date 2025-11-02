"""Permission checking middleware"""
from fastapi import Depends, HTTPException, status

from app.middleware.auth import get_api_key
from app.models.roles import Permission, has_permission


def require_permission(permission: Permission):
    """Dependency to require specific permission"""
    async def check_permission(user: dict = Depends(get_api_key)):
        user_role = user.get("role", "author")
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
        return user
    return check_permission


def require_any_permission(*permissions: Permission):
    """Dependency to require any of the specified permissions"""
    async def check_permissions(user: dict = Depends(get_api_key)):
        user_role = user.get("role", "author")
        if not any(has_permission(user_role, perm) for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return check_permissions


def require_role(*roles: str):
    """Dependency to require specific role(s)"""
    async def check_role(user: dict = Depends(get_api_key)):
        user_role = user.get("role", "author")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {', '.join(roles)}"
            )
        return user
    return check_role
