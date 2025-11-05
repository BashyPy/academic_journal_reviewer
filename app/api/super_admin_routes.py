"""Super Admin Dashboard API Routes"""

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.middleware.dual_auth import get_current_user
from app.models.roles import UserRole
from app.services.audit_logger import audit_logger
from app.services.cache_service import cache_service
from app.services.mongodb_service import mongodb_service
from app.services.security_monitor import security_monitor
from app.services.user_service import user_service
from app.utils.common_operations import (
    create_user_common,
    get_domain_analytics,
    get_paginated_audit_logs,
    get_paginated_submissions,
    get_paginated_users,
    get_performance_metrics,
    get_submission_analytics,
    reprocess_submission_common,
    update_user_status_common,
)
from app.utils.logger import get_logger
from app.utils.request_utils import get_client_ip

router = APIRouter(prefix="/super-admin", tags=["super-admin"])
logger = get_logger(__name__)

USER_NOT_FOUND = "User not found"
PROCESSING_TIME = "$processing_time"
MONGO_SORT = "$sort"
MONGO_GROUP = "$group"
MONGO_MATCH = "$match"


def require_super_admin(user: dict = Depends(get_current_user)):
    """Require super admin role"""
    if user.get("role") != UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


class SystemStats(BaseModel):
    total_users: int
    total_submissions: int
    active_reviews: int
    completed_reviews: int
    failed_reviews: int
    total_audit_logs: int


@router.get("/dashboard/stats")
async def get_dashboard_stats(_admin: dict = Depends(require_super_admin)):
    """Get comprehensive system statistics"""
    db = await mongodb_service.get_database()

    stats = {
        "total_users": await db.users.count_documents({}),
        "total_submissions": await db.submissions.count_documents({}),
        "active_reviews": await db.submissions.count_documents({"status": "processing"}),
        "completed_reviews": await db.submissions.count_documents({"status": "completed"}),
        "failed_reviews": await db.submissions.count_documents({"status": "failed"}),
        "total_audit_logs": await db.audit_logs.count_documents({}),
        "security_stats": security_monitor.get_stats(),
    }

    return stats


