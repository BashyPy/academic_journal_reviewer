"""Editor Dashboard API Routes"""

from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.middleware.dual_auth import get_current_user
from app.models.roles import UserRole
from app.services.audit_logger import audit_logger
from app.services.mongodb_service import mongodb_service
from app.utils.common_operations import (
    get_submission_analytics,
    reprocess_submission_common,
)
from app.utils.logger import get_logger
from app.utils.request_utils import get_client_ip

router = APIRouter(prefix="/editor", tags=["editor-dashboard"])
logger = get_logger(__name__)


def _process_submission(submission: dict) -> dict:
    """Process submission for API response."""
    submission["_id"] = str(submission["_id"])
    if "file_metadata" in submission and "file_data" in submission["file_metadata"]:
        del submission["file_metadata"]["file_data"]
    return submission


# MongoDB aggregation pipeline stages
MONGO_GROUP = "$group"
MONGO_MATCH = "$match"
MONGO_COUNT = "$count"
MONGO_SORT = "$sort"
MONGO_LIMIT = "$limit"
MONGO_PROJECT = "$project"
MONGO_FACET = "$facet"
MONGO_SUM = "$sum"
PROCESSING_TIME = "processing_time"


def require_editor(user: dict = Depends(get_current_user)):
    """Require editor role or higher"""
    role = user.get("role")
    if role not in [
        UserRole.EDITOR.value,
        UserRole.ADMIN.value,
        UserRole.SUPER_ADMIN.value,
    ]:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this resource."
        )
    return user


@router.get("/stats")
async def get_dashboard_stats(_editor: dict = Depends(require_editor)):
    """Get dashboard stats"""
    db = await mongodb_service.get_database()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    pipeline = [
        {
            "$facet": {
                "total_submissions": [{MONGO_COUNT: "count"}],
                "pending_review": [{MONGO_MATCH: {"status": "pending"}}, {MONGO_COUNT: "count"}],
                "in_review": [{MONGO_MATCH: {"status": "processing"}}, {MONGO_COUNT: "count"}],
                "completed": [{MONGO_MATCH: {"status": "completed"}}, {MONGO_COUNT: "count"}],
                "failed": [{MONGO_MATCH: {"status": "failed"}}, {MONGO_COUNT: "count"}],
                "today_submissions": [
                    {MONGO_MATCH: {"created_at": {"$gte": today_start}}},
                    {MONGO_COUNT: "count"},
                ],
                "this_week": [
                    {MONGO_MATCH: {"created_at": {"$gte": week_start}}},
                    {MONGO_COUNT: "count"},
                ],
            }
        }
    ]

    result = await db.submissions.aggregate(pipeline).to_list(length=1)

    if not result:
        return {
            "total_submissions": 0,
            "pending_review": 0,
            "in_review": 0,
            "completed": 0,
            "failed": 0,
            "today_submissions": 0,
            "this_week": 0,
        }

    counts = result[0]

    def get_count(field):
        return counts[field][0]["count"] if counts.get(field) and counts[field] else 0

    stats = {
        "total_submissions": get_count("total_submissions"),
        "pending_review": get_count("pending_review"),
        "in_review": get_count("in_review"),
        "completed": get_count("completed"),
        "failed": get_count("failed"),
        "today_submissions": get_count("today_submissions"),
        "this_week": get_count("this_week"),
    }

    return stats


