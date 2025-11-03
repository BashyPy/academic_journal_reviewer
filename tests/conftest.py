from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
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


@pytest.fixture
def mock_user():
    """Mock authenticated user for testing"""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "role": "user",
        "api_key": "test_api_key",
        "active": True,
        "email_verified": True
    }


@pytest.fixture
def auth_headers():
    """Authentication headers for testing"""
    return {"X-API-Key": "test_api_key"}


@pytest.fixture
def authenticated_client(client, mock_user):
    """Client with authentication mocked"""
    with patch('app.middleware.auth.get_api_key', return_value=mock_user):
        yield client


@pytest_asyncio.fixture
async def mock_llm_response():
    """Mock LLM response for testing"""
    return Mock(
        text="{\"score\": 8.5, \"findings\": [], \"recommendations\": [\"Test recommendation\"], \"confidence\": 0.9, \"bias_check\": \"Objective\"}",
        choices=[Mock(message=Mock(content="Test LLM response"))]
    )


@pytest_asyncio.fixture
async def mock_genai_model():
    """Mock Google Generative AI model"""
    mock = Mock()
    mock.generate_content_async = AsyncMock(return_value=Mock(
        text="{\"score\": 8.5, \"findings\": [], \"recommendations\": [\"Test\"], \"confidence\": 0.9, \"bias_check\": \"OK\"}"
    ))
    return mock


@pytest_asyncio.fixture
async def mock_langchain_service():
    """Mock LangChain service"""
    mock = Mock()
    mock.domain_aware_review = AsyncMock(return_value="Domain review complete")
    mock.chain_of_thought_analysis = AsyncMock(return_value="Chain analysis complete")
    mock.multi_model_consensus = AsyncMock(return_value="Consensus reached")
    mock.create_document_embeddings = AsyncMock()
    mock.embeddings = True
    return mock
