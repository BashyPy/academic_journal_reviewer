"""Mock tests for agent modules"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock


class TestLangChainService:
    def test_init(self):
        from app.services.langchain_service import langchain_service
        assert langchain_service is not None

    def test_get_model(self):
        from app.services.langchain_service import langchain_service
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}):
            m = langchain_service.get_model("openai")
            assert m is not None


class TestLangGraphWorkflow:
    @pytest.mark.asyncio
    async def test_run_workflow(self):
        from app.services.langgraph_workflow import langgraph_workflow
        with patch.object(langgraph_workflow, 'workflow') as m:
            m.ainvoke = AsyncMock(return_value={"final_report": "test", "status": "completed"})
            r = await langgraph_workflow.run_workflow({"content": "test"})
            assert "final_report" in r


class TestBaseAgent:
    def test_init(self):
        from app.agents.base_agent import BaseAgent
        with patch.multiple(BaseAgent, __abstractmethods__=set()):
            agent = BaseAgent("test", "test_type")
            assert agent.name == "test"


class TestSpecialistAgents:
    @pytest.mark.asyncio
    async def test_methodology_agent(self):
        from app.agents.specialist_agents import MethodologyAgent
        with patch('app.agents.specialist_agents.langchain_service') as m:
            m.get_model = Mock(return_value=Mock(ainvoke=AsyncMock(return_value=Mock(content="score: 8\nsummary: good"))))
            agent = MethodologyAgent()
            r = await agent.analyze("test content", "medical")
            assert r is not None


class TestSynthesisAgent:
    @pytest.mark.asyncio
    async def test_synthesize(self):
        from app.agents.synthesis_agent import SynthesisAgent
        with patch('app.agents.synthesis_agent.langchain_service') as m:
            m.get_model = Mock(return_value=Mock(ainvoke=AsyncMock(return_value=Mock(content="# Report\nTest"))))
            agent = SynthesisAgent()
            critiques = [{"agent_type": "methodology", "score": 8, "summary": "good"}]
            r = await agent.synthesize(critiques, "Test", "medical")
            assert r is not None


class TestGuardrails:
    def test_check_content(self):
        from app.services.guardrails import guardrails
        r = guardrails.check_content("normal text")
        assert r["safe"]

    def test_check_sensitive(self):
        from app.services.guardrails import guardrails
        r = guardrails.check_sensitive_data("SSN: 123-45-6789")
        assert not r["safe"]


class TestTextAnalysis:
    def test_analyze_text(self):
        from app.services.text_analysis import text_analyzer
        r = text_analyzer.analyze("test text for analysis")
        assert "word_count" in r

    def test_extract_keywords(self):
        from app.services.text_analysis import text_analyzer
        k = text_analyzer.extract_keywords("machine learning algorithm")
        assert len(k) > 0


class TestManuscriptAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze(self):
        from app.services.manuscript_analyzer import manuscript_analyzer
        with patch('app.services.manuscript_analyzer.langchain_service') as m:
            m.get_model = Mock(return_value=Mock(ainvoke=AsyncMock(return_value=Mock(content="analysis result"))))
            r = await manuscript_analyzer.analyze_manuscript("content", "medical")
            assert r is not None


class TestLLMService:
    @pytest.mark.asyncio
    async def test_call_llm(self):
        from app.services.llm_service import llm_service
        with patch('app.services.llm_service.openai') as m:
            m.ChatCompletion.acreate = AsyncMock(return_value={"choices": [{"message": {"content": "response"}}]})
            r = await llm_service.call_llm("openai", "prompt")
            assert r is not None
