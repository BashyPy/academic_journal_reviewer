"""Complete agent system tests with proper mocking"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.agents.base_agent import BaseAgent
from app.agents.specialist_agents import MethodologyAgent, LiteratureAgent, ClarityAgent, EthicsAgent
from app.agents.orchestrator import orchestrator
from app.models.schemas import AgentCritique, DetailedFinding, TextHighlight


@pytest.mark.asyncio
async def test_base_agent_execute_task(mock_genai_model):
    """Test base agent task execution"""
    with patch('app.agents.base_agent.genai.GenerativeModel', return_value=mock_genai_model):
        agent = MethodologyAgent()
        context = {
            "submission_id": "test123",
            "content": "This is a test manuscript with methodology section."
        }
        result = await agent.execute_task(context)
        assert isinstance(result, AgentCritique)
        assert result.agent_type == "methodology"


@pytest.mark.asyncio
async def test_methodology_agent_system_prompt():
    """Test methodology agent prompt generation"""
    agent = MethodologyAgent()
    prompt = agent.get_system_prompt()
    assert "Methodology" in prompt
    assert "Statistical methods" in prompt


@pytest.mark.asyncio
async def test_literature_agent_system_prompt():
    """Test literature agent prompt generation"""
    agent = LiteratureAgent()
    prompt = agent.get_system_prompt()
    assert "Literature" in prompt
    assert "Citation" in prompt


@pytest.mark.asyncio
async def test_clarity_agent_system_prompt():
    """Test clarity agent prompt generation"""
    agent = ClarityAgent()
    prompt = agent.get_system_prompt()
    assert "Clarity" in prompt
    assert "Presentation" in prompt


@pytest.mark.asyncio
async def test_ethics_agent_system_prompt():
    """Test ethics agent prompt generation"""
    agent = EthicsAgent()
    prompt = agent.get_system_prompt()
    assert "Ethics" in prompt
    assert "Integrity" in prompt


@pytest.mark.asyncio
async def test_agent_parse_response():
    """Test agent response parsing"""
    agent = MethodologyAgent()
    response = """{
        "score": 8.5,
        "findings": [
            {
                "finding": "Test finding",
                "highlights": [{"text": "test", "start_pos": 0, "end_pos": 4, "context": "ctx", "issue_type": "minor"}],
                "severity": "minor",
                "category": "methodology"
            }
        ],
        "recommendations": ["Test rec"],
        "confidence": 0.9,
        "bias_check": "OK"
    }"""
    critique = agent.parse_response(response)
    assert isinstance(critique, AgentCritique)
    assert len(critique.findings) == 1


@pytest.mark.asyncio
async def test_agent_build_prompt():
    """Test agent prompt building"""
    agent = MethodologyAgent()
    context = {
        "content": "Test manuscript content",
        "sections": {"introduction": {"word_count": 100, "content": [(1, "intro")]}}
    }
    prompt = agent.build_prompt(context)
    assert "Test manuscript content" in prompt
    assert "JSON RESPONSE FORMAT" in prompt


@pytest.mark.asyncio
async def test_orchestrator_process_submission():
    """Test orchestrator submission processing"""
    with patch('app.agents.orchestrator.mongodb_service') as mock_db, \
         patch('app.agents.orchestrator.langgraph_workflow') as mock_workflow, \
         patch('app.agents.orchestrator.rate_limiter') as mock_limiter, \
         patch('app.agents.orchestrator.document_cache_service') as mock_cache:

        mock_db.get_submission = AsyncMock(return_value={
            "_id": "test123",
            "title": "test.pdf",
            "content": "test content"
        })
        mock_db.update_submission = AsyncMock()
        mock_workflow.execute_review = AsyncMock(return_value="Final report")
        mock_limiter.check_concurrent_processing = Mock()
        mock_limiter.release_processing = Mock()
        mock_cache.cache_submission = AsyncMock()

        result = await orchestrator.process_submission("test123")
        assert result["status"] == "completed"
        assert result["submission_id"] == "test123"


@pytest.mark.asyncio
async def test_orchestrator_handles_errors():
    """Test orchestrator error handling"""
    with patch('app.agents.orchestrator.mongodb_service') as mock_db, \
         patch('app.agents.orchestrator.rate_limiter') as mock_limiter:

        mock_db.get_submission = AsyncMock(return_value=None)
        mock_limiter.check_concurrent_processing = Mock()
        mock_limiter.release_processing = Mock()

        with pytest.raises(ValueError):
            await orchestrator.process_submission("invalid_id")


@pytest.mark.asyncio
async def test_agent_enhance_findings():
    """Test finding enhancement with positions"""
    agent = MethodologyAgent()
    critique = AgentCritique(
        agent_type="methodology",
        score=8.0,
        findings=[
            DetailedFinding(
                finding="Test",
                highlights=[TextHighlight(text="test", start_pos=0, end_pos=0, context="", issue_type="minor")],
                severity="minor",
                category="methodology"
            )
        ],
        recommendations=["Test"],
        confidence=0.9,
        bias_check="OK"
    )
    manuscript = "This is a test manuscript"
    sections = {"introduction": {"word_count": 5, "content": [(1, "This is a test")]}}

    agent._enhance_findings_with_positions(critique, manuscript, sections)
    assert len(critique.findings) > 0


@pytest.mark.asyncio
async def test_agent_error_handling(mock_genai_model):
    """Test agent handles LLM errors gracefully"""
    mock_genai_model.generate_content_async = AsyncMock(side_effect=Exception("LLM error"))

    with patch('app.agents.base_agent.genai.GenerativeModel', return_value=mock_genai_model):
        agent = MethodologyAgent()
        context = {"submission_id": "test", "content": "test"}

        with pytest.raises(Exception):
            await agent.execute_task(context)
