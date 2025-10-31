from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SubmissionCreate(BaseModel):
    title: str
    content: str
    file_metadata: Dict[str, Any]


class Submission(BaseModel):
    id: str
    title: str
    content: str
    file_metadata: Dict[str, Any]
    final_report: Optional[str] = None
    created_at: datetime
    status: TaskStatus = TaskStatus.PENDING
