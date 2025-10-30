import asyncio
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import orchestrator
from app.models.responses import (
    ReportResponse,
    StatusResponse,
    SubmissionResponse,
    UploadResponse,
)
from app.models.schemas import TaskStatus
from app.services.disclaimer_service import disclaimer_service
from app.services.document_parser import document_parser
from app.services.mongodb_service import mongodb_service
from app.services.pdf_generator import pdf_generator
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger()

PDF_MEDIA_TYPE = "application/pdf"
DOCX_EXTENSION = ".docx"

SUBMISSION_NOT_FOUND = "Submission not found"

INVALID_SUBMISSION_ID = "Invalid submission ID"

INVALID_FILENAME = "Invalid filename"


def _content_matches_extension(data: bytes, extension: str) -> bool:
    if extension == ".pdf":
        if data[:4] == b"%PDF":
            return True
        return b"%PDF" in data[:1024]
    if extension == DOCX_EXTENSION:
        try:
            bio = io.BytesIO(data)
            if zipfile.is_zipfile(bio):
                with zipfile.ZipFile(bio) as zf:
                    names = zf.namelist()
                    return (
                        any(n.startswith("word/") for n in names)
                        or "[Content_Types].xml" in names
                    )
        except Exception:
            return False
    return False
    return False


def _sanitize_and_validate_filename(raw_filename: str):
    if not raw_filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if "/" in raw_filename or "\\" in raw_filename or "\x00" in raw_filename:
        raise HTTPException(status_code=400, detail=INVALID_FILENAME)

    basename = Path(raw_filename).name
    if not basename or basename in (".", ".."):
        raise HTTPException(status_code=400, detail=INVALID_FILENAME)
    if len(basename) > 255:
        raise HTTPException(status_code=400, detail="Filename too long")

    p = Path(basename)
    name_part = p.stem
    ext = p.suffix.lower()
    safe_name_part = "".join(
        c for c in name_part if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    if not safe_name_part:
        raise HTTPException(status_code=400, detail=INVALID_FILENAME)
    safe_filename = f"{safe_name_part}{ext}"
    if not safe_filename or safe_filename in (".", ".."):
        raise HTTPException(status_code=400, detail=INVALID_FILENAME)

    allowed_extensions = {".pdf", ".docx"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only {', '.join(sorted(allowed_extensions))} files are allowed",
        )
    return safe_filename, ext, basename


async def _read_and_validate_content(
    upload_file: UploadFile, ext: str, raw_filename: str
):
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    try:
        content = await upload_file.read()
    except Exception as e:
        logger.error(
            e,
            additional_info={"filename": raw_filename, "endpoint": "upload_manuscript"},
        )
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")

    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail="File too large. Maximum size is 50MB"
        )

    content_type = (getattr(upload_file, "content_type", "") or "").lower()
    if (
        ext == ".pdf"
        and "pdf" not in content_type
        and content_type not in ("", "application/octet-stream")
    ):
        logger.warning(
            "PDF uploaded with unexpected content-type",
            additional_info={"content_type": content_type, "filename": raw_filename},
        )

    if (
        ext == DOCX_EXTENSION
        and "word" not in content_type
        and "officedocument" not in content_type
        and content_type not in ("", "application/octet-stream")
    ):
        logger.warning(
            "DOCX uploaded with unexpected content-type",
            additional_info={"content_type": content_type, "filename": raw_filename},
        )

    if not _content_matches_extension(content, ext):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file content does not match the file extension",
        )

    return content, content_type


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
    x_timezone: str = Header(
        default="UTC",
        description="Client timezone (e.g., 'America/New_York', 'Europe/London')",
    ),
):
    """Accept an uploaded manuscript, validate it, parse, store and start background review."""
    try:
        # Basic presence check and sanitize filename
        if not file or not getattr(file, "filename", None):
            raise HTTPException(status_code=400, detail="No file provided")
        raw_filename = file.filename
        safe_filename, ext, _ = _sanitize_and_validate_filename(raw_filename)

        content, content_type = await _read_and_validate_content(
            file, ext, raw_filename
        )

        logger.info(
            f"Manuscript upload started: {safe_filename}",
            additional_info={
                "filename": safe_filename,
                "content_type": content_type,
                "file_size": len(content),
            },
        )

        parsed_data = document_parser.parse_document(content, safe_filename)

        submission_data = {
            "title": safe_filename,
            "content": parsed_data.get("content", ""),
            "file_metadata": {
                **parsed_data.get("metadata", {}),
                "original_filename": safe_filename,
                "file_size": len(content),
            },
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc),
        }

        submission_id = await mongodb_service.save_submission(submission_data)

        # Log the completed upload step (best-effort)
        try:
            logger.log_review_process(
                submission_id=submission_id,
                stage="upload_completed",
                status="success",
                additional_info={
                    "filename": safe_filename,
                    "file_size": len(content),
                    "content_length": len(parsed_data.get("content", "")),
                },
            )
        except Exception:
            logger.warning(
                "Failed to write structured review process log",
                additional_info={
                    "submission_id": submission_id,
                },
            )

        # Kick off background processing without blocking
        task = asyncio.create_task(
            orchestrator.process_submission(submission_id, x_timezone)
        )
        task.add_done_callback(lambda t: None)

        return {
            "submission_id": submission_id,
            "status": "processing",
            "message": "Manuscript uploaded successfully. Review process started.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            e,
            additional_info={
                "filename": getattr(file, "filename", "unknown"),
                "endpoint": "upload_manuscript",
            },
        )
        raise HTTPException(
            status_code=500, detail="Failed to process manuscript upload"
        )


