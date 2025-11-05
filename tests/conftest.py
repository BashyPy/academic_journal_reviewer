"""Shared test fixtures and utilities to eliminate code duplication"""

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi import UploadFile
from fastapi.security import HTTPAuthorizationCredentials

# ============================================================================
# SHARED FIXTURES
# ============================================================================


@pytest.fixture
def mock_user():
    """Standard mock user for tests"""
    return {
        "user_id": "test123",
        "email": "test@test.com",
        "name": "Test User",
        "role": "author",
        "active": True,
        "email_verified": True,
    }


@pytest.fixture
def mock_admin_user():
    """Mock admin user"""
    return {
        "user_id": "admin123",
        "email": "admin@test.com",
        "name": "Admin User",
        "role": "admin",
        "active": True,
        "email_verified": True,
    }


@pytest.fixture
def mock_editor_user():
    """Mock editor user"""
    return {
        "user_id": "editor123",
        "email": "editor@test.com",
        "name": "Editor User",
        "role": "editor",
        "active": True,
        "email_verified": True,
    }


@pytest.fixture
def mock_submission():
    """Standard mock submission"""
    return {
        "_id": "sub123",
        "title": "Test Manuscript",
        "content": "Test manuscript content for analysis",
        "detected_domain": "Computer Science",
        "status": "completed",
        "user_email": "test@test.com",
        "created_at": datetime.now(timezone.utc),
        "file_metadata": {"original_filename": "test.pdf", "pages": 10},
    }


@pytest.fixture
def mock_pdf_file():
    """Mock PDF file for upload tests"""
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"
    return UploadFile(filename="test.pdf", file=BytesIO(content))


@pytest.fixture
def mock_credentials():
    """Mock JWT credentials"""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")


# ============================================================================
# MOCK FACTORIES
# ============================================================================


class MockFactory:
    """Factory for creating common mock objects"""

    @staticmethod
    def create_mock_db():
        """Create mock database with common collections"""
        db = MagicMock()
        db.users = MagicMock()
        db.submissions = MagicMock()
        db.agent_tasks = MagicMock()
        db.review_assignments = MagicMock()
        db.audit_logs = MagicMock()
        return db

    @staticmethod
    def create_mock_cursor(data=None):
        """Create mock cursor with standard methods"""
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        cursor.to_list = AsyncMock(return_value=data or [])
        return cursor

    @staticmethod
    def create_mock_collection():
        """Create mock collection with standard methods"""
        collection = MagicMock()
        collection.find_one = AsyncMock(return_value=None)
        collection.insert_one = AsyncMock(return_value=Mock(inserted_id="test_id"))
        collection.update_one = AsyncMock(return_value=Mock(modified_count=1))
        collection.delete_one = AsyncMock(return_value=Mock(deleted_count=1))
        collection.count_documents = AsyncMock(return_value=0)
        collection.find = MagicMock(return_value=MockFactory.create_mock_cursor())
        collection.aggregate = MagicMock(return_value=MockFactory.create_mock_cursor())
        return collection


# ============================================================================
# COMMON TEST UTILITIES
# ============================================================================


class TestUtils:
    """Common test utilities"""

    @staticmethod
    def assert_api_response(response, expected_keys=None):
        """Assert API response has expected structure"""
        assert isinstance(response, dict)
        if expected_keys:
            for key in expected_keys:
                assert key in response

    @staticmethod
    def create_test_data(count=5, base_data=None):
        """Create test data list"""
        base = base_data or {"id": "test", "name": "Test Item"}
        return [{"id": f"{base['id']}_{i}", **base} for i in range(count)]


# ============================================================================
# SHARED MOCK CONTEXTS
# ============================================================================


@pytest.fixture
def mock_mongodb_service():
    """Mock MongoDB service with standard setup"""
    with pytest.mock.patch("app.services.mongodb_service.mongodb_service") as mock:
        mock.get_database = Mock(return_value=MockFactory.create_mock_db())
        mock.save_submission = AsyncMock(return_value="test_id")
        mock.get_submission = AsyncMock(return_value={"_id": "test_id"})
        mock.update_submission = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_user_service():
    """Mock user service with standard setup"""
    with pytest.mock.patch("app.services.user_service.user_service") as mock:
        mock.get_user_by_email = AsyncMock(return_value={"email": "test@test.com"})
        mock.get_user_by_api_key = AsyncMock(return_value={"api_key": "test_key"})
        mock.create_user = AsyncMock(return_value={"email": "test@test.com"})
        mock.authenticate_user = AsyncMock(return_value={"email": "test@test.com"})
        yield mock


@pytest.fixture
def mock_cache_service():
    """Mock cache service with standard setup"""
    with pytest.mock.patch("app.services.cache_service.cache_service") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        mock.clear_all = AsyncMock()
        mock.get_stats = AsyncMock(return_value={"hits": 100, "misses": 10})
        yield mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service with standard setup"""
    with pytest.mock.patch("app.services.llm_service.llm_service") as mock:
        mock.generate_content = AsyncMock(return_value="Generated content")
        mock.call_llm = Mock(return_value="Generated content")
        yield mock


@pytest.fixture
def mock_langchain_service():
    """Mock LangChain service with standard setup"""
    with pytest.mock.patch("app.services.langchain_service.langchain_service") as mock:
        mock.domain_aware_review = AsyncMock(return_value="Domain review")
        mock.chain_of_thought_analysis = AsyncMock(return_value="COT analysis")
        mock.multi_model_consensus = AsyncMock(return_value="Consensus")
        mock.create_document_embeddings = AsyncMock()
        mock.semantic_search = AsyncMock(return_value=[])
        yield mock


# ============================================================================
# PARAMETRIZED TEST DATA
# ============================================================================


@pytest.fixture(params=["admin", "editor", "reviewer"])
def privileged_user(request):
    """Parametrized fixture for users with elevated privileges"""
    return {
        "user_id": f"{request.param}123",
        "email": f"{request.param}@test.com",
        "role": request.param,
        "active": True,
    }


@pytest.fixture(params=["pending", "processing", "completed", "failed"])
def submission_status(request):
    """Parametrized fixture for submission statuses"""
    return request.param


# ============================================================================
# ASYNC TEST HELPERS
# ============================================================================


class AsyncTestHelper:
    """Helper class for async test operations"""

    @staticmethod
    async def run_with_timeout(coro, timeout=5):
        """Run coroutine with timeout"""
        import asyncio

        return await asyncio.wait_for(coro, timeout=timeout)

    @staticmethod
    def create_async_context_manager(return_value=None):
        """Create async context manager mock"""
        mock = AsyncMock()
        mock.__aenter__ = AsyncMock(return_value=return_value)
        mock.__aexit__ = AsyncMock(return_value=None)
        return mock
