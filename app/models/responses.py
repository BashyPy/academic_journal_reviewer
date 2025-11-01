from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response after an upload is accepted."""

    submission_id: str
    status: str
    message: str

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    """Status of an asynchronous task/agent."""

    agent_type: str
    status: str

    class Config:
        from_attributes = True


class StatusResponse(BaseModel):
    """Overall submission status including individual task statuses."""

    submission_id: str
    status: str
    tasks: List[TaskResponse]

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    """Represents a submission returned by the API."""

    submission_id: str
    title: str
    content: str
    file_metadata: Dict[str, Any]
    status: str
    final_report: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    """Final report for a submission."""

    submission_id: str
    title: str
    final_report: str
    completed_at: Optional[datetime] = None
    disclaimer: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True
