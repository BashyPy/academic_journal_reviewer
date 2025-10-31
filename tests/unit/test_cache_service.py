from unittest.mock import AsyncMock, patch

import pytest

from app.services.cache_service import CacheService


@pytest.fixture
def cache_service():
    return CacheService(default_ttl_hours=1)


@pytest.mark.asyncio
async def test_cache_key_generation(cache_service):
    key1 = cache_service._generate_cache_key("test prompt", "openai")
    key2 = cache_service._generate_cache_key("test prompt", "openai")
    key3 = cache_service._generate_cache_key("different prompt", "openai")

    assert key1 == key2  # Same inputs should generate same key
    assert key1 != key3  # Different inputs should generate different keys


@pytest.mark.asyncio
@patch("app.services.cache_service.mongodb_service")
async def test_cache_get_miss(mock_mongodb, cache_service):
    mock_mongodb.db.__getitem__.return_value.find_one = AsyncMock(return_value=None)

    result = await cache_service.get("test prompt", "openai")
    assert result is None


@pytest.mark.asyncio
@patch("app.services.cache_service.mongodb_service")
async def test_cache_get_hit(mock_mongodb, cache_service):
    mock_mongodb.db.__getitem__.return_value.find_one = AsyncMock(
        return_value={"response": "cached response"}
    )

    result = await cache_service.get("test prompt", "openai")
    assert result == "cached response"
