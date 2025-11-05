"""Complete workflow integration tests"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.langgraph_workflow import langgraph_workflow


@pytest.mark.asyncio
async def test_workflow_execute_review_complete():
    """Test complete workflow execution"""
    submission_data = {
        "_id": "test123",
        "content": "Test manuscript content",
        "title": "Test Paper",
        "file_metadata": {"pages": 10},
    }

    with (
        patch("app.services.langgraph_workflow.DomainDetector") as mock_detector,
        patch("app.services.langgraph_workflow.langchain_service") as mock_langchain,
        patch("app.services.langgraph_workflow.SynthesisAgent") as mock_synthesis,
    ):
        mock_detector.return_value.detect_domain.return_value = {"primary_domain": "general"}
        mock_langchain.embeddings = True
        mock_langchain.create_document_embeddings = AsyncMock()
        mock_langchain.domain_aware_review = AsyncMock(return_value="Review complete")
        mock_langchain.chain_of_thought_analysis = AsyncMock(return_value="Analysis complete")
        mock_langchain.multi_model_consensus = AsyncMock(return_value="Consensus reached")

        mock_synthesis_instance = Mock()
        mock_synthesis_instance.generate_final_report = AsyncMock(return_value="Final report")
        mock_synthesis.return_value = mock_synthesis_instance

        result = await langgraph_workflow.execute_review(submission_data)

        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_workflow_handles_errors():
    """Test workflow error handling"""
    submission_data = {
        "_id": "test123",
        "content": "Test content",
        "title": "Test",
        "file_metadata": {},
    }

    with patch("app.services.langgraph_workflow.DomainDetector") as mock_detector:
        mock_detector.return_value.detect_domain.side_effect = Exception("Domain detection failed")

        result = await langgraph_workflow.execute_review(submission_data)

        # Should return error message, not raise exception
        assert "error" in result.lower() or "failed" in result.lower()
