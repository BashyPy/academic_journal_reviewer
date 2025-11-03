"""Editor Dashboard API Routes"""

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.middleware.dual_auth import get_current_user
from app.models.roles import UserRole, Permission, has_permission
from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

router = APIRouter(prefix="/editor", tags=["editor-dashboard"])
logger = get_logger(__name__)


def require_editor(user: dict = Depends(get_current_user)):
    """Require editor role or higher"""
    role = user.get("role")
    if role not in [UserRole.EDITOR.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Editor access required")
    return user


@router.get("/dashboard/stats")
async def get_editor_stats(editor: dict = Depends(require_editor)):
    """Get editor dashboard statistics"""
    db = await mongodb_service.get_database()
    
    stats = {
        "total_submissions": await db.submissions.count_documents({}),
        "pending_review": await db.submissions.count_documents({"status": "pending"}),
        "in_review": await db.submissions.count_documents({"status": "processing"}),
        "completed": await db.submissions.count_documents({"status": "completed"}),
        "failed": await db.submissions.count_documents({"status": "failed"}),
        "today_submissions": await db.submissions.count_documents({
            "created_at": {"$gte": datetime.now().replace(hour=0, minute=0, second=0)}
        }),
        "this_week": await db.submissions.count_documents({
            "created_at": {"$gte": datetime.now() - timedelta(days=7)}
        }),
    }
    
    return stats


@router.get("/submissions")
async def list_all_submissions(
    editor: dict = Depends(require_editor),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    domain: Optional[str] = None,
):
    """List all submissions with filtering"""
    db = await mongodb_service.get_database()
    
    query = {}
    if status:
        query["status"] = status
    if domain:
        query["detected_domain"] = domain
    
    submissions = await db.submissions.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    total = await db.submissions.count_documents(query)
    
    for sub in submissions:
        sub["_id"] = str(sub["_id"])
    
    return {"submissions": submissions, "total": total, "skip": skip, "limit": limit}


@router.get("/submissions/{submission_id}")
async def get_submission_details(submission_id: str, editor: dict = Depends(require_editor)):
    """Get detailed submission with review data"""
    db = await mongodb_service.get_database()
    
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission["_id"] = str(submission["_id"])
    
    # Get agent tasks
    tasks = await db.agent_tasks.find({"submission_id": submission_id}).to_list(length=100)
    for task in tasks:
        task["_id"] = str(task["_id"])
    
    submission["agent_tasks"] = tasks
    
    # Add download URLs
    submission["download_urls"] = {
        "manuscript": f"/api/v1/downloads/manuscripts/{submission_id}",
        "review": f"/api/v1/downloads/reviews/{submission_id}" if submission.get("status") == "completed" else None
    }
    
    return submission


class EditorialDecision(BaseModel):
    decision: str  # accept, reject, revise
    comments: str
    notify_author: bool = True


@router.post("/submissions/{submission_id}/decision")
async def make_editorial_decision(
    submission_id: str,
    decision: EditorialDecision,
    editor: dict = Depends(require_editor),
):
    """Make editorial decision on submission"""
    db = await mongodb_service.get_database()
    
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    decision_data = {
        "decision": decision.decision,
        "comments": decision.comments,
        "editor_id": editor.get("user_id"),
        "editor_email": editor.get("email"),
        "decided_at": datetime.now(),
    }
    
    await db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": {"editorial_decision": decision_data, "updated_at": datetime.now()}},
    )
    
    await audit_logger.log_event(
        event_type="editorial_decision",
        user_id=editor.get("user_id"),
        details={"submission_id": submission_id, "decision": decision.decision},
        severity="info",
    )
    
    return {"message": "Editorial decision recorded", "decision": decision_data}


@router.get("/analytics/submissions")
async def get_submission_analytics(
    editor: dict = Depends(require_editor),
    days: int = Query(30, ge=1, le=365),
):
    """Get submission analytics over time"""
    db = await mongodb_service.get_database()
    start_date = datetime.now() - timedelta(days=days)
    
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    
    results = await db.submissions.aggregate(pipeline).to_list(length=days)
    return {"analytics": results, "period_days": days}


@router.get("/analytics/domains")
async def get_domain_distribution(editor: dict = Depends(require_editor)):
    """Get domain distribution"""
    db = await mongodb_service.get_database()
    
    pipeline = [
        {"$group": {"_id": "$detected_domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    
    results = await db.submissions.aggregate(pipeline).to_list(length=20)
    return {"domains": results}


@router.get("/analytics/performance")
async def get_review_performance(editor: dict = Depends(require_editor)):
    """Get review processing performance metrics"""
    db = await mongodb_service.get_database()
    
    pipeline = [
        {"$match": {"status": "completed", "completed_at": {"$exists": True}}},
        {
            "$project": {
                "processing_time": {"$subtract": ["$completed_at", "$created_at"]}
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_time_ms": {"$avg": "$processing_time"},
                "min_time_ms": {"$min": "$processing_time"},
                "max_time_ms": {"$max": "$processing_time"},
                "total_reviews": {"$sum": 1},
            }
        },
    ]
    
    result = await db.submissions.aggregate(pipeline).to_list(length=1)
    return {"performance": result[0] if result else {}}


@router.get("/analytics/status-breakdown")
async def get_status_breakdown(editor: dict = Depends(require_editor)):
    """Get submission status breakdown"""
    db = await mongodb_service.get_database()
    
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    
    results = await db.submissions.aggregate(pipeline).to_list(length=10)
    return {"status_breakdown": results}


@router.get("/recent-activity")
async def get_recent_activity(
    editor: dict = Depends(require_editor),
    limit: int = Query(20, ge=1, le=50),
):
    """Get recent editorial activity"""
    db = await mongodb_service.get_database()
    
    submissions = await db.submissions.find().sort("updated_at", -1).limit(limit).to_list(length=limit)
    
    for sub in submissions:
        sub["_id"] = str(sub["_id"])
    
    return {"recent_activity": submissions}


@router.post("/submissions/{submission_id}/reprocess")
async def reprocess_submission(submission_id: str, editor: dict = Depends(require_editor)):
    """Reprocess a failed submission"""
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
        user_id=editor.get("user_id"),
        details={"submission_id": submission_id},
        severity="info",
    )
    
    return {"message": "Submission queued for reprocessing"}
