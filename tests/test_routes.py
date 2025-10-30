import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import UploadFile
from io import BytesIO
from datetime import datetime, timezone

from app.api.routes import (
    _sanitize_and_validate_filename,
    _read_and_validate_content,
    _convert_to_timezone,
    _content_matches_extension
)

class TestFilenameValidation:
    def test_valid_filename(self):
        result = _sanitize_and_validate_filename("test_file.pdf")
        assert result[0] == "test_file.pdf"
        assert result[1] == ".pdf"

    def test_invalid_extension(self):
        with pytest.raises(Exception) as exc:
            _sanitize_and_validate_filename("test.txt")
        assert "Invalid file type" in str(exc.value.detail)

    def test_path_traversal_attempt(self):
        with pytest.raises(Exception):
            _sanitize_and_validate_filename("../../../etc/passwd.pdf")

    def test_empty_filename(self):
        with pytest.raises(Exception):
            _sanitize_and_validate_filename("")

    def test_long_filename(self):
        long_name = "a" * 300 + ".pdf"
        with pytest.raises(Exception):
            _sanitize_and_validate_filename(long_name)

class TestContentValidation:
    def test_pdf_content_match(self):
        assert _content_matches_extension(b"%PDF-1.4", ".pdf") == True
        assert _content_matches_extension(b"not pdf", ".pdf") == False

    def test_docx_content_match(self, sample_docx_content):
        assert _content_matches_extension(sample_docx_content, ".docx") == True
        assert _content_matches_extension(b"not docx", ".docx") == False

    @pytest.mark.asyncio
    async def test_read_valid_content(self, sample_pdf_content):
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=sample_pdf_content)
        mock_file.content_type = "application/pdf"
        
        content, content_type = await _read_and_validate_content(mock_file, ".pdf", "test.pdf")
        assert content == sample_pdf_content
        assert content_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_read_empty_file(self):
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=b"")
        
        with pytest.raises(Exception) as exc:
            await _read_and_validate_content(mock_file, ".pdf", "test.pdf")
        assert "Empty file" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_read_large_file(self):
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=large_content)
        
        with pytest.raises(Exception) as exc:
            await _read_and_validate_content(mock_file, ".pdf", "test.pdf")
        assert "File too large" in str(exc.value.detail)

class TestTimezoneConversion:
    def test_convert_utc_to_timezone(self):
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _convert_to_timezone(dt, "America/New_York")
        assert result.hour == 7  # UTC-5 in winter

    def test_convert_naive_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = _convert_to_timezone(dt, "America/New_York")
        assert result.tzinfo is not None

    def test_convert_invalid_timezone(self):
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _convert_to_timezone(dt, "Invalid/Timezone")
        assert result == dt  # Should return original

class TestAPIEndpoints:
    @patch('app.api.routes.mongodb_service')
    @patch('app.api.routes.document_parser')
    @patch('app.api.routes.orchestrator')
    def test_upload_manuscript_success(self, mock_orchestrator, mock_parser, mock_db, client, sample_pdf_content):
        mock_db.save_submission = AsyncMock(return_value="test_id_123")
        mock_parser.parse_document.return_value = {
            "content": "parsed content",
            "metadata": {"pages": 1}
        }
        mock_orchestrator.process_submission = AsyncMock()

        response = client.post(
            "/api/v1/submissions/upload",
            files={"file": ("test.pdf", sample_pdf_content, "application/pdf")}
        )
        assert response.status_code == 200
        assert "submission_id" in response.json()

    def test_upload_invalid_file_type(self, client):
        response = client.post(
            "/api/v1/submissions/upload",
            files={"file": ("test.txt", b"content", "text/plain")}
        )
        assert response.status_code == 400

    def test_upload_no_file(self, client):
        response = client.post("/api/v1/submissions/upload")
        assert response.status_code == 422

    @patch('app.api.routes.mongodb_service')
    def test_get_submission_success(self, mock_db, client):
        from datetime import datetime
        mock_db.get_submission = AsyncMock(return_value={
            "id": "test_id",
            "title": "test.pdf",
            "content": "content",
            "status": "completed",
            "file_metadata": {"pages": 1, "file_type": "pdf"},
            "created_at": datetime.now()
        })
        
        response = client.get("/api/v1/submissions/test_id")
        assert response.status_code == 200

    @patch('app.api.routes.mongodb_service')
    def test_get_submission_not_found(self, mock_db, client):
        mock_db.get_submission = AsyncMock(return_value=None)
        
        response = client.get("/api/v1/submissions/nonexistent")
        assert response.status_code == 404

    def test_get_submission_invalid_id(self, client):
        response = client.get("/api/v1/submissions/")
        assert response.status_code == 404

    @patch('app.api.routes.mongodb_service')
    def test_get_status_success(self, mock_db, client):
        mock_db.get_submission = AsyncMock(return_value={"status": "processing"})
        mock_db.get_agent_tasks = AsyncMock(return_value=[
            {"agent_type": "methodology", "status": "completed"}
        ])
        
        response = client.get("/api/v1/submissions/test_id/status")
        assert response.status_code == 200
        assert "tasks" in response.json()

    @patch('app.api.routes.mongodb_service')
    @patch('app.api.routes.disclaimer_service')
    def test_get_report_success(self, mock_disclaimer, mock_db, client):
        from datetime import datetime
        mock_db.get_submission = AsyncMock(return_value={
            "status": "completed",
            "title": "test.pdf",
            "final_report": "report content",
            "completed_at": datetime.now()
        })
        mock_disclaimer.get_api_disclaimer.return_value = {"disclaimer": "test"}
        
        response = client.get("/api/v1/submissions/test_id/report")
        assert response.status_code == 200

    @patch('app.api.routes.mongodb_service')
    def test_get_report_not_completed(self, mock_db, client):
        mock_db.get_submission = AsyncMock(return_value={"status": "processing"})
        
        response = client.get("/api/v1/submissions/test_id/report")
        assert response.status_code == 400

    @patch('app.api.routes.mongodb_service')
    @patch('app.api.routes.pdf_generator')
    def test_download_pdf_success(self, mock_pdf, mock_db, client):
        mock_db.get_submission = AsyncMock(return_value={
            "status": "completed",
            "final_report": "report",
            "file_metadata": {"original_filename": "test.pdf"}
        })
        mock_pdf.generate_review_pdf.return_value = BytesIO(b"pdf content")
        
        response = client.get("/api/v1/submissions/test_id/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"