"""Common operations to eliminate code duplication across API routes"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.services.user_service import user_service
from app.utils.request_utils import get_client_ip


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
        user = await user_service.create_user(
            email=email,
            password=password,
            name=name,
            username=username,
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
    except Exception:
        raise HTTPException(status_code=500, detail="User creation failed")


async def get_paginated_users(
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    exclude_super_admin: bool = False,
) -> Dict:
    """Common pagination logic for user listings"""
    db = await mongodb_service.get_database()

    query = {}
    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active
    if exclude_super_admin:
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
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission["_id"] = str(submission["_id"])

    # Add download URLs
    submission["download_urls"] = {
        "manuscript": f"/api/v1/downloads/manuscripts/{submission_id}",
        "review": (
            f"/api/v1/downloads/reviews/{submission_id}"
            if submission.get("status") == "completed"
            else None
        ),
    }

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
    """Common submission analytics aggregation"""
    db = await mongodb_service.get_database()
    start_date = datetime.now() - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                    }
                },
                "count": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=days)
    return {"analytics": results, "period_days": days}


async def get_domain_analytics(limit: int = 100) -> Dict:
    """Common domain distribution analytics"""
    db = await mongodb_service.get_database()

    pipeline = [
        {"$group": {"_id": "$detected_domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]

    if limit > 0:
        pipeline.append({"$limit": limit})

    results = await db.submissions.aggregate(pipeline).to_list(length=limit)
    return {"domain_distribution": results}


def generate_filename_base(submission: Dict) -> str:
    """Common filename generation logic"""
    original_filename = submission.get("file_metadata", {}).get(
        "original_filename", submission.get("title", "manuscript")
    )
    # Remove extension if present
    if "." in original_filename:
        base_name = original_filename.rsplit(".", 1)[0]
    else:
        base_name = original_filename

    return base_name


async def reprocess_submission_common(submission_id: str, user: Dict, request_obj: Any) -> Dict:
    """Common submission reprocessing logic"""
    db = await mongodb_service.get_database()

    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    await db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": {"status": "pending", "updated_at": datetime.now()}},
    )

    await audit_logger.log_event(
        event_type="submission_reprocessed",
        user_id=str(user["_id"]),
        user_email=user.get("email"),
        ip_address=get_client_ip(request_obj),
        details={"submission_id": submission_id},
    )

    return {"message": "Submission queued for reprocessing", "submission_id": submission_id}


async def get_performance_metrics(user_id: Optional[str] = None) -> Dict:
    """Common performance metrics calculation"""
    db = await mongodb_service.get_database()

    query = {"status": "completed", "completed_at": {"$exists": True}}
    if user_id:
        query["user_id"] = user_id

    pipeline = [
        {"$match": query},
        {"$project": {"processing_time": {"$subtract": ["$completed_at", "$created_at"]}}},
        {
            "$group": {
                "_id": None,
                "avg_time_ms": {"$avg": "$processing_time"},
                "min_time_ms": {"$min": "$processing_time"},
                "max_time_ms": {"$max": "$processing_time"},
            }
        },
    ]

    result = await db.submissions.aggregate(pipeline).to_list(length=1)
    return {
        "performance": (
            result[0] if result else {"avg_time_ms": 0, "min_time_ms": 0, "max_time_ms": 0}
        )
    }


async def update_user_status_common(
    user_id: str, is_active: bool, admin: Dict, request_obj: Any
) -> Dict:
    """Common user status update logic"""
    db = await mongodb_service.get_database()

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": is_active, "updated_at": datetime.now()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    await audit_logger.log_event(
        event_type="user_status_updated",
        user_id=str(admin["_id"]),
        user_email=admin.get("email"),
        ip_address=get_client_ip(request_obj),
        details={"target_user_id": user_id, "is_active": is_active},
    )

    return {"message": "User status updated successfully"}


def handle_common_exceptions(operation_name: str = "operation"):
    """Common exception handling decorator"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                from app.utils.logger import get_logger

                logger = get_logger(__name__)
                # Log the exception with a clear message and include traceback,
                # embedding additional context in the message since this logger
                # implementation does not accept the 'extra' keyword argument.
                logger.error(
                    f"{operation_name} failed: {e} | context: args={args}, kwargs={kwargs}",
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail=f"{operation_name} failed")

        return wrapper

    return decorator
