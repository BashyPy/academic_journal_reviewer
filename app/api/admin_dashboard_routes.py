"""Admin Dashboard API Routes (Admin role - not Super Admin)"""

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.middleware.auth import auth_service
from app.middleware.dual_auth import get_current_user
from app.models.roles import UserRole
from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.utils.common_operations import (
    get_paginated_audit_logs,
    get_paginated_submissions,
    get_submission_analytics,
    get_submission_with_downloads,
    update_user_status_common,
)
from app.utils.logger import get_logger
from app.utils.request_utils import get_client_ip

router = APIRouter(prefix="/admin-dashboard", tags=["admin-dashboard"])
logger = get_logger(__name__)


USER_NOT_FOUND = "User not found"
MONGO_SORT = "$sort"
MONGO_GROUP = "$group"
MONGO_MATCH = "$match"
MONGO_COUNT = "$count"
MONGO_IF_NULL = "$ifNull"
MONGO_ARRAY_ELEM_AT = "$arrayElemAt"
MONGO_PROJECT = "$project"
MONGO_FACET = "$facet"
MONGO_SUM = "$sum"
MONGO_NE = "$ne"
MONGO_LIMIT = "$limit"


def require_admin(user: dict = Depends(get_current_user)):
    """Require admin or super_admin role"""
    role = user.get("role")
    if role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource.",
        )
    return user


@router.get("/stats")
async def get_dashboard_stats(_admin: dict = Depends(require_admin)):
    """Get dashboard statistics"""
    db = await mongodb_service.get_database()

    user_stats_pipeline = [
        {
            MONGO_FACET: {
                "total_users": [{MONGO_COUNT: "count"}],
                "active_users": [{MONGO_MATCH: {"is_active": True}}, {MONGO_COUNT: "count"}],
            }
        },
        {
            MONGO_PROJECT: {
                "total_users": {
                    MONGO_IF_NULL: [{MONGO_ARRAY_ELEM_AT: ["$total_users.count", 0]}, 0]
                },
                "active_users": {
                    MONGO_IF_NULL: [{MONGO_ARRAY_ELEM_AT: ["$active_users.count", 0]}, 0]
                },
            }
        },
    ]
    submission_stats_pipeline = [
        {
            MONGO_FACET: {
                "total_submissions": [{MONGO_COUNT: "count"}],
                "pending_submissions": [
                    {MONGO_MATCH: {"status": "pending"}},
                    {MONGO_COUNT: "count"},
                ],
                "processing_submissions": [
                    {MONGO_MATCH: {"status": "processing"}},
                    {MONGO_COUNT: "count"},
                ],
                "completed_submissions": [
                    {MONGO_MATCH: {"status": "completed"}},
                    {MONGO_COUNT: "count"},
                ],
                "failed_submissions": [{MONGO_MATCH: {"status": "failed"}}, {MONGO_COUNT: "count"}],
            }
        },
        {
            MONGO_PROJECT: {
                "total_submissions": {
                    MONGO_IF_NULL: [{MONGO_ARRAY_ELEM_AT: ["$total_submissions.count", 0]}, 0]
                },
                "pending_submissions": {
                    MONGO_IF_NULL: [{MONGO_ARRAY_ELEM_AT: ["$pending_submissions.count", 0]}, 0]
                },
                "processing_submissions": {
                    MONGO_IF_NULL: [{MONGO_ARRAY_ELEM_AT: ["$processing_submissions.count", 0]}, 0]
                },
                "completed_submissions": {
                    MONGO_IF_NULL: [{MONGO_ARRAY_ELEM_AT: ["$completed_submissions.count", 0]}, 0]
                },
                "failed_submissions": {
                    MONGO_IF_NULL: [{MONGO_ARRAY_ELEM_AT: ["$failed_submissions.count", 0]}, 0]
                },
            }
        },
    ]

    user_stats_result = await db.users.aggregate(user_stats_pipeline).to_list(length=1)
    submission_stats_result = await db.submissions.aggregate(submission_stats_pipeline).to_list(
        length=1
    )
    recent_activity_count = await db.audit_logs.count_documents(
        {"timestamp": {"$gte": datetime.now() - timedelta(hours=24)}}
    )

    user_stats = (
        user_stats_result[0] if user_stats_result else {"total_users": 0, "active_users": 0}
    )
    submission_stats = (
        submission_stats_result[0]
        if submission_stats_result
        else {
            "total_submissions": 0,
            "pending_submissions": 0,
            "processing_submissions": 0,
            "completed_submissions": 0,
            "failed_submissions": 0,
        }
    )

    _ = {
        **user_stats,
        **submission_stats,
        "recent_activity_count": recent_activity_count,
    }


