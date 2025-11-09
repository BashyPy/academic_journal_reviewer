"""Common operations to eliminate code duplication across API routes"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.services.user_service import user_service
from app.utils.logger import get_logger
from app.utils.request_utils import get_client_ip

logger = get_logger(__name__)


# MongoDB Operators
MONGO_GROUP = "$group"
MONGO_MATCH = "$match"
MONGO_SORT = "$sort"
MONGO_LIMIT = "$limit"
MONGO_PROJECT = "$project"
MONGO_SET = "$set"
MONGO_SUM = "$sum"
MONGO_COND = "$cond"
MONGO_EQ = "$eq"
MONGO_NE = "$ne"
MONGO_GTE = "$gte"
MONGO_AND = "$and"
MONGO_DATE_TO_STRING = "$dateToString"
MONGO_AVG = "$avg"
MONGO_MIN = "$min"
MONGO_MAX = "$max"
MONGO_SUBTRACT = "$subtract"


async def create_user_common(
    email: str,
    password: str,
    name: str,
    username: Optional[str] = None,
    role: str = "author",
    admin_user: Optional[Dict] = None,
    request_obj: Optional[Any] = None,
    verify_email: bool = False,
) -> Dict:
    """Common user creation logic used across multiple routes"""
    try:
        # Ensure username is a string, defaulting to the email prefix if not provided.
        effective_username = username if username else email.split("@")[0]
        user = await user_service.create_user(
            email=email,
            password=password,
            name=name,
            username=effective_username,
        )

        # Set role if different from default
        if role != "author":
            db = await mongodb_service.get_database()
            await db.users.update_one({"email": email}, {"$set": {"role": role}})

        # Auto-verify email if requested (admin creation)
        if verify_email:
            await user_service.verify_email(email)

        # Log audit event if admin created the user
        if admin_user:
            await audit_logger.log_event(
                event_type="admin_user_created",
                user_id=str(admin_user["_id"]),
                user_email=admin_user.get("email"),
                ip_address=get_client_ip(request_obj) if request_obj else None,
                details={"created_user": email, "role": role},
            )

        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # It's better to log the actual exception for debugging purposes.
        # Assuming a logger is available or can be imported.
        logger.error(f"User creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="User creation failed")


def handle_common_exceptions(func=None, *, operation_name: str = "operation"):
    """Common exception handling decorator"""

    def decorator(f):
        async def wrapper(*args, **kwargs):
            try:
                return await f(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    f"{operation_name} failed: {e} | context: args={args}, kwargs={kwargs}",
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail=f"{operation_name} failed")

            return wrapper

        if func:
            return decorator(func)
        return decorator


async def get_paginated_users(
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    exclude_super_admin: bool = False,
) -> Dict:
    """Common pagination logic for user listings"""
    db = await mongodb_service.get_database()

    query: Dict[str, Any] = {}
    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active

    if exclude_super_admin:
        if "role" in query:
            # If a role is specified, and we need to exclude super_admin,
            # we combine the conditions.
            query["$and"] = [{"role": query.pop("role")}, {"role": {"$ne": "super_admin"}}]
        else:
            # If no role is specified, just exclude super_admin.
            query["role"] = {"$ne": "super_admin"}

    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    total = await db.users.count_documents(query)

    for user in users:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)

    return {"users": users, "total": total, "skip": skip, "limit": limit}


async def get_paginated_submissions(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    sort_field: str = "created_at",
    sort_direction: int = -1,
) -> Dict:
    """Common pagination logic for submission listings"""
    if sort_direction not in [1, -1]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort_direction. Use 1 for ascending, -1 for descending.",
        )

    allowed_sort_fields = ["created_at", "updated_at", "status", "title"]
    if sort_field not in allowed_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_field. Allowed fields are: {', '.join(allowed_sort_fields)}",
        )

    db = await mongodb_service.get_database()

    query = {}
    if status:
        query["status"] = status

    submissions = (
        await db.submissions.find(query)
        .sort(sort_field, sort_direction)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total = await db.submissions.count_documents(query)

    for sub in submissions:
        sub["_id"] = str(sub["_id"])
        # Remove or convert binary fields that can't be JSON serialized
        for key, value in sub.items():
            if isinstance(value, bytes):
                sub[key] = f"<binary data: {len(value)} bytes>"

    return {
        "submissions": submissions,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


async def get_submission_with_downloads(submission_id: str) -> Dict:
    """Get submission details with download URLs"""
    db = await mongodb_service.get_database()
    try:
        obj_submission_id = ObjectId(submission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid submission_id format: {e}")

    submission = await db.submissions.find_one({"_id": obj_submission_id})

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission["_id"] = str(submission["_id"])

    return submission


async def get_paginated_audit_logs(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = 7,
) -> Dict:
    """Common pagination logic for audit logs"""
    db = await mongodb_service.get_database()

    query = {"timestamp": {"$gte": datetime.now() - timedelta(days=days)}}
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


async def get_submission_analytics(days: int = 30) -> Dict:
    """Common submission analytics logic"""
    db = await mongodb_service.get_database()
    start_date = datetime.now() - timedelta(days=days)

    pipeline = [
        {MONGO_MATCH: {"created_at": {MONGO_GTE: start_date}}},
        {
            MONGO_GROUP: {
                "_id": {
                    MONGO_DATE_TO_STRING: {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                    }
                },
                "count": {MONGO_SUM: 1},
                "completed": {
                    MONGO_SUM: {MONGO_COND: [{MONGO_EQ: ["$status", "completed"]}, 1, 0]}
                },
                "failed": {MONGO_SUM: {MONGO_COND: [{MONGO_EQ: ["$status", "failed"]}, 1, 0]}},
            }
        },
        {MONGO_SORT: {"_id": 1}},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=days)
    return {"analytics": results, "period_days": days}


async def get_performance_analytics(user_id: Optional[str] = None) -> Dict:
    """Common performance analytics logic"""
    db = await mongodb_service.get_database()
    query: Dict[str, Any] = {"status": "completed", "completed_at": {"$ne": None}}

    if user_id:
        try:
            query["user_id"] = ObjectId(user_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid user_id format: {e}")

    processing_time_field = "$processing_time"
    pipeline = [
        {"$match": query},
        {"$project": {"processing_time": {"$subtract": ["$completed_at", "$created_at"]}}},
        {
            "$group": {
                "_id": None,
                "avg_time_ms": {"$avg": processing_time_field},
                "min_time_ms": {"$min": processing_time_field},
                "max_time_ms": {"$max": processing_time_field},
            }
        },
    ]

    result = await db.submissions.aggregate(pipeline).to_list(length=1)
    return {"performance": result[0] if result else {}}


# Aliases for backward compatibility
get_performance_metrics = get_performance_analytics
get_domain_analytics = get_submission_analytics


def generate_filename_base(submission_id: str, title: str = "manuscript") -> str:
    """Generate safe filename base for downloads"""
    import re

    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:50]
    return f"{safe_title}_{submission_id[:8]}"


async def update_user_status_common(user_id: str, is_active: bool) -> Dict:
    """Update user active status"""
    db = await mongodb_service.get_database()
    try:
        obj_user_id = ObjectId(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid user_id: {e}")

    result = await db.users.update_one({"_id": obj_user_id}, {"$set": {"is_active": is_active}})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User status updated"}


async def reprocess_submission_common(submission_id: str) -> Dict:
    """Reprocess a failed submission"""
    db = await mongodb_service.get_database()
    try:
        obj_submission_id = ObjectId(submission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid submission_id: {e}")

    submission = await db.submissions.find_one({"_id": obj_submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    await db.submissions.update_one(
        {"_id": obj_submission_id}, {"$set": {"status": "pending", "error_message": None}}
    )

    return {"message": "Submission queued for reprocessing"}
