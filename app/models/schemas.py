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


class TextHighlight(BaseModel):
    text: str
    start: int
    end: int
    context: Optional[str] = None


class DetailedFinding(BaseModel):
    issue: str
    severity: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    highlights: Optional[list[TextHighlight]] = None


class AgentCritique(BaseModel):
    agent_type: str
    score: float
    summary: str
    findings: list[DetailedFinding]
    strengths: list[str]
    weaknesses: list[str]
