import asyncio
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.agents.orchestrator import orchestrator
from app.models.schemas import TaskStatus
from app.services.document_parser import document_parser
from app.services.mongodb_service import mongodb_service

router = APIRouter()


@router.post("/submissions/upload")
async def upload_manuscript(file: UploadFile = File(...)):
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
            "created_at": datetime.utcnow(),
        }

        submission_id = await mongodb_service.save_submission(submission_data)
        asyncio.create_task(orchestrator.process_submission(submission_id))

        return JSONResponse(
            {
                "submission_id": submission_id,
                "status": "processing",
                "message": "Manuscript uploaded successfully. Review process started.",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str):
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        return submission
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/submissions/{submission_id}/status")
async def get_submission_status(submission_id: str):
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

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


@router.get("/submissions/{submission_id}/report")
async def get_final_report(submission_id: str):
    try:
        submission = await mongodb_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

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
