from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_mongodb_service():
    mock = Mock()
    mock.save_submission = AsyncMock(return_value="test_id_123")
    mock.get_submission = AsyncMock(
        return_value={
            "_id": "test_id_123",
            "title": "test.pdf",
            "content": "test content",
            "status": "completed",
            "final_report": "test report",
        }
    )
    mock.get_agent_tasks = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_document_parser():
    mock = Mock()
    mock.parse_document.return_value = {
        "content": "parsed content",
        "metadata": {"pages": 1, "file_type": "pdf"},
    }
    return mock


@pytest.fixture
def mock_orchestrator():
    mock = Mock()
    mock.process_submission = AsyncMock()
    return mock


@pytest.fixture
def sample_pdf_content():
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj"


@pytest.fixture
def sample_docx_content():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("word/document.xml", "<document/>")
        zf.writestr("[Content_Types].xml", "<Types/>")
    return buffer.getvalue()
