"""Admin Dashboard API Routes (Admin role - not Super Admin)"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.middleware.dual_auth import get_current_user
from app.models.roles import UserRole, Permission, has_permission
from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

router = APIRouter(prefix="/admin-dashboard", tags=["admin-dashboard"])
logger = get_logger(__name__)


def require_admin(user: dict = Depends(get_current_user)):
    """Require admin or super_admin role"""
    role = user.get("role")
    if role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    """Get admin dashboard statistics"""
    db = await mongodb_service.get_database()
    
    # Admins can see user and submission stats but not full system access
    stats = {
        "total_users": await db.users.count_documents({}),
        "active_users": await db.users.count_documents({"is_active": True}),
        "total_submissions": await db.submissions.count_documents({}),
        "pending_submissions": await db.submissions.count_documents({"status": "pending"}),
        "processing_submissions": await db.submissions.count_documents({"status": "processing"}),
        "completed_submissions": await db.submissions.count_documents({"status": "completed"}),
        "failed_submissions": await db.submissions.count_documents({"status": "failed"}),
        "recent_activity_count": await db.audit_logs.count_documents({
            "timestamp": {"$gte": datetime.now() - timedelta(hours=24)}
        }),
    }
    
    return stats


@router.get("/users")
async def list_users(
    admin: dict = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List users (admins can view but not modify super_admins)"""
    db = await mongodb_service.get_database()
    
    query = {}
    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active
    
    # Admins cannot see super_admin users
    if admin.get("role") == UserRole.ADMIN.value:
        query["role"] = {"$ne": UserRole.SUPER_ADMIN.value}
    
    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    total = await db.users.count_documents(query)
    
    for user in users:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
    
    return {"users": users, "total": total, "skip": skip, "limit": limit}


@router.get("/users/{user_id}")
async def get_user_details(user_id: str, admin: dict = Depends(require_admin)):
    """Get detailed user information"""
    from bson import ObjectId
    
    db = await mongodb_service.get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Admins cannot view super_admin details
    if admin.get("role") == UserRole.ADMIN.value and user.get("role") == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Cannot access super admin details")
    
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    
    return user


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: UpdateUserStatusRequest,
    admin: dict = Depends(require_admin),
):
    """Activate or deactivate user (cannot modify super_admins)"""
    from bson import ObjectId
    
    db = await mongodb_service.get_database()
    
    # Check if target user exists and is not super_admin
    target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.get("role") == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Cannot modify super admin accounts")
    
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": request.is_active, "updated_at": datetime.now()}},
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await audit_logger.log_event(
        event_type="user_status_updated",
        user_id=admin.get("user_id"),
        details={"target_user_id": user_id, "is_active": request.is_active},
        severity="info",
    )
    
    return {"message": f"User {'activated' if request.is_active else 'deactivated'} successfully"}


