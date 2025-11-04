"""Admin routes for user management"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.middleware.permissions import require_permission
from app.models.roles import Permission
from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.services.user_service import user_service

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

NOT_FOUND_MSG = "User not found"


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "author"


class UpdateUserRoleRequest(BaseModel):
    email: EmailStr
    role: str


class ResetPasswordRequest(BaseModel):
    identifier: str  # email or username
    new_password: str


@router.get("")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_permission(Permission.MANAGE_USERS))
):
    """List all users (admin only)"""
    db = await mongodb_service.get_database()
    users = db["users"]

    cursor = users.find({}, {"password": 0}).skip(skip).limit(limit)
    user_list = await cursor.to_list(length=limit)

    total = await users.count_documents({})

    return {"users": user_list, "total": total, "skip": skip, "limit": limit}


@router.post("")
async def create_user_admin(
    request: CreateUserRequest,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS))
):
    """Create user (admin only)"""
    try:
        user = await user_service.create_user(
            email=request.email,
            password=request.password,
            name=request.name,
            role=request.role,
        )

        await user_service.verify_email(request.email)

        await audit_logger.log_event(
            event_type="admin_user_created",
            user_id=admin.get("email", admin.get("name")),
            details={"created_user": request.email, "role": request.role},
        )

        return {
            "message": "User created",
            "email": user["email"],
            "api_key": user["api_key"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/role")
async def update_user_role(
    request: UpdateUserRoleRequest,
    admin: dict = Depends(require_permission(Permission.MANAGE_ROLES))
):
    """Update user role (admin only)"""
    db = await mongodb_service.get_database()
    users = db["users"]

    result = await users.update_one(
        {"email": request.email}, {"$set": {"role": request.role}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    await audit_logger.log_event(
        event_type="admin_role_updated",
        user_id=admin.get("email", admin.get("name")),
        details={"target_user": request.email, "new_role": request.role},
    )

    return {"message": "Role updated"}


@router.delete("/{email}")
async def delete_user(
    email: str,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS))
):
    """Delete user account (admin only)"""
    # user_service.delete_user is expected to be async and return truthy on success
    deleted = await user_service.delete_user(email)
    if not deleted:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    await audit_logger.log_event(
        event_type="admin_user_deleted",
        user_id=admin.get("email", admin.get("name")),
        details={"deleted_user": email},
        severity="warning",
    )

    return {"message": "User deleted"}


@router.post("/{email}/deactivate")
async def deactivate_user(
    email: str,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS))
):
    """Deactivate user account (admin only)"""
    db = await mongodb_service.get_database()
    users = db["users"]

    result = await users.update_one({"email": email}, {"$set": {"active": False}})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    await audit_logger.log_event(
        event_type="admin_user_deactivated",
        user_id=admin.get("email", admin.get("name")),
        details={"deactivated_user": email},
        severity="warning",
    )

    return {"message": "User deactivated"}


@router.post("/{email}/activate")
async def activate_user(
    email: str,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS))
):
    """Activate user account (admin only)"""
    db = await mongodb_service.get_database()
    users = db["users"]

    result = await users.update_one({"email": email}, {"$set": {"active": True}})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)

    await audit_logger.log_event(
        event_type="admin_user_activated",
        user_id=admin.get("email", admin.get("name")),
        details={"activated_user": email},
    )

    return {"message": "User activated"}


@router.post("/reset-password")
async def reset_user_password(
    request: ResetPasswordRequest,
    admin: dict = Depends(require_permission(Permission.MANAGE_USERS))
):
    """Reset user password (admin only)"""
    db = await mongodb_service.get_database()
    user = await db.users.find_one({"$or": [{"email": request.identifier}, {"username": request.identifier}]})
    
    if not user:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)
    
    try:
        success = await user_service.update_password(user["email"], request.new_password)
        
        if not success:
            raise HTTPException(status_code=404, detail=NOT_FOUND_MSG)
        
        await audit_logger.log_event(
            event_type="admin_password_reset",
            user_id=admin.get("email", admin.get("name")),
            details={"target_user": request.identifier},
            severity="warning",
        )
        
        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