def _convert_field_with_logging(
    submission: dict, field_name: str, submission_id: str, tz_string: str
):
    """Helper to convert a datetime field in submission and log results safely."""
    if field_name not in submission:
        return

    original = submission.get(field_name)
    try:
        converted = _convert_to_timezone(original, tz_string)
        submission[field_name] = converted
        logger.info(
            f"Converted {field_name} to client timezone",
            additional_info={
                "submission_id": submission_id,
                f"original_{field_name}": (
                    original.isoformat()
                    if isinstance(original, datetime)
                    else str(original)
                ),
                f"converted_{field_name}": (
                    converted.isoformat()
                    if isinstance(converted, datetime)
                    else str(converted)
                ),
                "timezone": tz_string,
            },
        )
    except Exception as e:
        logger.warning(
            f"Failed to convert {field_name} for timezone {tz_string}: {e}",
            additional_info={"submission_id": submission_id},
        )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get Submission",
    description="Retrieve complete submission details including content, metadata, and status.",
)
async def get_submission(
    submission_id: str,
    x_timezone: str = Header(
        default="UTC",
        description="Client timezone (e.g., 'America/New_York', 'Europe/London')",
    ),
):
    # Validate submission_id format
    if not submission_id or len(submission_id.strip()) == 0:
        raise HTTPException(status_code=400, detail=INVALID_SUBMISSION_ID)

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

        # Use helper to convert timestamp fields and centralize logging/error handling
        _convert_field_with_logging(submission, "created_at", submission_id, x_timezone)
        _convert_field_with_logging(
            submission, "completed_at", submission_id, x_timezone
        )

        return submission
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, additional_info={"submission_id": submission_id})
        raise HTTPException(status_code=500, detail="Failed to retrieve submission")


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
    # Validate submission_id format
    if not submission_id or len(submission_id.strip()) == 0:
        raise HTTPException(status_code=400, detail=INVALID_SUBMISSION_ID)
    try:
        logger.info(f"Status request for submission: {submission_id}")

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, additional_info={"submission_id": submission_id})
        raise HTTPException(
            status_code=500, detail="Failed to retrieve submission status"
        )