@router.get("/users")
async def list_users(
    admin: dict = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List users"""
    db = await mongodb_service.get_database()
    query = {}

    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active

    # Admins cannot see super_admin users
    if admin.get("role") == UserRole.ADMIN.value:
        query["role"] = {MONGO_NE: UserRole.SUPER_ADMIN.value}

    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    total = await db.users.count_documents(query)

    for user in users:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)

    return {"users": users, "total": total, "skip": skip, "limit": limit}


@router.get("/users/{user_id}")
async def get_user_details(user_id: str, admin: dict = Depends(require_admin)):
    """Get detailed user information"""

    db = await mongodb_service.get_database()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID format") from None

    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

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
    req: Request,
    admin: dict = Depends(require_admin),
):
    """Activate or deactivate user (cannot modify super_admins)"""
    db = await mongodb_service.get_database()
    try:
        target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID format") from None

    if not target_user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    if target_user.get("role") == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Cannot modify super admin accounts")

    return await update_user_status_common(user_id, request.is_active, admin, req)


@router.get("/submissions")
async def list_submissions(
    _admin: dict = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all submissions"""
    return await get_paginated_submissions(skip, limit, status)


@router.get("/submissions/{submission_id}")
async def get_submission_details(submission_id: str, _admin: dict = Depends(require_admin)):
    """Get detailed submission information"""
    return await get_submission_with_downloads(submission_id)


@router.get("/audit-logs")
async def get_audit_logs(  # pylint: disable=too-many-arguments
    _admin: dict = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = Query(7, ge=1, le=30),
):
    """Get audit logs (limited to 30 days for admins)"""
    return await get_paginated_audit_logs(skip, limit, event_type, severity, days)


@router.get("/analytics/submissions")
async def get_submission_analytics_route(_admin: dict = Depends(require_admin)):
    """Get submission analytics"""
    return await get_submission_analytics()


@router.get("/analytics/domains")
async def get_domain_analytics(_admin: dict = Depends(require_admin)):
    """Get domain distribution analytics"""
    db = await mongodb_service.get_database()

    pipeline = [
        {MONGO_GROUP: {"_id": "$detected_domain", "count": {MONGO_SUM: 1}}},
        {MONGO_SORT: {"count": -1}},
        {MONGO_LIMIT: 20},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=20)
    return results


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
    req: Request,
    admin: dict = Depends(require_admin),
):
    """Create API key (admins cannot create super_admin keys)"""

    # Admins cannot create super_admin API keys
    if request.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Cannot create super admin API keys")

    # Validate role
    valid_roles = [r.value for r in UserRole if r != UserRole.SUPER_ADMIN]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    new_key_data = await auth_service.create_api_key(
        name=request.name,
        role=request.role,
        expires_days=request.expires_days,
    )

    await audit_logger.log_event(
        event_type="api_key_created",
        details=f"API key '{request.name}' created for role '{request.role}'.",
        user_email=admin.get("email"),
        ip_address=get_client_ip(req),
    )

    return new_key_data


@router.get("/recent-activity")
async def get_recent_activity(
    _admin: dict = Depends(require_admin),
    limit: int = Query(20, ge=1, le=50),
):
    """Get recent system activity"""
    db = await mongodb_service.get_database()
    recent_logs = (
        await db.audit_logs.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
    )
    for log in recent_logs:
        log["_id"] = str(log["_id"])
    return {"recent_activity": recent_logs}


@router.get("/analytics/users")
async def get_user_statistics(admin: dict = Depends(require_admin)):
    """Get user statistics by role"""
    db = await mongodb_service.get_database()

    pipeline = [
        {MONGO_GROUP: {"_id": "$role", "count": {MONGO_SUM: 1}}},
        {MONGO_SORT: {"count": -1}},
    ]

    # Exclude super_admin from stats for regular admins
    if admin.get("role") == UserRole.ADMIN.value:
        match_filter = {MONGO_MATCH: {"role": {MONGO_NE: UserRole.SUPER_ADMIN.value}}}
        pipeline.insert(0, match_filter)

    results = await db.users.aggregate(pipeline).to_list(length=10)

    return {"user_statistics": results}
