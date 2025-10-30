from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    METHODOLOGY = "methodology"
    LITERATURE = "literature"
    CLARITY = "clarity"
    ETHICS = "ethics"
    SYNTHESIS = "synthesis"


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


class AgentTask(BaseModel):
    id: Optional[str] = None
    agent_type: AgentType
    submission_id: str
    status: TaskStatus = TaskStatus.PENDING
    context: Optional[Dict[str, Any]] = None
    critique: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class TextHighlight(BaseModel):
    text: str
    start_pos: int
    end_pos: int
    context: str
    issue_type: str


class DetailedFinding(BaseModel):
    finding: str
    highlights: List[TextHighlight]
    severity: str  # "minor", "moderate", "major"
    category: str


class AgentCritique(BaseModel):
    agent_type: AgentType
    score: float
    findings: List[DetailedFinding]
    recommendations: List[str]
    confidence: float
    bias_check: str
