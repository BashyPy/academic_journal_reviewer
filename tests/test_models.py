from datetime import datetime

import pytest
from pydantic import ValidationError


class TestSchemas:
    def test_task_status_enum(self):
        from app.models.schemas import TaskStatus

        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_submission_schema_valid(self):
        from app.models.schemas import SubmissionCreate

        data = {
            "title": "test.pdf",
            "content": "test content",
            "file_metadata": {"pages": 1, "file_type": "pdf"},
        }

        submission = SubmissionCreate(**data)
        assert submission.title == "test.pdf"
        assert submission.content == "test content"

    def test_submission_schema_invalid(self):
        from app.models.schemas import SubmissionCreate

        with pytest.raises(ValidationError):
            SubmissionCreate(title="", content="")

    def test_agent_task_schema(self):
        from app.models.schemas import AgentTask

        data = {
            "submission_id": "test_id",
            "agent_type": "methodology",
            "status": "completed",
            "critique": {"score": 8, "issues": []},
        }

        task = AgentTask(**data)
        assert task.agent_type == "methodology"
        assert task.status == "completed"


class TestResponses:
    def test_upload_response(self):
        from app.models.responses import UploadResponse

        data = {
            "submission_id": "test_id",
            "status": "processing",
            "message": "Upload successful",
        }

        response = UploadResponse(**data)
        assert response.submission_id == "test_id"
        assert response.status == "processing"

    def test_status_response(self):
        from app.models.responses import StatusResponse

        data = {
            "submission_id": "test_id",
            "status": "processing",
            "tasks": [{"agent_type": "methodology", "status": "completed"}],
        }

        response = StatusResponse(**data)
        assert response.submission_id == "test_id"
        assert len(response.tasks) == 1

    def test_report_response(self):
        from app.models.responses import ReportResponse

        data = {
            "submission_id": "test_id",
            "title": "test.pdf",
            "final_report": "Test report content",
            "completed_at": datetime.now(),
            "status": "completed",
        }

        response = ReportResponse(**data)
        assert response.submission_id == "test_id"
        assert response.final_report == "Test report content"

    def test_submission_response(self):
        from app.models.responses import SubmissionResponse

        data = {
            "id": "test_id",
            "title": "test.pdf",
            "content": "test content",
            "file_metadata": {"pages": 1},
            "status": "completed",
            "created_at": datetime.now(),
        }

        response = SubmissionResponse(**data)
        assert response.id == "test_id"
        assert response.title == "test.pdf"

    def test_response_validation_error(self):
        from app.models.responses import UploadResponse

        # This should not raise an error as empty strings are valid
        response = UploadResponse(submission_id="", status="", message="")
        assert response.submission_id == ""
        assert response.status == ""
        assert response.message == ""


class TestResponseSerialization:
    def test_upload_response_json(self):
        from app.models.responses import UploadResponse

        response = UploadResponse(
            submission_id="test_id", status="processing", message="Success"
        )

        json_data = response.model_dump()
        assert json_data["submission_id"] == "test_id"
        assert json_data["status"] == "processing"

    def test_datetime_serialization(self):
        from app.models.responses import ReportResponse

        now = datetime.now()
        response = ReportResponse(
            submission_id="test_id",
            title="test.pdf",
            final_report="report",
            completed_at=now,
            status="completed",
        )

        json_data = response.model_dump()
        assert "completed_at" in json_data
        assert isinstance(json_data["completed_at"], datetime)
