"""Role management routes"""

from fastapi import APIRouter, Depends, HTTPException

from app.middleware.permissions import require_permission
from app.models.roles import (
    Permission,
    UserRole,
    get_available_roles,
    get_role_description,
    get_role_permissions,
)

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("")
async def list_roles():
    """List all available roles"""
    roles = []
    for role in UserRole:
        roles.append(
            {
                "role": role.value,
                "description": get_role_description(role.value),
                "permissions": [p.value for p in get_role_permissions(role.value)],
            }
        )
    return {"roles": roles}


@router.get("/{role}")
async def get_role_info(role: str):
    """Get information about a specific role"""
    if role not in get_available_roles():
        raise HTTPException(status_code=404, detail="Role not found")

    return {
        "role": role,
        "description": get_role_description(role),
        "permissions": [p.value for p in get_role_permissions(role)],
    }


@router.get("/permissions/list")
async def list_permissions(user: dict = Depends(require_permission(Permission.VIEW_STATISTICS))):
    """List all available permissions"""
    return {
        "permissions": [
            {"name": p.value, "description": p.name.replace("_", " ").title()} for p in Permission
        ]
    }
