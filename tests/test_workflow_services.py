"""Workflow services tests - consolidated and deduplicated"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
async def test_orchestrator_complete_flow():
    from app.agents.orchestrator import orchestrator

    with (
        patch("app.agents.orchestrator.mongodb_service") as mock_db,
        patch("app.agents.orchestrator.langgraph_workflow") as mock_workflow,
        patch("app.agents.orchestrator.rate_limiter") as mock_limiter,
        patch("app.agents.orchestrator.document_cache_service") as mock_cache,
    ):
        mock_db.get_submission = AsyncMock(
            return_value={"_id": "test", "title": "test.pdf", "content": "test"}
        )
        mock_db.update_submission = AsyncMock()
        mock_workflow.execute_review = AsyncMock(return_value="Final report")
        mock_limiter.check_concurrent_processing = Mock()
        mock_limiter.release_processing = Mock()
        mock_cache.cache_submission = AsyncMock()

        result = await orchestrator.process_submission("test", "127.0.0.1", "UTC")
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_orchestrator_error_handling():
    from app.agents.orchestrator import orchestrator

    with (
        patch("app.agents.orchestrator.mongodb_service") as mock_db,
        patch("app.agents.orchestrator.langgraph_workflow") as mock_workflow,
        patch("app.agents.orchestrator.rate_limiter") as mock_limiter,
    ):
        mock_db.get_submission = AsyncMock(
            return_value={"_id": "test", "title": "test", "content": "test"}
        )
        mock_db.update_submission = AsyncMock()
        mock_workflow.execute_review = AsyncMock(side_effect=Exception("Test error"))
        mock_limiter.check_concurrent_processing = Mock()
        mock_limiter.release_processing = Mock()

        with pytest.raises(Exception):
            await orchestrator.process_submission("test")
