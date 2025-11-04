"""Super Admin Dashboard API Routes"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.middleware.dual_auth import get_current_user
from app.models.roles import UserRole
from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.services.security_monitor import security_monitor
from app.utils.logger import get_logger

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
        raise HTTPException(
            status_code=403, detail="Super admin access required"
        )
    return user


class SystemStats(BaseModel):
    total_users: int
    total_submissions: int
    active_reviews: int
    completed_reviews: int
    failed_reviews: int
    total_audit_logs: int


@router.get("/dashboard/stats")
async def get_dashboard_stats(admin: dict = Depends(require_super_admin)):
    """Get comprehensive system statistics"""
    db = await mongodb_service.get_database()

    stats = {
        "total_users": await db.users.count_documents({}),
        "total_submissions": await db.submissions.count_documents({}),
        "active_reviews": await db.submissions.count_documents(
            {"status": "processing"}
        ),
        "completed_reviews": await db.submissions.count_documents(
            {"status": "completed"}
        ),
        "failed_reviews": await db.submissions.count_documents(
            {"status": "failed"}
        ),
        "total_audit_logs": await db.audit_logs.count_documents({}),
        "security_stats": security_monitor.get_stats(),
    }

    return stats


@router.get("/users")
async def list_all_users(
    admin: dict = Depends(require_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
):
    """List all users with pagination"""
    db = await mongodb_service.get_database()

    query = {}
    if role:
        query["role"] = role

    users = (
        await db.users.find(query)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total = await db.users.count_documents(query)

    for user in users:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)

    return {"users": users, "total": total, "skip": skip, "limit": limit}


@router.get("/submissions")
async def list_all_submissions(
    admin: dict = Depends(require_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all submissions with pagination"""
    db = await mongodb_service.get_database()

    query = {}
    if status:
        query["status"] = status

    submissions = (
        await db.submissions.find(query)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total = await db.submissions.count_documents(query)

    for sub in submissions:
        sub["_id"] = str(sub["_id"])

    return {
        "submissions": submissions,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/audit-logs")
async def get_audit_logs(
    admin: dict = Depends(require_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
):
    """Get audit logs with filtering"""
    db = await mongodb_service.get_database()

    query = {
        "timestamp": {"$gte": datetime.now() - timedelta(days=days)}
    }
    if event_type:
        query["event_type"] = event_type
    if severity:
        query["severity"] = severity

    logs = (
        await db.audit_logs.find(query)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total = await db.audit_logs.count_documents(query)

    for log in logs:
        log["_id"] = str(log["_id"])

    return {"logs": logs, "total": total, "skip": skip, "limit": limit}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str, admin: dict = Depends(require_super_admin)
):
    """Delete a user (super admin only)"""
    from bson import ObjectId

    db = await mongodb_service.get_database()
    result = await db.users.delete_one({"_id": ObjectId(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="user_deleted",
        user_id=admin.get("user_id"),
        details={"deleted_user_id": user_id},
        severity="warning",
    )

    return {"message": "User deleted successfully"}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    admin: dict = Depends(require_super_admin),
):
    """Update user role"""
    from bson import ObjectId

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
        user_id=admin.get("user_id"),
        details={"target_user_id": user_id, "new_role": role},
        severity="info",
    )

    return {"message": "User role updated successfully"}


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    admin: dict = Depends(require_super_admin),
):
    """Activate or deactivate user"""
    from bson import ObjectId

    db = await mongodb_service.get_database()

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": is_active, "updated_at": datetime.now()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    await audit_logger.log_event(
        event_type="user_status_updated",
        user_id=admin.get("user_id"),
        details={"target_user_id": user_id, "is_active": is_active},
        severity="warning",
    )

    return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}


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
    admin: dict = Depends(require_super_admin),
):
    """Create a new user account with role assignment"""
    from app.services.user_service import user_service

    if request.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="Invalid role")

    try:
        user = await user_service.create_user(
            email=request.email,
            password=request.password,
            name=request.name,
            username=request.username,
        )

        db = await mongodb_service.get_database()
        await db.users.update_one(
            {"email": request.email},
            {"$set": {"role": request.role, "email_verified": True}},
        )

        await audit_logger.log_event(
            event_type="user_created_by_admin",
            user_id=admin.get("user_id"),
            details={"created_user_email": request.email, "role": request.role},
            severity="info",
        )

        return {
            "message": "User account created successfully",
            "user": {"email": user["email"], "name": user["name"], "role": request.role},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user account")


@router.get("/analytics/submissions")
async def get_submission_analytics(
    admin: dict = Depends(require_super_admin),
    days: int = Query(30, ge=1, le=365),
):
    """Get submission analytics"""
    db = await mongodb_service.get_database()

    start_date = datetime.now() - timedelta(days=days)

    pipeline = [
        {MONGO_MATCH: {"created_at": {"$gte": start_date}}},
        {
            MONGO_GROUP: {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                    }
                },
                "count": {"$sum": 1},
                "completed": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "completed"]}, 1, 0]
                    }
                },
                "failed": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "failed"]}, 1, 0]
                    }
                },
            }
        },
        {MONGO_SORT: {"_id": 1}},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=days)

    return {"analytics": results, "period_days": days}


