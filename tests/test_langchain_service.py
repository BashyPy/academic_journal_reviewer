"""LangChain service tests"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.langchain_service import langchain_service


@pytest.mark.asyncio
async def test_langchain_domain_aware_review():
    """Test domain-aware review"""
    with patch('app.services.langchain_service.llm_service') as mock_llm:
        mock_llm.generate_content = AsyncMock(return_value="Domain-specific review")

        result = await langchain_service.domain_aware_review(
            "Test content",
            "computer_science",
            "methodology",
            {"domain": "computer_science"}
        )

        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_langchain_chain_of_thought_analysis():
    """Test chain of thought analysis"""
    with patch('app.services.langchain_service.llm_service') as mock_llm:
        mock_llm.generate_content = AsyncMock(return_value="Step-by-step analysis")

        result = await langchain_service.chain_of_thought_analysis(
            "Test prompt",
            {"context": "test"}
        )

        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_langchain_multi_model_consensus():
    """Test multi-model consensus"""
    with patch('app.services.langchain_service.llm_service') as mock_llm:
        mock_llm.generate_content = AsyncMock(return_value="Model response")

        result = await langchain_service.multi_model_consensus(
            "Test prompt",
            {"context": "test"}
        )

        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_langchain_create_document_embeddings():
    """Test document embedding creation"""
    with patch('app.services.langchain_service.langchain_service.embeddings') as mock_embeddings:
        mock_embeddings.embed_documents = Mock(return_value=[[0.1, 0.2, 0.3]])

        await langchain_service.create_document_embeddings(
            "Test content",
            {"title": "Test"}
        )



@pytest.mark.asyncio
async def test_langchain_semantic_search():
    """Test semantic search"""
    with patch('app.services.langchain_service.langchain_service.vector_store') as mock_store:
        mock_store.similarity_search = AsyncMock(return_value=[
            Mock(page_content="Result 1"),
            Mock(page_content="Result 2")
        ])

        results = await langchain_service.semantic_search("test query", k=2)

        assert len(results) == 2


@pytest.mark.asyncio
async def test_langchain_handles_errors():
    """Test LangChain service error handling"""
    with patch('app.services.langchain_service.llm_service') as mock_llm:
        mock_llm.generate_content = AsyncMock(side_effect=Exception("LLM error"))

        # Should handle error gracefully
        result = await langchain_service.domain_aware_review(
            "Test",
            "general",
            "methodology",
            {}
        )

        assert isinstance(result, str)
