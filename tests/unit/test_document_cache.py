from unittest.mock import AsyncMock, patch

import pytest

from app.services.document_cache_service import DocumentCacheService


@pytest.fixture
def doc_cache_service():
    return DocumentCacheService()


def test_content_hash_generation(doc_cache_service):
    content1 = "This is test content for academic paper"
    content2 = "This is test content for academic paper"  # Same content
    content3 = "Different content for academic paper"

    hash1 = doc_cache_service._generate_content_hash(content1)
    hash2 = doc_cache_service._generate_content_hash(content2)
    hash3 = doc_cache_service._generate_content_hash(content3)

    assert hash1 == hash2  # Same content = same hash
    assert hash1 != hash3  # Different content = different hash
    assert len(hash1) == 64  # SHA256 hex length


@pytest.mark.asyncio
@patch("app.services.document_cache_service.mongodb_service")
async def test_cache_miss(mock_mongodb, doc_cache_service):
    mock_mongodb.db.__getitem__.return_value.find_one = AsyncMock(return_value=None)

    result = await doc_cache_service.get_cached_submission("test content")
    assert result is None


@pytest.mark.asyncio
@patch("app.services.document_cache_service.mongodb_service")
async def test_cache_hit(mock_mongodb, doc_cache_service):
    cached_data = {"submission_data": {"_id": "test123", "status": "completed"}}
    mock_mongodb.db.__getitem__.return_value.find_one = AsyncMock(return_value=cached_data)

    result = await doc_cache_service.get_cached_submission("test content")
    assert result == {"_id": "test123", "status": "completed"}
