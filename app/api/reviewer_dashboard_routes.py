"""Reviewer Dashboard API Routes"""

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.middleware.dual_auth import get_current_user
from app.models.roles import UserRole
from app.services.mongodb_service import mongodb_service
from app.utils.common_operations import get_submission_with_downloads
from app.utils.logger import get_logger

router = APIRouter(prefix="/reviewer", tags=["reviewer-dashboard"])
logger = get_logger(__name__)

MONGO_MATCH = "$match"
MONGO_EXISTS = "$exists"
MONGO_PROJECT = "$project"
MONGO_GROUP = "$group"
MONGO_COMPLETED_AT = "$completed_at"
MONGO_SUBTRACT = "$subtract"
INVALID_ASSIGNMENT_ID_FORMAT = "Invalid assignment ID format"


def require_reviewer(user: dict = Depends(get_current_user)):
    """Require reviewer role or higher"""
    role = user.get("role", "author")
    if role not in [
        UserRole.REVIEWER.value,
        UserRole.EDITOR.value,
        UserRole.ADMIN.value,
        UserRole.SUPER_ADMIN.value,
    ]:
        raise HTTPException(status_code=403, detail="Reviewer access required")
    return user


@router.get("/dashboard/stats")
async def get_reviewer_stats(user: dict = Depends(require_reviewer)):
    """Get reviewer-specific statistics"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])

    # Count assignments
    total_assigned = await db.review_assignments.count_documents({"reviewer_id": reviewer_id})
    pending = await db.review_assignments.count_documents(
        {"reviewer_id": reviewer_id, "status": "pending"}
    )
    in_progress = await db.review_assignments.count_documents(
        {"reviewer_id": reviewer_id, "status": "in_progress"}
    )
    completed = await db.review_assignments.count_documents(
        {"reviewer_id": reviewer_id, "status": "completed"}
    )
    pipeline = [
        {
            MONGO_MATCH: {
                "reviewer_id": reviewer_id,
                "completed_at": {MONGO_EXISTS: True},
                "started_at": {MONGO_EXISTS: True},
            }
        },
        {MONGO_PROJECT: {"review_time": {"$subtract": ["$completed_at", "$started_at"]}}},
        {MONGO_GROUP: {"_id": None, "avg_time_ms": {"$avg": "$review_time"}}},
    ]

    avg_result = await db.review_assignments.aggregate(pipeline).to_list(length=1)
    avg_time_ms = avg_result[0].get("avg_time_ms") if avg_result else 0
    avg_time_hours = (avg_time_ms / (1000 * 60 * 60)) if avg_time_ms else 0

    return {
        "total_assigned": total_assigned,
        "pending_reviews": pending,
        "in_progress": in_progress,
        "completed_reviews": completed,
        "avg_review_time_hours": round(avg_time_hours, 2),
    }


@router.get("/assignments")
async def get_reviewer_assignments(
    user: dict = Depends(require_reviewer),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """Get reviewer's assigned manuscripts"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])

    query = {"reviewer_id": reviewer_id}
    if status:
        query["status"] = status

    pipeline = [
        {MONGO_MATCH: query},
        {"$sort": {"assigned_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "submissions",
                "localField": "submission_id",
                "foreignField": "_id",
                "as": "submission_details",
            }
        },
        {"$unwind": {"path": "$submission_details", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "_id": {"$toString": "$_id"},
                "submission_title": {"$ifNull": ["$submission_details.title", "Untitled"]},
                "submission_domain": {
                    "$ifNull": ["$submission_details.detected_domain", "Unknown"]
                },
                "submission_status": {"$ifNull": ["$submission_details.status", "unknown"]},
            }
        },
        {"$project": {"submission_details": 0}},
    ]

    assignments = await db.review_assignments.aggregate(pipeline).to_list(length=limit)
    total = await db.review_assignments.count_documents(query)

    return {"assignments": assignments, "total": total, "skip": skip, "limit": limit}


