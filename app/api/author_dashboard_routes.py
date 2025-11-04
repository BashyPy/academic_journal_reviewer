"""Author Dashboard API Routes"""

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.middleware.dual_auth import get_current_user
from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

router = APIRouter(prefix="/author", tags=["author-dashboard"])
logger = get_logger(__name__)


def require_author(user: dict = Depends(get_current_user)):
    """Require authenticated user (any role can be an author)"""
    return user


@router.get("/dashboard/stats")
async def get_author_stats(user: dict = Depends(require_author)):
    """Get author-specific statistics"""
    db = await mongodb_service.get_database()
    user_id = user.get("user_id")

    total = await db.submissions.count_documents({"user_id": user_id})
    completed = await db.submissions.count_documents({"user_id": user_id, "status": "completed"})
    processing = await db.submissions.count_documents({"user_id": user_id, "status": "processing"})
    failed = await db.submissions.count_documents({"user_id": user_id, "status": "failed"})

    return {
        "total_submissions": total,
        "completed_reviews": completed,
        "in_progress": processing,
        "failed_reviews": failed,
    }


@router.get("/submissions")
async def get_author_submissions(
    user: dict = Depends(require_author),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """Get author's submissions with pagination"""
    db = await mongodb_service.get_database()
    user_id = user.get("user_id")

    query = {"user_id": user_id}
    if status:
        query["status"] = status

    submissions = (
        await db.submissions.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total = await db.submissions.count_documents(query)

    for sub in submissions:
        sub["_id"] = str(sub["_id"])

    return {"submissions": submissions, "total": total, "skip": skip, "limit": limit}


@router.get("/submissions/{submission_id}")
async def get_submission_detail(submission_id: str, user: dict = Depends(require_author)):
    """Get detailed submission information"""
    db = await mongodb_service.get_database()
    user_id = user.get("user_id")

    submission = await db.submissions.find_one({"_id": ObjectId(submission_id), "user_id": user_id})

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


@router.get("/analytics/timeline")
async def get_submission_timeline(
    user: dict = Depends(require_author),
    days: int = Query(30, ge=7, le=365),
):
    """Get submission timeline analytics"""
    db = await mongodb_service.get_database()
    user_id = user.get("user_id")
    start_date = datetime.now() - timedelta(days=days)

    pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": start_date}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=days)
    return {"timeline": results, "period_days": days}


@router.get("/analytics/domains")
async def get_domain_distribution(user: dict = Depends(require_author)):
    """Get domain distribution for author's submissions"""
    db = await mongodb_service.get_database()
    user_id = user.get("user_id")

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$detected_domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=50)
    return {"domains": results}


@router.get("/analytics/performance")
async def get_review_performance(user: dict = Depends(require_author)):
    """Get average review processing time"""
    db = await mongodb_service.get_database()
    user_id = user.get("user_id")

    pipeline = [
        {"$match": {"user_id": user_id, "status": "completed", "completed_at": {"$exists": True}}},
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
    return {"performance": result[0] if result else {}}


@router.delete("/submissions/{submission_id}")
async def delete_submission(submission_id: str, user: dict = Depends(require_author)):
    """Delete author's own submission"""
    db = await mongodb_service.get_database()
    user_id = user.get("user_id")

    result = await db.submissions.delete_one({"_id": ObjectId(submission_id), "user_id": user_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")

    await db.agent_tasks.delete_many({"submission_id": submission_id})

    return {"message": "Submission deleted successfully"}