@router.get("/analytics/domains")
async def get_domain_analytics(admin: dict = Depends(require_super_admin)):
    """Get domain distribution analytics"""
    db = await mongodb_service.get_database()

    pipeline = [
        {MONGO_GROUP: {"_id": "$detected_domain", "count": {"$sum": 1}}},
        {MONGO_SORT: {"count": -1}},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=100)

    return {"domain_distribution": results}


@router.post("/system/clear-cache")
async def clear_system_cache(admin: dict = Depends(require_super_admin)):
    """Clear system cache"""
    from app.services.cache_service import cache_service

    cache_service.clear_all()

    await audit_logger.log_event(
        event_type="cache_cleared",
        user_id=admin.get("user_id"),
        severity="info",
    )

    return {"message": "System cache cleared successfully"}


@router.get("/system/health")
async def get_system_health(admin: dict = Depends(require_super_admin)):
    """Get detailed system health"""
    db = await mongodb_service.get_database()

    try:
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "database": db_status,
        "security_monitor": "active",
        "audit_logger": "active",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/api-keys")
async def list_api_keys(admin: dict = Depends(require_super_admin)):
    """List all API keys"""
    db = await mongodb_service.get_database()
    keys = await db.api_keys.find({}).to_list(length=100)

    for key in keys:
        key["_id"] = str(key["_id"])
        key["key"] = key["key"][:8] + "..." if "key" in key else "N/A"

    return {"api_keys": keys}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, admin: dict = Depends(require_super_admin)):
    """Revoke an API key"""
    from bson import ObjectId

    db = await mongodb_service.get_database()
    result = await db.api_keys.update_one(
        {"_id": ObjectId(key_id)},
        {"$set": {"is_active": False, "revoked_at": datetime.now()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    await audit_logger.log_event(
        event_type="api_key_revoked",
        user_id=admin.get("user_id"),
        details={"key_id": key_id},
        severity="warning",
    )

    return {"message": "API key revoked successfully"}


@router.get("/analytics/performance")
async def get_performance_metrics(admin: dict = Depends(require_super_admin)):
    """Get system performance metrics"""
    db = await mongodb_service.get_database()

    # Average processing time
    pipeline = [
        {
            MONGO_MATCH: {
                "status": "completed",
                "completed_at": {"$exists": True},
            }
        },
        {
            "$project": {
                "processing_time": {
                    "$subtract": ["$completed_at", "$created_at"]
                }
            }
        },
        {
            MONGO_GROUP: {
                "_id": None,
                "avg_time_ms": {"$avg": PROCESSING_TIME},
                "min_time_ms": {"$min": PROCESSING_TIME},
                "max_time_ms": {"$max": PROCESSING_TIME},
            }
        },
    ]

    result = await db.submissions.aggregate(pipeline).to_list(length=1)

    return {
        "performance": result[0] if result else {},
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/analytics/user-activity")
async def get_user_activity(
    admin: dict = Depends(require_super_admin), days: int = 7
):
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
    submission_id: str, admin: dict = Depends(require_super_admin)
):
    """Reprocess a failed submission"""
    from bson import ObjectId

    db = await mongodb_service.get_database()
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Reset submission status
    await db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": {"status": "pending", "updated_at": datetime.now()}},
    )

    await audit_logger.log_event(
        event_type="submission_reprocessed",
        user_id=admin.get("user_id"),
        details={"submission_id": submission_id},
        severity="info",
    )

    return {"message": "Submission queued for reprocessing"}


@router.delete("/submissions/{submission_id}")
async def delete_submission(
    submission_id: str, admin: dict = Depends(require_super_admin)
):
    """Delete a submission"""
    from bson import ObjectId

    db = await mongodb_service.get_database()
    result = await db.submissions.delete_one({"_id": ObjectId(submission_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Also delete related agent tasks
    await db.agent_tasks.delete_many({"submission_id": submission_id})

    await audit_logger.log_event(
        event_type="submission_deleted",
        user_id=admin.get("user_id"),
        details={"submission_id": submission_id},
        severity="warning",
    )

    return {"message": "Submission deleted successfully"}


@router.post("/users/reset-password")
async def reset_user_password(
    request: ResetPasswordRequest,
    admin: dict = Depends(require_super_admin),
):
    """Reset user password (super admin only)"""
    from app.services.user_service import user_service

    await mongodb_service.get_database()
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    try:
        success = await user_service.update_password(user["email"], request.new_password)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset password")

        await audit_logger.log_event(
            event_type="password_reset_by_admin",
            user_id=admin.get("user_id"),
            details={
                "target_user_id": request.user_id,
                "target_email": user["email"],
            },
            severity="warning",
        )

        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
