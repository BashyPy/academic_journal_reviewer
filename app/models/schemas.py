from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator


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


class TextHighlight(BaseModel):
    text: str
    start: int
    end: int
    context: Optional[str] = None

    @field_validator("start")
    def start_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("start must be a non-negative integer")
        return v

    @field_validator("end")
    def end_must_be_greater_than_start(cls, v: int, values: Dict[str, Any]) -> int:
        if "start" in values and v < values["start"]:
            raise ValueError("end must be greater than or equal to start")
        return v


class DetailedFinding(BaseModel):
    issue: str
    severity: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    highlights: Optional[list[TextHighlight]] = None


class AgentCritique(BaseModel):
    agent_type: AgentType
    score: float
    summary: str
    findings: list[DetailedFinding]
    strengths: list[str]
    weaknesses: list[str]

    @field_validator("score")
    def score_must_be_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 10.0:
            raise ValueError("score must be between 0.0 and 10.0")
        return v
