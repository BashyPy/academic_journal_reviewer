"""Author Dashboard API Routes"""

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.middleware.dual_auth import get_current_user
from app.services.mongodb_service import mongodb_service
from app.utils.common_operations import (
    get_performance_metrics,
    get_submission_with_downloads,
)
from app.utils.logger import get_logger

router = APIRouter(prefix="/author", tags=["author-dashboard"])
logger = get_logger(__name__)


PROCESSING_TIME = "$processing_time"
MONGO_SORT = "$sort"
MONGO_GROUP = "$group"
MONGO_MATCH = "$match"


def require_author(user: dict = Depends(get_current_user)):
    """Require authenticated user (any role can be an author)"""
    return user


@router.get("/dashboard/stats")
async def get_author_stats(user: dict = Depends(require_author)):
    """Get author-specific statistics"""
    db = await mongodb_service.get_database()
    user_id = str(user["_id"])

    pipeline = [
        {MONGO_MATCH: {"user_id": user_id}},
        {
            MONGO_GROUP: {
                "_id": "$status",
                "count": {"$sum": 1},
            }
        },
    ]
    results = await db.submissions.aggregate(pipeline).to_list(length=None)

    stats = {"completed": 0, "processing": 0, "failed": 0}
    total = 0
    for res in results:
        status = res["_id"]
        count = res["count"]
        if status in stats:
            stats[status] = count
        total += count

    return {
        "total_submissions": total,
        "completed_reviews": stats["completed"],
        "in_progress": stats["processing"],
        "failed_reviews": stats["failed"],
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
    user_id = str(user["_id"])

    query = {"user_id": user_id}
    if status:
        query["status"] = status

    submissions = (
        await db.submissions.find(query, {"file_data": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total = await db.submissions.count_documents(query)

    for sub in submissions:
        sub["_id"] = str(sub["_id"])
        if "file_metadata" in sub and "file_data" in sub["file_metadata"]:
            del sub["file_metadata"]["file_data"]

    return {"submissions": submissions, "total": total, "skip": skip, "limit": limit}


@router.get("/submissions/{submission_id}")
async def get_submission_detail(submission_id: str, user: dict = Depends(require_author)):
    """Get detailed submission information"""
    if not submission_id or not submission_id.strip():
        raise HTTPException(status_code=400, detail="Invalid submission ID")
    try:
        obj_id = ObjectId(submission_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid submission ID format")

    db = await mongodb_service.get_database()
    db = await mongodb_service.get_database()
    user_id = str(user["_id"])
    submission = await db.submissions.find_one({"_id": obj_id, "user_id": user_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return await get_submission_with_downloads(submission_id)


@router.get("/analytics/timeline")
async def get_submission_timeline(
    user: dict = Depends(require_author),
    days: int = Query(30, ge=7, le=365),
):
    """Get submission timeline analytics"""
    try:
        db = await mongodb_service.get_database()
        user_id = str(user["_id"])
        start_date = datetime.now() - timedelta(days=days)

        pipeline = [
            {MONGO_MATCH: {"user_id": user_id, "created_at": {"$gte": start_date}}},
            {
                MONGO_GROUP: {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1},
                    "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                }
            },
            {MONGO_SORT: {"_id": 1}},
        ]

        results = await db.submissions.aggregate(pipeline).to_list(length=days)
        return {"timeline": results, "period_days": days}
    except Exception as e:
        logger.error(f"Error fetching submission timeline for user {user.get('_id')}", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch submission timeline.")


@router.get("/analytics/domains")
async def get_domain_distribution(user: dict = Depends(require_author)):
    """Get domain distribution for author's submissions"""
    try:
        db = await mongodb_service.get_database()
        user_id = str(user["_id"])

        pipeline = [
            {MONGO_MATCH: {"user_id": user_id}},
            {MONGO_GROUP: {"_id": "$detected_domain", "count": {"$sum": 1}}},
            {MONGO_SORT: {"count": -1}},
        ]

        results = await db.submissions.aggregate(pipeline).to_list(length=50)
        return {"domains": results}
    except Exception as e:
        logger.error(f"Error fetching domain distribution for user {user.get('_id')}", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch domain distribution.")


@router.get("/analytics/performance")
async def get_review_performance(user: dict = Depends(require_author)):
    """Get average review processing time"""
    try:
        return await get_performance_metrics(str(user["_id"]))
    except Exception as e:
        logger.error(f"Error fetching review performance for user {user.get('_id')}", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to fetch review performance.")


@router.delete("/submissions/{submission_id}")
async def delete_submission(submission_id: str, user: dict = Depends(require_author)):
    """Delete author's own submission"""
    if not submission_id or not submission_id.strip():
        raise HTTPException(status_code=400, detail="Invalid submission ID")
    try:
        db = await mongodb_service.get_database()
        user_id = str(user["_id"])

        obj_id = ObjectId(submission_id)

        # First, verify the submission exists and belongs to the user
        submission = await db.submissions.find_one({"_id": obj_id, "user_id": user_id})
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found or not owned by user")

        # If found, proceed with deletion
        await db.submissions.delete_one({"_id": obj_id})
        await db.agent_tasks.delete_many({"submission_id": submission_id})

        return {"message": "Submission deleted successfully"}
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid submission ID format")
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTPException to avoid being caught by the generic one
    except Exception as e:
        logger.error(
            f"Error deleting submission {submission_id} for user {user.get('_id')}", exc_info=e
        )
        raise HTTPException(status_code=500, detail="Failed to delete submission.")
