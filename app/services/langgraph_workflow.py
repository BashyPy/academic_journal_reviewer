import asyncio
from typing import Any, Dict, List, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.services.domain_detector import DomainDetector
from app.services.issue_deduplicator import IssueDeduplicator
from app.services.langchain_service import langchain_service
from app.utils.logger import get_logger


class EnhancedReviewState(TypedDict):
    submission_id: str
    content: str
    title: str
    metadata: Dict[str, Any]
    domain: str
    methodology_critique: Dict[str, Any]
    literature_critique: Dict[str, Any]
    clarity_critique: Dict[str, Any]
    ethics_critique: Dict[str, Any]
    final_report: str
    context: Dict[str, Any]
    embeddings_created: bool


class EnhancedLangGraphWorkflow:
    def __init__(self):
        self.domain_detector = DomainDetector()
        self.issue_deduplicator = IssueDeduplicator()
        self.memory = MemorySaver()
        self.logger = get_logger()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(EnhancedReviewState)

        workflow.add_node("initialize", self._initialize_review)
        workflow.add_node("create_embeddings", self._create_embeddings)
        workflow.add_node("parallel_reviews", self._parallel_reviews)
        workflow.add_node("synthesize", self._synthesize_report)

        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "create_embeddings")
        workflow.add_edge("create_embeddings", "parallel_reviews")
        workflow.add_edge("parallel_reviews", "synthesize")
        workflow.add_edge("synthesize", END)

        return workflow.compile(checkpointer=self.memory)

    def _initialize_review(
        self, state: EnhancedReviewState
    ) -> EnhancedReviewState:
        domain = self.domain_detector.detect_domain(state["content"])
        state["domain"] = domain
        state["context"] = {
            "domain": domain,
            "metadata": state["metadata"],
            "title": state["title"],
        }
        state["embeddings_created"] = False
        return state

    async def _create_embeddings(
        self, state: EnhancedReviewState
    ) -> EnhancedReviewState:
        await langchain_service.create_document_embeddings(
            state["content"], state["metadata"]
        )
        state["embeddings_created"] = True
        return state

    async def _parallel_reviews(
        self, state: EnhancedReviewState
    ) -> EnhancedReviewState:
        async def methodology_review():
            return await langchain_service.domain_aware_review(
                state["content"], state["domain"], "methodology", state["context"]
            )

        async def literature_review():
            return await langchain_service.domain_aware_review(
                state["content"], state["domain"], "literature", state["context"]
            )

        async def clarity_review():
            prompt = f"Assess clarity and presentation of this {state['domain']} manuscript"
            return await langchain_service.chain_of_thought_analysis(
                prompt, state["context"]
            )

        async def ethics_review():
            prompt = f"Evaluate ethical considerations for this {state['domain']} manuscript"
            consensus = await langchain_service.multi_model_consensus(
                prompt, state["context"]
            )
            return consensus["consensus_analysis"]

        # Execute all reviews in parallel
        methodology_result, literature_result, clarity_result, ethics_result = await asyncio.gather(
            methodology_review(),
            literature_review(), 
            clarity_review(),
            ethics_review()
        )

        state["methodology_critique"] = {
            "agent_type": "methodology",
            "content": methodology_result,
            "score": self._extract_score(methodology_result),
        }
        state["literature_critique"] = {
            "agent_type": "literature",
            "content": literature_result,
            "score": self._extract_score(literature_result),
        }
        state["clarity_critique"] = {
            "agent_type": "clarity",
            "content": clarity_result,
            "score": self._extract_score(clarity_result),
        }
        state["ethics_critique"] = {
            "agent_type": "ethics",
            "content": ethics_result,
            "score": self._extract_score(ethics_result),
        }
        
        return state

    async def _synthesize_report(
        self, state: EnhancedReviewState
    ) -> EnhancedReviewState:
        critiques = [
            state["methodology_critique"],
            state["literature_critique"],
            state["clarity_critique"],
            state["ethics_critique"],
        ]

        deduplicated_critiques = self.issue_deduplicator.deduplicate_issues(critiques)

        synthesis_prompt = f"""
        Create comprehensive review report for {state['domain']} manuscript:
        Title: {state['title']}
        
        Agent Reviews: {self._format_critiques(deduplicated_critiques)}
        
        Provide executive summary, detailed analysis, and actionable recommendations.
        """

        final_report = await langchain_service.invoke_with_rag(
            synthesis_prompt, context=state["context"], use_memory=False
        )

        state["final_report"] = final_report
        return state

    def _extract_score(self, response: str) -> int:
        import re

        score_match = re.search(r"Score:\s*(\d+)", response)
        return int(score_match.group(1)) if score_match else 7

    def _format_critiques(self, critiques: List[Dict[str, Any]]) -> str:
        formatted = []
        for critique in critiques:
            formatted.append(
                f"{critique['agent_type'].title()}: {critique['content'][:500]}..."
            )
        return "\n\n".join(formatted)

    async def execute_review(self, submission_data: Dict[str, Any]) -> str:
        initial_state = EnhancedReviewState(
            submission_id=submission_data["_id"],
            content=submission_data["content"],
            title=submission_data["title"],
            metadata=submission_data.get("file_metadata", {}),
            domain="",
            methodology_critique={},
            literature_critique={},
            clarity_critique={},
            ethics_critique={},
            final_report="",
            context={},
            embeddings_created=False,
        )

        config = {"configurable": {"thread_id": submission_data["_id"]}}
        final_state = await self.workflow.ainvoke(initial_state, config)
        return final_state["final_report"]


langgraph_workflow = EnhancedLangGraphWorkflow()
