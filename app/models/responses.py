from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    submission_id: str
    status: str
    message: str


class TaskResponse(BaseModel):
    agent_type: str
    status: str


class StatusResponse(BaseModel):
    submission_id: str
    status: str
    tasks: List[TaskResponse]


class SubmissionResponse(BaseModel):
    id: str
    title: str
    content: str
    file_metadata: Dict[str, Any]
    status: str
    final_report: Optional[str] = None
    created_at: datetime


class ReportResponse(BaseModel):
    submission_id: str
    title: str
    final_report: str
    completed_at: datetime
