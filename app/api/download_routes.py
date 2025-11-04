"""File download routes with role-based permissions"""

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.middleware.dual_auth import get_current_user
from app.models.roles import Permission, has_permission
from app.services.mongodb_service import mongodb_service
from app.services.pdf_generator import pdf_generator
from app.utils.logger import get_logger

router = APIRouter(prefix="/downloads", tags=["downloads"])
logger = get_logger(__name__)


def _can_access_submission(user: dict, submission: dict) -> bool:
    """Check if user can access this submission"""
    user_role = user.get("role", "author")
    user_id = user.get("user_id")

    # Super admin and admin can access all
    if user_role in ["super_admin", "admin"]:
        return True

    # Editor can access all submissions
    if has_permission(user_role, Permission.VIEW_ALL_SUBMISSIONS):
        return True

    # Reviewer can access assigned submissions
    if user_role == "reviewer":
        # Check if reviewer is assigned to this submission
        # For now, allow reviewers to view all (can be restricted later)
        return True

    # Author can only access their own
    return submission.get("user_id") == user_id


@router.get("/manuscripts/{submission_id}")
async def download_original_manuscript(submission_id: str, user: dict = Depends(get_current_user)):
    """Download original uploaded manuscript

    Permissions:
    - Author: Own submissions only
    - Reviewer: Assigned submissions
    - Editor: All submissions
    - Admin/Super Admin: All submissions
    """
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Check permissions
        if not _can_access_submission(user, submission):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get original file content
        file_content = submission.get("original_file")
        if not file_content:
            raise HTTPException(status_code=404, detail="Original file not available")

        # Get file metadata
        metadata = submission.get("file_metadata", {})
        original_filename = metadata.get("original_filename", "manuscript.pdf")
        file_type = metadata.get("file_type", "pdf")

        # Determine media type
        media_type = (
            "application/pdf"
            if file_type == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # Create response
        file_buffer = io.BytesIO(file_content)
        file_buffer.seek(0)

        return StreamingResponse(
            file_buffer,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{original_filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            e, additional_info={"submission_id": submission_id, "user_id": user.get("user_id")}
        )
        raise HTTPException(status_code=500, detail="Failed to download manuscript")


@router.get("/reviews/{submission_id}")
async def download_review_pdf(submission_id: str, user: dict = Depends(get_current_user)):
    """Download processed review PDF

    Permissions:
    - Author: Own submissions only
    - Reviewer: Assigned submissions
    - Editor: All submissions
    - Admin/Super Admin: All submissions
    """
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Check permissions
        if not _can_access_submission(user, submission):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if review is completed
        if submission.get("status") != "completed":
            raise HTTPException(status_code=400, detail="Review not completed yet")

        # Generate PDF
        pdf_buffer = pdf_generator.generate_review_pdf(
            submission, submission.get("final_report", "")
        )

        # Ensure buffer is seekable
        if not hasattr(pdf_buffer, "seek"):
            pdf_bytes = (
                pdf_buffer.getvalue() if hasattr(pdf_buffer, "getvalue") else pdf_buffer.read()
            )
            pdf_buffer = io.BytesIO(pdf_bytes)

        pdf_buffer.seek(0)

        # Build filename
        original_filename = submission.get("file_metadata", {}).get(
            "original_filename", submission.get("title", "manuscript")
        )
        if "." in original_filename:
            base_name = original_filename.rsplit(".", 1)[0]
        else:
            base_name = original_filename

        safe_name = (
            "".join(c for c in base_name if c.isalnum() or c in (" ", "-", "_")).strip()
            or "manuscript"
        )
        filename = f"{safe_name}_reviewed.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            e, additional_info={"submission_id": submission_id, "user_id": user.get("user_id")}
        )
        raise HTTPException(status_code=500, detail="Failed to download review PDF")