@router.get(
    "/submissions/{submission_id}/report",
    response_model=ReportResponse,
    summary="Get Final Report",
    description="Retrieve the synthesized review report with scores and recommendations.",
)
async def get_final_report(
    submission_id: str,
    x_timezone: str = Header(default="UTC", description="Display timezone"),
):
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
    # Validate submission_id format
    if not submission_id or len(submission_id.strip()) == 0:
        raise HTTPException(status_code=400, detail=INVALID_SUBMISSION_ID)
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail=SUBMISSION_NOT_FOUND)

        if submission["status"] != TaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Review not completed yet")

        # Use helpers to keep this function concise and reduce cognitive complexity
        disclaimer_info = _get_disclaimer_safe(submission_id)
        completed_at_iso = _parse_and_convert_completed_at(
            submission.get("completed_at"), x_timezone, submission_id
        )

        return {
            "submission_id": submission_id,
            "title": submission["title"],
            "final_report": submission.get("final_report", ""),
            "completed_at": completed_at_iso,
            "status": submission["status"],
            "disclaimer": disclaimer_info.get("disclaimer", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, additional_info={"submission_id": submission_id})
        raise HTTPException(status_code=500, detail="Failed to retrieve final report")


def _get_disclaimer_safe(submission_id: str) -> dict:
    """Retrieve disclaimer info without raising; returns an empty dict on failure."""
    try:
        return disclaimer_service.get_api_disclaimer() or {}
    except Exception as e:
        logger.warning(
            f"Failed to retrieve disclaimer: {e}",
            additional_info={"submission_id": submission_id},
        )
        return {}


def _parse_and_convert_completed_at(
    completed_at_raw, x_timezone: str, submission_id: str
):
    """Parse various completed_at formats and convert to the target timezone, returning an ISO string or None."""
    if not completed_at_raw:
        return None

    try:
        # Accept both ISO strings and datetime objects
        if isinstance(completed_at_raw, str):
            s = completed_at_raw
            # Support trailing 'Z' UTC indicator
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            completed_dt = datetime.fromisoformat(s)
        elif isinstance(completed_at_raw, datetime):
            completed_dt = completed_at_raw
        else:
            raise ValueError(f"Unsupported completed_at type: {type(completed_at_raw)}")

        # Ensure timezone-aware and convert
        completed_dt = _convert_to_timezone(completed_dt, x_timezone)
        return completed_dt.isoformat()
    except Exception as e:
        logger.warning(
            f"Failed to parse/convert completed_at: {e}",
            additional_info={"submission_id": submission_id},
        )
        return None


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
    # Validate submission_id format
    if not submission_id or len(submission_id.strip()) == 0:
        raise HTTPException(status_code=400, detail=INVALID_SUBMISSION_ID)

    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail=SUBMISSION_NOT_FOUND)

        if submission["status"] != TaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Review not completed yet")

        # Generate PDF from the review content
        pdf_buffer = pdf_generator.generate_review_pdf(
            submission, submission["final_report"]
        )

        # Create safe filename using {file_name}_reviewed format
        original_filename = submission.get("file_metadata", {}).get(
            "original_filename", submission.get("title", "manuscript")
        )
        # Remove extension if present
        if "." in original_filename:
            base_name = original_filename.rsplit(".", 1)[0]
        else:
            base_name = original_filename
        # Build a safe filename keeping alphanumeric, spaces, hyphens and underscores
        safe_chars = []
        for c in base_name:
            if c.isalnum() or c in (" ", "-", "_"):
                safe_chars.append(c)
        safe_name = "".join(safe_chars).rstrip() or "manuscript"
        filename = f"{safe_name}_reviewed.pdf"

        # Ensure buffer is at start and stream it directly (avoids creating extra copies)
        try:
            pdf_buffer.seek(0)
        except Exception:
            # Fallback: recreate a BytesIO from the bytes
            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer = io.BytesIO(pdf_bytes)
            pdf_buffer.seek(0)

        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

        return StreamingResponse(
            pdf_buffer,
            media_type=PDF_MEDIA_TYPE,
            headers=headers,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, additional_info={"submission_id": submission_id})
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")


def _convert_to_timezone(dt: datetime, tz_string: str) -> datetime:
    """Convert datetime to specified timezone for display.

    Args:
        dt: Datetime object to convert
        tz_string: Target timezone string (IANA format)

    Returns:
        Converted datetime object or original if conversion fails
    """
    if not dt:
        return dt

    # Ensure datetime is timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    try:
        target_tz = ZoneInfo(tz_string)
        return dt.astimezone(target_tz)
    except (ValueError, KeyError, OSError) as e:
        logger.warning(f"Failed to convert timezone {tz_string}: {e}")
        return dt  # Return original if conversion fails
