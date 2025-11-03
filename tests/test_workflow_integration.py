"""Complete workflow integration tests"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.langgraph_workflow import langgraph_workflow, EnhancedReviewState


@pytest.mark.asyncio
async def test_workflow_initialize_review():
    """Test workflow initialization"""
    state = EnhancedReviewState(
        submission_id="test123",
        content="Test manuscript content",
        title="Test Paper",
        metadata={"pages": 10},
        domain="",
        methodology_critique={},
        literature_critique={},
        clarity_critique={},
        ethics_critique={},
        final_report="",
        context={},
        embeddings_created=False,
        retry_count=0
    )
    
    with patch('app.services.langgraph_workflow.DomainDetector') as mock_detector:
        mock_detector.return_value.detect_domain.return_value = {"primary_domain": "computer_science"}
        
        workflow = langgraph_workflow
        result = workflow._initialize_review(state)
        
        assert result["domain"] == "computer_science"
        assert "domain" in result["context"]


@pytest.mark.asyncio
async def test_workflow_create_embeddings():
    """Test workflow embedding creation"""
    state = EnhancedReviewState(
        submission_id="test123",
        content="Test content",
        title="Test",
        metadata={},
        domain="general",
        methodology_critique={},
        literature_critique={},
        clarity_critique={},
        ethics_critique={},
        final_report="",
        context={},
        embeddings_created=False,
        retry_count=0
    )
    
    with patch('app.services.langgraph_workflow.langchain_service') as mock_service:
        mock_service.embeddings = True
        mock_service.create_document_embeddings = AsyncMock()
        
        workflow = langgraph_workflow
        result = await workflow._create_embeddings(state)
        
        assert result["embeddings_created"] == True


@pytest.mark.asyncio
async def test_workflow_parallel_reviews(mock_langchain_service):
    """Test workflow parallel review execution"""
    state = EnhancedReviewState(
        submission_id="test123",
        content="Test manuscript with methodology and literature review",
        title="Test Paper",
        metadata={},
        domain="computer_science",
        methodology_critique={},
        literature_critique={},
        clarity_critique={},
        ethics_critique={},
        final_report="",
        context={"domain": "computer_science"},
        embeddings_created=True,
        retry_count=0
    )
    
    with patch('app.services.langgraph_workflow.langchain_service', mock_langchain_service):
        workflow = langgraph_workflow
        result = await workflow._parallel_reviews(state)
        
        assert "methodology_critique" in result
        assert "literature_critique" in result
        assert "clarity_critique" in result
        assert "ethics_critique" in result


@pytest.mark.asyncio
async def test_workflow_synthesize_report():
    """Test workflow report synthesis"""
    state = EnhancedReviewState(
        submission_id="test123",
        content="Test content",
        title="Test Paper",
        metadata={},
        domain="general",
        methodology_critique={"agent_type": "methodology", "content": "Good methodology", "score": 8},
        literature_critique={"agent_type": "literature", "content": "Good literature", "score": 7},
        clarity_critique={"agent_type": "clarity", "content": "Clear writing", "score": 9},
        ethics_critique={"agent_type": "ethics", "content": "Ethical", "score": 8},
        final_report="",
        context={},
        embeddings_created=True,
        retry_count=0
    )
    
    with patch('app.services.langgraph_workflow.SynthesisAgent') as mock_agent:
        mock_instance = Mock()
        mock_instance.generate_final_report = AsyncMock(return_value="Final comprehensive report")
        mock_agent.return_value = mock_instance
        
        workflow = langgraph_workflow
        result = await workflow._synthesize_report(state)
        
        assert result["final_report"] == "Final comprehensive report"


@pytest.mark.asyncio
async def test_workflow_execute_review_complete():
    """Test complete workflow execution"""
    submission_data = {
        "_id": "test123",
        "content": "Test manuscript content",
        "title": "Test Paper",
        "file_metadata": {"pages": 10}
    }
    
    with patch('app.services.langgraph_workflow.DomainDetector') as mock_detector, \
         patch('app.services.langgraph_workflow.langchain_service') as mock_langchain, \
         patch('app.services.langgraph_workflow.SynthesisAgent') as mock_synthesis:
        
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
        "file_metadata": {}
    }
    
    with patch('app.services.langgraph_workflow.DomainDetector') as mock_detector:
        mock_detector.return_value.detect_domain.side_effect = Exception("Domain detection failed")
        
        result = await langgraph_workflow.execute_review(submission_data)
        
        # Should return error message, not raise exception
        assert "error" in result.lower() or "failed" in result.lower()


@pytest.mark.asyncio
async def test_workflow_should_retry_reviews():
    """Test workflow retry logic"""
    state = EnhancedReviewState(
        submission_id="test123",
        content="Test",
        title="Test",
        metadata={},
        domain="general",
        methodology_critique={"content": "failed due to internal error"},
        literature_critique={"content": "Good review"},
        clarity_critique={"content": "Good review"},
        ethics_critique={"content": "Good review"},
        final_report="",
        context={},
        embeddings_created=True,
        retry_count=0
    )
    
    workflow = langgraph_workflow
    result = workflow._should_retry_reviews(state)
    
    assert result == "retry"
    assert state["retry_count"] == 1


@pytest.mark.asyncio
async def test_workflow_no_retry_after_max():
    """Test workflow doesn't retry after max attempts"""
    state = EnhancedReviewState(
        submission_id="test123",
        content="Test",
        title="Test",
        metadata={},
        domain="general",
        methodology_critique={"content": "failed due to internal error"},
        literature_critique={"content": "Good"},
        clarity_critique={"content": "Good"},
        ethics_critique={"content": "Good"},
        final_report="",
        context={},
        embeddings_created=True,
        retry_count=1
    )
    
    workflow = langgraph_workflow
    result = workflow._should_retry_reviews(state)
    
    assert result == "synthesize"


@pytest.mark.asyncio
async def test_workflow_extract_score():
    """Test score extraction from response"""
    workflow = langgraph_workflow
    
    response_with_score = "The methodology is good. Score: 8"
    score = workflow._extract_score(response_with_score)
    assert score == 8
    
    response_without_score = "The methodology is good."
    score = workflow._extract_score(response_without_score)
    assert score == 7  # Default


@pytest.mark.asyncio
async def test_workflow_format_critiques():
    """Test critique formatting"""
    workflow = langgraph_workflow
    
    critiques = [
        {"agent_type": "methodology", "content": "x" * 600},
        {"agent_type": "literature", "content": "Good literature review"}
    ]
    
    formatted = workflow._format_critiques(critiques)
    
    assert "Methodology:" in formatted
    assert "Literature:" in formatted
    assert len(formatted.split("Methodology:")[1].split("\n")[0]) <= 510  # Truncated to 500 + "..."