@router.get("/submissions")
async def list_submissions(
    admin: dict = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all submissions"""
    db = await mongodb_service.get_database()
    
    query = {}
    if status:
        query["status"] = status
    
    submissions = await db.submissions.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    total = await db.submissions.count_documents(query)
    
    for sub in submissions:
        sub["_id"] = str(sub["_id"])
    
    return {"submissions": submissions, "total": total, "skip": skip, "limit": limit}


@router.get("/submissions/{submission_id}")
async def get_submission_details(submission_id: str, admin: dict = Depends(require_admin)):
    """Get detailed submission information"""
    from bson import ObjectId
    
    db = await mongodb_service.get_database()
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission["_id"] = str(submission["_id"])
    
    # Add download URLs
    submission["download_urls"] = {
        "manuscript": f"/api/v1/downloads/manuscripts/{submission_id}",
        "review": f"/api/v1/downloads/reviews/{submission_id}" if submission.get("status") == "completed" else None
    }
    
    return submission


@router.get("/audit-logs")
async def get_audit_logs(
    admin: dict = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = Query(7, ge=1, le=30),
):
    """Get audit logs (limited to 30 days for admins)"""
    db = await mongodb_service.get_database()
    
    query = {"timestamp": {"$gte": datetime.now() - timedelta(days=days)}}
    if event_type:
        query["event_type"] = event_type
    if severity:
        query["severity"] = severity
    
    logs = await db.audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)
    total = await db.audit_logs.count_documents(query)
    
    for log in logs:
        log["_id"] = str(log["_id"])
    
    return {"logs": logs, "total": total, "skip": skip, "limit": limit}


@router.get("/analytics/submissions")
async def get_submission_analytics(
    admin: dict = Depends(require_admin),
    days: int = Query(30, ge=1, le=90),
):
    """Get submission analytics"""
    db = await mongodb_service.get_database()
    
    start_date = datetime.now() - timedelta(days=days)
    
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "count": {"$sum": 1},
                "completed": {
                    "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                },
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    
    results = await db.submissions.aggregate(pipeline).to_list(length=days)
    
    return {"analytics": results, "period_days": days}


@router.get("/analytics/domains")
async def get_domain_analytics(admin: dict = Depends(require_admin)):
    """Get domain distribution analytics"""
    db = await mongodb_service.get_database()
    
    pipeline = [
        {"$group": {"_id": "$detected_domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    
    results = await db.submissions.aggregate(pipeline).to_list(length=20)
    
    return {"domain_distribution": results}


@router.get("/api-keys")
async def list_api_keys(admin: dict = Depends(require_admin)):
    """List API keys (admins can view but not create/revoke super_admin keys)"""
    db = await mongodb_service.get_database()
    
    query = {}
    # Admins cannot see super_admin API keys
    if admin.get("role") == UserRole.ADMIN.value:
        query["role"] = {"$ne": UserRole.SUPER_ADMIN.value}
    
    keys = await db.api_keys.find(query).to_list(length=100)
    
    for key in keys:
        key["_id"] = str(key["_id"])
        key["key"] = key["key"][:8] + "..." if "key" in key else "N/A"
    
    return {"api_keys": keys}


class CreateAPIKeyRequest(BaseModel):
    name: str
    role: str
    expires_days: int = 365


@router.post("/api-keys")
async def create_api_key(
    request: CreateAPIKeyRequest,
    admin: dict = Depends(require_admin),
):
    """Create API key (admins cannot create super_admin keys)"""
    from app.middleware.auth import auth_service
    
    # Admins cannot create super_admin API keys
    if request.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Cannot create super admin API keys")
    
    # Validate role
    if request.role not in [r.value for r in UserRole if r != UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await auth_service.create_api_key(
        name=request.name,
        role=request.role,
        expires_days=request.expires_days,
    )
    
    await audit_logger.log_event(
        event_type="api_key_created",
        user_id=admin.get("user_id"),
        details={"key_name": request.name, "role": request.role},
        severity="info",
    )
    
    return result


@router.get("/recent-activity")
async def get_recent_activity(
    admin: dict = Depends(require_admin),
    limit: int = Query(20, ge=1, le=50),
):
    """Get recent system activity"""
    db = await mongodb_service.get_database()
    
    logs = await db.audit_logs.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
    
    for log in logs:
        log["_id"] = str(log["_id"])
    
    return {"recent_activity": logs}


@router.get("/user-statistics")
async def get_user_statistics(admin: dict = Depends(require_admin)):
    """Get user statistics by role"""
    db = await mongodb_service.get_database()
    
    pipeline = [
        {"$group": {"_id": "$role", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    
    # Exclude super_admin from stats for regular admins
    if admin.get("role") == UserRole.ADMIN.value:
        pipeline.insert(0, {"$match": {"role": {"$ne": UserRole.SUPER_ADMIN.value}}})
    
    results = await db.users.aggregate(pipeline).to_list(length=10)
    
    return {"user_statistics": results}