@router.get("/submissions")
async def list_all_submissions(
    _editor: dict = Depends(require_editor),
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

    total = await db.submissions.count_documents(query)
    submissions = (
        await db.submissions.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )

    processed_submissions = [_process_submission(sub) for sub in submissions]

    return {"submissions": processed_submissions, "total": total}


@router.get("/submissions/{submission_id}")
async def get_submission_details(submission_id: str, _editor: dict = Depends(require_editor)):
    """Get detailed submission with review data"""
    db = await mongodb_service.get_database()
    try:
        obj_id = ObjectId(submission_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid submission ID format")

    submission = await db.submissions.find_one({"_id": obj_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission = _process_submission(submission)
    tasks = await db.agent_tasks.find({"submission_id": submission_id}).to_list(length=100)
    for task in tasks:
        task["_id"] = str(task["_id"])
    submission["agent_tasks"] = tasks
    submission["download_urls"] = {
        "manuscript": f"/api/v1/downloads/manuscripts/{submission_id}",
        "review": (
            f"/api/v1/downloads/reviews/{submission_id}"
            if submission.get("status") == "completed"
            else None
        ),
    }
    return submission


class EditorialDecision(BaseModel):
    """Model for editorial decision"""

    decision: str
    comments: Optional[str] = None


@router.post("/submissions/{submission_id}/decision")
async def make_editorial_decision(
    submission_id: str,
    decision: EditorialDecision,
    req: Request,
    editor: dict = Depends(require_editor),
):
    """Make editorial decision on submission"""
    db = await mongodb_service.get_database()

    try:
        obj_id = ObjectId(submission_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid submission ID format")

    submission = await db.submissions.find_one({"_id": obj_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    decision_data = {
        "decision": decision.decision,
        "comments": decision.comments,
        "editor_id": str(editor["_id"]),
        "editor_email": editor.get("email"),
        "decided_at": datetime.now(),
    }

    await db.submissions.update_one(
        {"_id": obj_id},
        {"$set": {"editorial_decision": decision_data, "updated_at": datetime.now()}},
    )

    await audit_logger.log_event(
        event_type="editorial_decision",
        user_id=str(editor["_id"]),
        user_email=editor.get("email"),
        ip_address=get_client_ip(req),
        details={"submission_id": submission_id, "decision": decision.decision},
        severity="info",
    )

    return {"message": "Editorial decision recorded", "decision": decision_data}


@router.get("/analytics/submissions")
async def get_submission_analytics_route(_editor: dict = Depends(require_editor)):
    """Get submission analytics"""
    return await get_submission_analytics()


@router.get("/analytics/domain-distribution")
async def get_domain_distribution(_editor: dict = Depends(require_editor)):
    """Get domain distribution"""
    db = await mongodb_service.get_database()
    pipeline = [
        {MONGO_GROUP: {"_id": "$detected_domain", "count": {"$sum": 1}}},
        {MONGO_SORT: {"count": -1}},
        {"$limit": 20},
    ]
    results = await db.submissions.aggregate(pipeline).to_list(length=20)
    return results


@router.get("/analytics/performance")
async def get_performance_analytics(_editor: dict = Depends(require_editor)):
    db = await mongodb_service.get_database()

    pipeline = [
        {MONGO_MATCH: {"status": "completed", "completed_at": {"$exists": True}}},
        {"$project": {PROCESSING_TIME: {"$subtract": ["$completed_at", "$created_at"]}}},
        {
            MONGO_GROUP: {
                "_id": None,
                "avg_time_ms": {"$avg": f"${PROCESSING_TIME}"},
                "min_time_ms": {"$min": f"${PROCESSING_TIME}"},
                "max_time_ms": {"$max": f"${PROCESSING_TIME}"},
                "total_reviews": {"$sum": 1},
            }
        },
    ]

    result = await db.submissions.aggregate(pipeline).to_list(length=1)
    return {
        "performance": (
            result[0]
            if result
            else {
                "avg_time_ms": 0,
                "min_time_ms": 0,
                "max_time_ms": 0,
                "total_reviews": 0,
            }
        ),
    }


@router.get("/analytics/status-breakdown")
async def get_status_breakdown(_editor: dict = Depends(require_editor)):
    """Get submission status breakdown"""
    db = await mongodb_service.get_database()

    pipeline = [
        {MONGO_GROUP: {"_id": "$status", "count": {"$sum": 1}}},
        {MONGO_SORT: {"count": -1}},
    ]

    results = await db.submissions.aggregate(pipeline).to_list(length=10)
    return results


@router.get("/recent-activity")
async def get_recent_activity(
    _editor: dict = Depends(require_editor), limit: int = Query(10, ge=1, le=50)
):
    """Get recent editorial activity"""
    db = await mongodb_service.get_database()

    submissions = (
        await db.submissions.find({"editorial_decision": {"$exists": True}})
        .sort("editorial_decision.decided_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )

    processed_submissions = [_process_submission(sub) for sub in submissions]

    return {"recent_activity": processed_submissions}


@router.post("/submissions/{submission_id}/reprocess")
async def reprocess_submission(
    submission_id: str, req: Request, editor: dict = Depends(require_editor)
):
    """Reprocess a failed submission"""
    return await reprocess_submission_common(submission_id, editor, req)
