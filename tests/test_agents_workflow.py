"""Focused tests to boost coverage to 80%"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.models.schemas import AgentCritique, DetailedFinding, TextHighlight


# Agent Tests
@pytest.mark.asyncio
async def test_methodology_agent_prompt():
    from app.agents.specialist_agents import MethodologyAgent
    agent = MethodologyAgent()
    prompt = agent.get_system_prompt()
    assert "Methodology" in prompt
    assert len(prompt) > 100


@pytest.mark.asyncio
async def test_literature_agent_prompt():
    from app.agents.specialist_agents import LiteratureAgent
    agent = LiteratureAgent()
    prompt = agent.get_system_prompt()
    assert "Literature" in prompt


@pytest.mark.asyncio
async def test_clarity_agent_prompt():
    from app.agents.specialist_agents import ClarityAgent
    agent = ClarityAgent()
    prompt = agent.get_system_prompt()
    assert "Clarity" in prompt


@pytest.mark.asyncio
async def test_ethics_agent_prompt():
    from app.agents.specialist_agents import EthicsAgent
    agent = EthicsAgent()
    prompt = agent.get_system_prompt()
    assert "Ethics" in prompt


@pytest.mark.asyncio
async def test_base_agent_build_prompt():
    from app.agents.specialist_agents import MethodologyAgent
    agent = MethodologyAgent()
    context = {
        "content": "Test content",
        "sections": {"intro": {"word_count": 100, "content": [(1, "test")]}}
    }
    prompt = agent.build_prompt(context)
    assert "Test content" in prompt
    assert "JSON RESPONSE FORMAT" in prompt


@pytest.mark.asyncio
async def test_base_agent_parse_valid_response():
    from app.agents.specialist_agents import MethodologyAgent
    agent = MethodologyAgent()
    response = '{"score": 8.0, "findings": [], "recommendations": ["Test"], "confidence": 0.9, "bias_check": "OK"}'
    critique = agent.parse_response(response)
    assert isinstance(critique, AgentCritique)
    assert critique.agent_type == "methodology"


@pytest.mark.asyncio
async def test_base_agent_parse_invalid_response():
    from app.agents.specialist_agents import MethodologyAgent
    agent = MethodologyAgent()
    response = "Invalid JSON"
    critique = agent.parse_response(response)
    assert isinstance(critique, AgentCritique)
    assert critique.score == 0.0


# LLM Service Tests
@pytest.mark.asyncio
async def test_llm_service_get_provider():
    from app.services.llm_service import llm_service
    with patch('app.services.llm_service.settings') as mock_settings:
        mock_settings.DEFAULT_LLM = "groq"
        mock_settings.GROQ_API_KEY = "test"
        provider = llm_service.get_provider("groq")
        assert provider is not None


@pytest.mark.asyncio
async def test_llm_service_invalid_provider():
    from app.services.llm_service import llm_service
    with pytest.raises(ValueError):
        llm_service.get_provider("invalid")


@pytest.mark.asyncio
async def test_llm_service_generate_with_cache():
    from app.services.llm_service import llm_service
    with patch('app.services.llm_service.cache_service') as mock_cache, \
         patch('app.services.llm_service.settings') as mock_settings:
        mock_settings.DEFAULT_LLM = "groq"
        mock_cache.get = AsyncMock(return_value="Cached")
        result = await llm_service.generate_content("Test")
        assert result == "Cached"


# Workflow Tests
@pytest.mark.asyncio
async def test_workflow_initialize():
    from app.services.langgraph_workflow import langgraph_workflow, EnhancedReviewState
    state = EnhancedReviewState(
        submission_id="test",
        content="Test content",
        title="Test",
        metadata={},
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
    result = langgraph_workflow._initialize_review(state)
    assert "domain" in result
    assert "context" in result


@pytest.mark.asyncio
async def test_workflow_extract_score():
    from app.services.langgraph_workflow import langgraph_workflow
    score = langgraph_workflow._extract_score("Score: 8")
    assert score == 8
    score = langgraph_workflow._extract_score("No score")
    assert score == 7


@pytest.mark.asyncio
async def test_workflow_should_retry():
    from app.services.langgraph_workflow import langgraph_workflow, EnhancedReviewState
    state = EnhancedReviewState(
        submission_id="test",
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
        retry_count=0
    )
    result = langgraph_workflow._should_retry_reviews(state)
    assert result == "retry"


# LangChain Service Tests
@pytest.mark.asyncio
async def test_langchain_service_init():
    from app.services.langchain_service import langchain_service
    assert langchain_service.models is not None
    assert langchain_service.domain_prompts is not None


@pytest.mark.asyncio
async def test_langchain_cleanup_memory():
    from app.services.langchain_service import langchain_service
    langchain_service.cleanup_memory()
    # Should not raise


# Synthesis Agent Tests
@pytest.mark.asyncio
async def test_synthesis_agent_calculate_weighted_score():
    from app.agents.synthesis_agent import SynthesisAgent
    agent = SynthesisAgent()
    critiques = [
        {"agent_type": "methodology", "score": 8.0},
        {"agent_type": "literature", "score": 7.0}
    ]
    weights = {"methodology": 0.4, "literature": 0.3, "clarity": 0.2, "ethics": 0.1}
    score = agent._calculate_weighted_score(critiques, weights)
    assert 0.0 <= score <= 10.0


@pytest.mark.asyncio
async def test_synthesis_agent_determine_decision():
    from app.agents.synthesis_agent import SynthesisAgent
    agent = SynthesisAgent()
    assert agent._determine_decision(9.0) == "Accept"
    assert agent._determine_decision(7.0) == "Minor Revisions"
    assert agent._determine_decision(5.0) == "Major Revisions"
    assert agent._determine_decision(3.0) == "Reject"


@pytest.mark.asyncio
async def test_synthesis_agent_format_agent_scores():
    from app.agents.synthesis_agent import SynthesisAgent
    agent = SynthesisAgent()
    critiques = [
        {"agent_type": "methodology", "score": 8.0},
        {"agent_type": "literature", "score": 7.0}
    ]
    result = agent._format_agent_scores(critiques)
    assert "Methodology" in result
    assert "8.0" in result


@pytest.mark.asyncio
async def test_synthesis_agent_format_domain_criteria():
    from app.agents.synthesis_agent import SynthesisAgent
    agent = SynthesisAgent()
    criteria = {
        "methodology": ["test1", "test2"],
        "literature": ["test3"]
    }
    result = agent._format_domain_criteria(criteria)
    assert "methodology" in result.lower()


# Orchestrator Tests
@pytest.mark.asyncio
async def test_orchestrator_process_submission_success():
    from app.agents.orchestrator import orchestrator
    with patch('app.agents.orchestrator.mongodb_service') as mock_db, \
         patch('app.agents.orchestrator.langgraph_workflow') as mock_workflow, \
         patch('app.agents.orchestrator.rate_limiter') as mock_limiter, \
         patch('app.agents.orchestrator.document_cache_service') as mock_cache:
        
        mock_db.get_submission = AsyncMock(return_value={
            "_id": "test", "title": "test.pdf", "content": "test"
        })
        mock_db.update_submission = AsyncMock()
        mock_workflow.execute_review = AsyncMock(return_value="Report")
        mock_limiter.check_concurrent_processing = Mock()
        mock_limiter.release_processing = Mock()
        mock_cache.cache_submission = AsyncMock()
        
        result = await orchestrator.process_submission("test")
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_orchestrator_submission_not_found():
    from app.agents.orchestrator import orchestrator
    with patch('app.agents.orchestrator.mongodb_service') as mock_db, \
         patch('app.agents.orchestrator.rate_limiter') as mock_limiter:
        
        mock_db.get_submission = AsyncMock(return_value=None)
        mock_limiter.check_concurrent_processing = Mock()
        mock_limiter.release_processing = Mock()
        
        with pytest.raises(ValueError):
            await orchestrator.process_submission("invalid")


# Enhanced LLM Service Tests
@pytest.mark.asyncio
async def test_enhanced_llm_service_exists():
    try:
        from app.services.enhanced_llm_service import enhanced_llm_service
        assert enhanced_llm_service is not None
    except ImportError:
        pytest.skip("Enhanced LLM service not available")


# Manuscript Analyzer Tests
def test_manuscript_analyzer_analyze_structure():
    from app.services.manuscript_analyzer import manuscript_analyzer
    content = "Introduction\nThis is intro.\n\nMethods\nThis is methods."
    result = manuscript_analyzer.analyze_structure(content)
    assert isinstance(result, dict)


def test_manuscript_analyzer_find_line_number():
    from app.services.manuscript_analyzer import manuscript_analyzer
    content = "Line 1\nLine 2\nLine 3"
    line = manuscript_analyzer.find_line_number(content, "Line 2")
    assert line is not None


# Text Analysis Tests
def test_text_analyzer_find_position():
    from app.services.text_analysis import TextAnalyzer
    content = "This is a test"
    start, end = TextAnalyzer.find_text_position(content, "test")
    assert start >= 0
    assert end > start


def test_text_analyzer_extract_context():
    from app.services.text_analysis import TextAnalyzer
    content = "This is a test content"
    context = TextAnalyzer.extract_context(content, 10, 14)
    assert isinstance(context, str)
