"""Admin routes for user management"""

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.middleware.permissions import require_permission
from app.models.roles import Permission
from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.services.user_service import user_service
from app.utils.common_operations import create_user_common, get_paginated_users
from app.utils.request_utils import get_client_ip

router = APIRouter()
NOT_FOUND_MSG = "User not found"


class RoleEnum(str, Enum):
    """Enumeration for user roles."""

    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    AUTHOR = "author"


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="User password")
    name: str = Field(..., min_length=2, max_length=50, description="User's full name")
    role: RoleEnum = RoleEnum.AUTHOR


class UpdateUserRoleRequest(BaseModel):
    email: EmailStr
    role: RoleEnum


class ResetPasswordRequest(BaseModel):
    identifier: str  # email or username
    new_password: str


@router.get("")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    _user: dict = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """List all users (admin only)"""
    return await get_paginated_users(skip=skip, limit=limit)


@router.post("")
async def create_user_admin(
    request: CreateUserRequest,
    req: Request,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Create user (admin only)"""
    try:
        user = await create_user_common(
            email=request.email,
            password=request.password,
            name=request.name,
            role=request.role,
            admin_user=admin,
            request_obj=req,
            verify_email=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during user creation."
        ) from e

    await audit_logger.log_event(
        event_type="admin_user_created",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={
            "created_user_email": user["email"],
            "created_user_role": user["role"],
        },
    )

    return {
        "message": "User created",
        "email": user["email"],
        "api_key": user["api_key"],
    }


@router.put("/role")
async def update_user_role(
    request: UpdateUserRoleRequest,
    req: Request,
    admin: dict = Depends(require_permission(Permission.MANAGE_ROLES)),
):
    """Update user role (admin only)"""
    db = await mongodb_service.get_database()
    users = db["users"]

    updated_user = await users.find_one_and_update(
        {"email": request.email},
        {"$set": {"role": request.role}},
        return_document=True,
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    await audit_logger.log_event(
        event_type="admin_role_updated",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={
            "target_user": request.email,
            "new_role": request.role,
        },
    )

    updated_user["_id"] = str(updated_user["_id"])
    return updated_user


@router.delete("/{email}")
async def delete_user(
    email: EmailStr,
    req: Request,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Delete user account (admin only)"""
    # user_service.delete_user is expected to be async and return truthy on success
    deleted = await user_service.delete_user(email)
    if not deleted:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    try:
        await audit_logger.log_event(
            event_type="admin_user_deleted",
            user_id=str(admin["_id"]),
            user_email=admin.get("email"),
            ip_address=get_client_ip(req),
            details={"deleted_user": email},
            severity="warning",
        )
    except Exception as e:
        # Log the audit failure but don't fail the request
        audit_logger.log_error(f"Failed to log admin_user_deleted event: {e}")

    return {"message": "User deleted"}


@router.post("/{email}/deactivate")
async def deactivate_user(
    email: EmailStr,
    req: Request,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Deactivate user account (admin only)"""
    db = await mongodb_service.get_database()
    users = db["users"]

    result = await users.update_one({"email": email}, {"$set": {"active": False}})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    await audit_logger.log_event(
        event_type="admin_user_deactivated",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={"deactivated_user": email},
        severity="warning",
    )

    return {"message": "User deactivated"}


@router.post("/{email}/activate")
async def activate_user(
    email: EmailStr,
    req: Request,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Activate user account (admin only)"""
    db = await mongodb_service.get_database()
    users = db["users"]

    result = await users.update_one({"email": email}, {"$set": {"active": True}})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    await audit_logger.log_event(
        event_type="admin_user_activated",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={"activated_user": email},
    )

    return {"message": "User activated"}


@router.post("/reset-password")
async def reset_user_password(
    request: ResetPasswordRequest,
    req: Request,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Reset user password (admin only)"""
    db = await mongodb_service.get_database()
    user = await db.users.find_one(
        {"$or": [{"email": request.identifier}, {"username": request.identifier}]}
    )

    if not user:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    try:
        success = await user_service.update_password(user["email"], request.new_password)

        if not success:
            raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

        await audit_logger.log_event(
            event_type="admin_password_reset",
            user_id=str(admin["_id"]),
            user_email=admin.get("email"),
            ip_address=get_client_ip(req),
            details={"target_user": request.identifier},
            severity="warning",
        )

        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.") from e