@router.get("/users")
async def list_all_users(
    _admin: dict = Depends(require_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
):
    """List all users with pagination"""
    return await get_paginated_users(skip=skip, limit=limit, role=role)


@router.get("/submissions")
async def list_all_submissions(
    _admin: dict = Depends(require_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all submissions with pagination"""
    return await get_paginated_submissions(skip=skip, limit=limit, status=status)


@router.get("/audit-logs")
async def get_audit_logs(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    _admin: dict = Depends(require_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
):
    """Get audit logs with filtering"""
    return await get_paginated_audit_logs(
        skip=skip, limit=limit, event_type=event_type, severity=severity, days=days
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, req: Request, admin: dict = Depends(require_super_admin)):
    """Delete a user (super admin only)"""

    db = await mongodb_service.get_database()
    result = await db.users.delete_one({"_id": ObjectId(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="user_deleted",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={"deleted_user_id": user_id},
        severity="warning",
    )

    return {"message": "User deleted successfully"}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    req: Request,
    admin: dict = Depends(require_super_admin),
):
    """Update user role"""

    if role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="Invalid role")

    db = await mongodb_service.get_database()

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": role, "updated_at": datetime.now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="user_role_updated",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={"target_user_id": user_id, "new_role": role},
        severity="info",
    )

    return {"message": "User role updated successfully"}


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    req: Request,
    admin: dict = Depends(require_super_admin),
):
    """Activate or deactivate user"""
    return await update_user_status_common(user_id, is_active, admin, req)


class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str
    username: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    user_id: str
    new_password: str


@router.post("/users/create")
async def create_user_account(
    request: CreateUserRequest,
    req: Request,
    admin: dict = Depends(require_super_admin),
):
    """Create a new user account with role assignment"""

    if request.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = await create_user_common(
        email=request.email,
        password=request.password,
        name=request.name,
        username=request.username,
        role=request.role,
        admin_user=admin,
        request_obj=req,
        verify_email=True,
    )

    return {
        "message": "User account created successfully",
        "user": {
            "email": user["email"],
            "name": user["name"],
            "role": request.role,
        },
    }


@router.get("/analytics/submissions")
async def get_submission_analytics_route(
    _admin: dict = Depends(require_super_admin),
    days: int = Query(30, ge=1, le=365),
):
    """Get submission analytics"""
    return await get_submission_analytics(days=days)


@router.get("/analytics/domains")
async def get_domain_analytics_route(_admin: dict = Depends(require_super_admin)):
    """Get domain distribution analytics"""
    return await get_domain_analytics()


@router.post("/system/clear-cache")
async def clear_system_cache(req: Request, admin: dict = Depends(require_super_admin)):
    """Clear system cache"""
    cache_service.clear_all()  # pylint: disable=no-member

    await audit_logger.log_event(
        event_type="cache_cleared",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        severity="info",
    )

    return {"message": "System cache cleared successfully"}


@router.get("/system/health")
async def get_system_health(_admin: dict = Depends(require_super_admin)):
    """Get detailed system health"""
    db = await mongodb_service.get_database()

    try:
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:  # pylint: disable=broad-exception-caught
        db_status = f"unhealthy: {str(e)}"

    return {
        "database": db_status,
        "security_monitor": "active",
        "audit_logger": "active",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/api-keys")
async def list_api_keys(_admin: dict = Depends(require_super_admin)):
    """List all API keys"""
    db = await mongodb_service.get_database()
    keys = await db.api_keys.find({}).to_list(length=100)

    for key in keys:
        key["_id"] = str(key["_id"])
        key["key"] = key["key"][:8] + "..." if "key" in key else "N/A"

    return {"api_keys": keys}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, req: Request, admin: dict = Depends(require_super_admin)):
    """Revoke an API key"""

    db = await mongodb_service.get_database()
    result = await db.api_keys.update_one(
        {"_id": ObjectId(key_id)},
        {"$set": {"is_active": False, "revoked_at": datetime.now()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    await audit_logger.log_event(
        event_type="api_key_revoked",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={"key_id": key_id},
        severity="warning",
    )

    return {"message": "API key revoked successfully"}


@router.get("/analytics/performance")
async def get_performance_metrics_route(_admin: dict = Depends(require_super_admin)):
    """Get system performance metrics"""
    result = await get_performance_metrics()
    result["timestamp"] = datetime.now().isoformat()
    return result


@router.get("/analytics/user-activity")
async def get_user_activity(_admin: dict = Depends(require_super_admin), days: int = 7):
    """Get user activity statistics"""
    db = await mongodb_service.get_database()
    start_date = datetime.now() - timedelta(days=days)

    pipeline = [
        {MONGO_MATCH: {"timestamp": {"$gte": start_date}}},
        {
            MONGO_GROUP: {
                "_id": "$user_id",
                "event_count": {"$sum": 1},
                "last_activity": {"$max": "$timestamp"},
            }
        },
        {MONGO_SORT: {"event_count": -1}},
        {"$limit": 20},
    ]

    results = await db.audit_logs.aggregate(pipeline).to_list(length=20)

    return {"user_activity": results, "period_days": days}


@router.post("/submissions/{submission_id}/reprocess")
async def reprocess_submission(
    submission_id: str, req: Request, admin: dict = Depends(require_super_admin)
):
    """Reprocess a failed submission"""
    return await reprocess_submission_common(submission_id, admin, req)


@router.delete("/submissions/{submission_id}")
async def delete_submission(
    submission_id: str, req: Request, admin: dict = Depends(require_super_admin)
):
    """Delete a submission"""

    db = await mongodb_service.get_database()
    result = await db.submissions.delete_one({"_id": ObjectId(submission_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Also delete related agent tasks
    await db.agent_tasks.delete_many({"submission_id": submission_id})

    await audit_logger.log_event(
        event_type="submission_deleted",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
        details={"submission_id": submission_id},
        severity="warning",
    )

    return {"message": "Submission deleted successfully"}


@router.post("/users/reset-password")
async def reset_user_password(
    request: ResetPasswordRequest,
    req: Request,
    admin: dict = Depends(require_super_admin),
):
    """Reset user password (super admin only)"""

    db = await mongodb_service.get_database()
    user = await db.users.find_one({"_id": ObjectId(request.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    try:
        success = await user_service.update_password(user["email"], request.new_password)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset password")

        await audit_logger.log_event(
            event_type="password_reset_by_admin",
            user_id=str(admin["_id"]),
            user_email=admin.get("email"),
            ip_address=get_client_ip(req),
            details={
                "target_user_id": request.user_id,
                "target_email": user["email"],
            },
            severity="warning",
        )

        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
