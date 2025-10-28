import asyncio
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import orchestrator
from app.models.responses import (
    ReportResponse,
    StatusResponse,
    SubmissionResponse,
    UploadResponse,
)
from app.models.schemas import TaskStatus
from app.services.document_parser import document_parser
from app.services.mongodb_service import mongodb_service
from app.services.pdf_generator import pdf_generator

router = APIRouter()

SUBMISSION_NOT_FOUND = "Submission not found"


@router.post(
    "/submissions/upload",
    response_model=UploadResponse,
    summary="Upload Manuscript",
    description="Upload a manuscript (PDF/DOCX) for AI-powered academic review. Initiates multi-agent analysis.",
)
async def upload_manuscript(
    file: UploadFile = File(
        description="Academic manuscript file (PDF or DOCX format)"
    ),
):
    """
    Upload a manuscript for AI-powered academic review.
    
    Accepts PDF or DOCX files and initiates the multi-agent review process.
    The document is parsed, stored in MongoDB, and the orchestrator agent
    coordinates specialist agents to perform comprehensive analysis.
    
    Args:
        file: Academic manuscript file (PDF or DOCX format)
        
    Example Request:
        curl -X POST "http://localhost:8000/api/v1/submissions/upload" \
             -H "Content-Type: multipart/form-data" \
             -F "file=@research_paper.pdf"
        
    Returns:
        JSONResponse: Contains submission ID and processing status
        
    Example Response:
        {
            "submission_id": "507f1f77bcf86cd799439011",
            "status": "processing",
            "message": "Manuscript uploaded successfully. Review process started."
        }
        
    Raises:
        HTTPException: 500 if file parsing or processing fails
    """
    try:
        content = await file.read()
        parsed_data = document_parser.parse_document(content, file.filename)

        submission_data = {
            "title": file.filename,
            "content": parsed_data["content"],
            "file_metadata": {
                **parsed_data["metadata"],
                "original_filename": file.filename,
                "file_size": len(content),
            },
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(),
        }

        submission_id = await mongodb_service.save_submission(submission_data)
        asyncio.create_task(orchestrator.process_submission(submission_id))

        return {
            "submission_id": submission_id,
            "status": "processing",
            "message": "Manuscript uploaded successfully. Review process started.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get Submission",
    description="Retrieve complete submission details including content, metadata, and status.",
)
async def get_submission(submission_id: str):
    """
    Retrieve complete submission details by ID.

    Returns the full submission record including manuscript content,
    metadata, current status, and final report if completed.

    Args:
        submission_id: Unique identifier for the submission

    Example Request:
        GET /api/v1/submissions/507f1f77bcf86cd799439011

    Returns:
        dict: Complete submission data

    Example Response:
        {
            "id": "507f1f77bcf86cd799439011",
            "title": "research_paper.pdf",
            "content": "Abstract: This paper presents...",
            "file_metadata": {
                "pages": 12,
                "file_type": "pdf",
                "original_filename": "research_paper.pdf",
                "file_size": 2048576
            },
            "status": "completed",
            "final_report": "# Executive Summary...",
            "created_at": "2024-01-15T10:30:00Z"
        }

    Raises:
        HTTPException: 404 if submission not found, 500 for server errors
    """
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail=SUBMISSION_NOT_FOUND)
        return submission
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/submissions/{submission_id}/status",
    response_model=StatusResponse,
    summary="Get Review Status",
    description="Get real-time progress of specialist agents (Methodology, Literature, Clarity, Ethics).",
)
async def get_submission_status(submission_id: str):
    """
    Get real-time review progress status.

    Returns the current status of the submission and progress of each
    specialist agent (Methodology, Literature, Clarity, Ethics).
    Useful for tracking review progress in real-time.

    Args:
        submission_id: Unique identifier for the submission

    Example Request:
        GET /api/v1/submissions/507f1f77bcf86cd799439011/status

    Returns:
        dict: Status summary with agent task progress

    Example Response:
        {
            "submission_id": "507f1f77bcf86cd799439011",
            "status": "pending",
            "tasks": [
                {"agent_type": "methodology", "status": "completed"},
                {"agent_type": "literature", "status": "running"},
                {"agent_type": "clarity", "status": "pending"},
                {"agent_type": "ethics", "status": "pending"}
            ]
        }

    Raises:
        HTTPException: 404 if submission not found, 500 for server errors
    """
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail=SUBMISSION_NOT_FOUND)

        tasks = await mongodb_service.get_agent_tasks(submission_id)

        return {
            "submission_id": submission_id,
            "status": submission["status"],
            "tasks": [
                {"agent_type": task["agent_type"], "status": task["status"]}
                for task in tasks
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/submissions/{submission_id}/report",
    response_model=ReportResponse,
    summary="Get Final Report",
    description="Retrieve the synthesized review report with scores and recommendations.",
)
async def get_final_report(submission_id: str):
    """
    Retrieve the final comprehensive review report.

    Returns the synthesized review report compiled from all specialist
    agents' analyses. Only available after review completion.

    Args:
        submission_id: Unique identifier for the submission

    Example Request:
        GET /api/v1/submissions/507f1f77bcf86cd799439011/report

    Returns:
        dict: Final report with recommendations and scores

    Example Response:
        {
            "submission_id": "507f1f77bcf86cd799439011",
            "title": "research_paper.pdf",
            "final_report": "# Executive Summary\n\nOverall Score: 7.2/10\n\n## Methodology Analysis\nScore: 8/10\nStrengths: Well-designed experiment...\n\n## Recommendations\n- Improve statistical analysis\n- Expand literature review",
            "completed_at": "2024-01-15T11:45:00Z"
        }

    Raises:
        HTTPException: 404 if submission not found,
                      400 if review not completed,
                      500 for server errors
    """
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail=SUBMISSION_NOT_FOUND)

        if submission["status"] != TaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Review not completed yet")

        return {
            "submission_id": submission_id,
            "title": submission["title"],
            "final_report": submission["final_report"],
            "completed_at": submission.get("completed_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/submissions/{submission_id}/download",
    summary="Download PDF Report",
    description="Download the final review report as a professional PDF document.",
)
async def download_report_pdf(submission_id: str):
    """
    Download the final review report as a professional PDF.

    Generates and returns a professionally formatted PDF document
    containing the complete review report with proper styling,
    headers, and manuscript information.

    Args:
        submission_id: Unique identifier for the submission

    Returns:
        StreamingResponse: PDF file download

    Raises:
        HTTPException: 404 if submission not found,
                      400 if review not completed,
                      500 for server errors
    """
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail=SUBMISSION_NOT_FOUND)

        if submission["status"] != TaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Review not completed yet")

        pdf_buffer = pdf_generator.generate_review_pdf(
            submission, submission["final_report"]
        )

        filename = f"review_report_{submission_id[:8]}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
