"""Synthesis agent tests"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.agents.synthesis_agent import SynthesisAgent


@pytest.mark.asyncio
async def test_synthesis_agent_generate_final_report():
    """Test synthesis agent report generation"""
    with patch('app.agents.synthesis_agent.mongodb_service') as mock_db, \
         patch('app.agents.synthesis_agent.llm_service') as mock_llm:

        mock_db.get_agent_tasks = AsyncMock(return_value=[
            {
                "agent_type": "methodology",
                "critique": {
                    "score": 8.0,
                    "findings": [],
                    "recommendations": ["Test rec"]
                }
            }
        ])

        mock_llm.generate_content = AsyncMock(return_value="Final comprehensive report")

        agent = SynthesisAgent()
        context = {
            "submission": {
                "_id": "test123",
                "title": "Test Paper",
                "content": "Test content"
            },
            "critiques": [
                {"agent_type": "methodology", "content": "Good", "score": 8}
            ]
        }

        result = await agent.generate_final_report(context)

        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_synthesis_agent_compile_critiques():
    """Test critique compilation"""
    agent = SynthesisAgent()

    critiques = [
        {"agent_type": "methodology", "content": "Good methodology", "score": 8},
        {"agent_type": "literature", "content": "Good literature", "score": 7}
    ]

    compiled = agent._compile_critiques(critiques)

    assert "methodology" in compiled.lower()
    assert "literature" in compiled.lower()


@pytest.mark.asyncio
async def test_synthesis_agent_calculate_overall_score():
    """Test overall score calculation"""
    agent = SynthesisAgent()

    critiques = [
        {"score": 8.0},
        {"score": 7.0},
        {"score": 9.0}
    ]

    score = agent._calculate_overall_score(critiques)

    assert 7.0 <= score <= 9.0


@pytest.mark.asyncio
async def test_synthesis_agent_handles_errors():
    """Test synthesis agent error handling"""
    with patch('app.agents.synthesis_agent.mongodb_service') as mock_db:
        mock_db.get_agent_tasks = AsyncMock(side_effect=Exception("DB error"))

        agent = SynthesisAgent()
        context = {
            "submission": {"_id": "test", "title": "Test", "content": "Test"},
            "critiques": []
        }

        result = await agent.generate_final_report(context)

        # Should return error message, not raise
        assert isinstance(result, str)