@router.get("/assignments/{assignment_id}")
async def get_assignment_detail(assignment_id: str, user: dict = Depends(require_reviewer)):
    """Get detailed assignment information with manuscript content"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])
    try:
        obj_assignment_id = ObjectId(assignment_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=INVALID_ASSIGNMENT_ID_FORMAT)

    assignment = await db.review_assignments.find_one(
        {"_id": obj_assignment_id, "reviewer_id": reviewer_id}
    )

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment["_id"] = str(assignment["_id"])
    submission_id = assignment["submission_id"]

    # Get submission details
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if submission:
        submission_with_urls = await get_submission_with_downloads(submission_id)
        submission["_id"] = str(submission["_id"])
        assignment["submission_details"] = submission_with_urls

    return assignment


@router.post("/assignments/{assignment_id}/start")
async def start_review(assignment_id: str, user: dict = Depends(require_reviewer)):
    """Mark review as started"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])
    try:
        obj_assignment_id = ObjectId(assignment_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=INVALID_ASSIGNMENT_ID_FORMAT)

    result = await db.review_assignments.update_one(
        {
            "_id": obj_assignment_id,
            "reviewer_id": reviewer_id,
            "status": "pending",
        },
        {"$set": {"status": "in_progress", "started_at": datetime.now()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found or not in pending state")

    return {"message": "Review started"}


@router.post("/assignments/{assignment_id}/submit")
async def submit_review(
    assignment_id: str, review_data: dict, user: dict = Depends(require_reviewer)
):
    """Submit completed review"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])
    try:
        obj_assignment_id = ObjectId(assignment_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail=INVALID_ASSIGNMENT_ID_FORMAT)

    # Validate assignment
    assignment = await db.review_assignments.find_one(
        {"_id": obj_assignment_id, "reviewer_id": reviewer_id}
    )

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Review already submitted")

    # Update assignment with review
    result = await db.review_assignments.update_one(
        {"_id": obj_assignment_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": datetime.now(),
                "review": review_data,
            }
        },
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to submit review")

    return {"message": "Review submitted successfully"}


@router.put("/assignments/{assignment_id}/update")
async def update_review(
    assignment_id: str, review_data: dict, user: dict = Depends(require_reviewer)
):
    """Update an existing review (before final submission)"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])

    try:
        obj_assignment_id = ObjectId(assignment_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid assignment ID format")

    result = await db.review_assignments.update_one(
        {
            "_id": obj_assignment_id,
            "reviewer_id": reviewer_id,
            "status": "in_progress",
        },
        {"$set": {"review": review_data, "last_updated": datetime.now()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found or not in progress")

    return {"message": "Review updated successfully"}


@router.get("/analytics/timeline")
async def get_review_timeline(
    user: dict = Depends(require_reviewer),
    days: int = Query(30, ge=7, le=365),
):
    """Get review completion timeline"""
    start_date = datetime.now() - timedelta(days=days)
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])

    pipeline = [
        {
            MONGO_MATCH: {
                "reviewer_id": reviewer_id,
                "completed_at": {MONGO_EXISTS: True, "$gte": start_date},
            }
        },
        {
            MONGO_GROUP: {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$completed_at"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    results = await db.review_assignments.aggregate(pipeline).to_list(length=days)
    return {"timeline": results, "period_days": days}


@router.get("/analytics/domains")
async def get_review_domains(user: dict = Depends(require_reviewer)):
    """Get distribution of reviewed domains"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])

    pipeline = [
        {MONGO_MATCH: {"reviewer_id": reviewer_id}},
        {
            "$lookup": {
                "from": "submissions",
                "localField": "submission_id",
                "foreignField": "_id",
                "as": "submission_details",
            }
        },
        {
            MONGO_GROUP: {
                "_id": {"$ifNull": ["$submission_details.detected_domain", "Unknown"]},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    domains = await db.review_assignments.aggregate(pipeline).to_list(length=None)

    return {"domains": domains}


@router.get("/analytics/performance")
async def get_reviewer_performance(user: dict = Depends(require_reviewer)):
    """Get reviewer performance metrics"""
    db = await mongodb_service.get_database()
    reviewer_id = str(user["_id"])
    pipeline = [
        {
            MONGO_MATCH: {
                "reviewer_id": reviewer_id,
                "status": "completed",
                "completed_at": {MONGO_EXISTS: True},
                "started_at": {MONGO_EXISTS: True},
            }
        },
        {
            MONGO_GROUP: {
                "_id": None,
                "avg_time_ms": {"$avg": "$review_time"},
                "min_time_ms": {"$min": "$review_time"},
                "max_time_ms": {"$max": "$review_time"},
            }
        },
    ]

    result = await db.review_assignments.aggregate(pipeline).to_list(length=1)
    return {
        "performance": (
            result[0] if result else {"avg_time_ms": 0, "min_time_ms": 0, "max_time_ms": 0}
        )
    }
