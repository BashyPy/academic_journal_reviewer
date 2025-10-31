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
        """Construct the StateGraph by delegating node registration and edge wiring to helper methods for clarity."""
        workflow = StateGraph(EnhancedReviewState)

        # register nodes in one place to simplify future changes
        self._register_nodes(workflow)

        # connect edges and set entry point separately for clearer intent
        self._connect_edges(workflow)

        return workflow.compile(checkpointer=self.memory)

    def _register_nodes(self, workflow: StateGraph) -> None:
        """Register workflow nodes (actions) in a single method to improve discoverability."""
        workflow.add_node("initialize", self._initialize_review)
        workflow.add_node("create_embeddings", self._create_embeddings)
        workflow.add_node("parallel_reviews", self._parallel_reviews)
        workflow.add_node("synthesize", self._synthesize_report)

    def _connect_edges(self, workflow: StateGraph) -> None:
        """Wire the workflow transitions and set the entry point."""
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "create_embeddings")
        workflow.add_edge("create_embeddings", "parallel_reviews")
        workflow.add_edge("parallel_reviews", "synthesize")
        workflow.add_edge("synthesize", END)

    def _initialize_review(self, state: EnhancedReviewState) -> EnhancedReviewState:
        try:
            content = state.get("content", "")
            # attempt to detect domain safely
            domain = self.domain_detector.detect_domain(content)
            if not domain or not isinstance(domain, str):
                # fallback and log a warning rather than failing
                self.logger.error(
                    "Domain detector returned invalid value, defaulting to 'general'",
                    additional_info={
                        "stage": "initialize_review",
                        "detected_domain": repr(domain),
                    },
                )
                domain = "general"

            metadata = state.get("metadata", {}) or {}
            title = state.get("title", "Unknown")

            state["domain"] = domain
            state["context"] = {
                "domain": domain,
                "metadata": metadata,
                "title": title,
            }
            state["embeddings_created"] = False
            return state
        except Exception as e:
            import traceback

            self.logger.error(
                "Exception during initialize_review",
                additional_info={
                    "stage": "initialize_review",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            # keep state consistent and non-empty so downstream nodes don't crash
            state["domain"] = state.get("domain") or "general"
            state["context"] = {
                "domain": state["domain"],
                "metadata": state.get("metadata") or {},
                "title": state.get("title", "Unknown"),
            }
            state["embeddings_created"] = False
            # preserve exception info in state for observability
            state.setdefault("errors", []).append(
                {"stage": "initialize_review", "error": str(e)}
            )
            return state

    async def _create_embeddings(
        self, state: EnhancedReviewState
    ) -> EnhancedReviewState:
        try:
            await langchain_service.create_document_embeddings(
                state["content"], state["metadata"]
            )
            state["embeddings_created"] = True
        except Exception as e:
            self.logger.error(e, additional_info={"stage": "create_embeddings"})
            state["embeddings_created"] = False
        return state

    async def _parallel_reviews(
        self, state: EnhancedReviewState
    ) -> EnhancedReviewState:
        async def methodology_review():
            try:
                return await langchain_service.domain_aware_review(
                    state["content"], state["domain"], "methodology", state["context"]
                )
            except Exception as e:
                self.logger.error(e, additional_info={"review_type": "methodology"})
                return "Methodology review failed due to internal error."

        async def literature_review():
            try:
                return await langchain_service.domain_aware_review(
                    state["content"], state["domain"], "literature", state["context"]
                )
            except Exception as e:
                self.logger.error(e, additional_info={"review_type": "literature"})
                return "Literature review failed due to internal error."

        async def clarity_review():
            try:
                prompt = f"Assess clarity and presentation of this {state['domain']} manuscript"
                return await langchain_service.chain_of_thought_analysis(
                    prompt, state["context"]
                )
            except Exception as e:
                self.logger.error(e, additional_info={"review_type": "clarity"})
                return "Clarity review failed due to internal error."

        async def ethics_review():
            try:
                prompt = f"Evaluate ethical considerations for this {state['domain']} manuscript"
                consensus = await langchain_service.multi_model_consensus(
                    prompt, state["context"]
                )
                if isinstance(consensus, dict):
                    return consensus.get(
                        "consensus_analysis", "No consensus analysis returned"
                    )
                return str(consensus)
            except Exception as e:
                self.logger.error(e, additional_info={"review_type": "ethics"})
                return "Ethics review failed due to internal error."

        # Execute all reviews in parallel with error handling
        try:
            methodology_result, literature_result, clarity_result, ethics_result = (
                await asyncio.gather(
                    methodology_review(),
                    literature_review(),
                    clarity_review(),
                    ethics_review(),
                    return_exceptions=True,
                )
            )
        except Exception as e:
            import traceback

            # log and record the exception that prevented gather from completing
            self.logger.error(e, additional_info={"stage": "parallel_reviews"})
            state.setdefault("errors", []).append(
                {
                    "stage": "parallel_reviews",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            methodology_result = "Error in methodology review"
            literature_result = "Error in literature review"
            clarity_result = "Error in clarity review"
            ethics_result = "Error in ethics review"

        # Handle individual review errors: log, record detailed traceback, and replace with safe message
        import traceback

        reviewed_results = {
            "methodology": methodology_result,
            "literature": literature_result,
            "clarity": clarity_result,
            "ethics": ethics_result,
        }

        for review_type, result in reviewed_results.items():
            if isinstance(result, Exception):
                # log detailed exception and add to state errors for observability
                self.logger.error(result, additional_info={"review_type": review_type})
                state.setdefault("errors", []).append(
                    {
                        "stage": "parallel_reviews",
                        "review_type": review_type,
                        "error": str(result),
                        "traceback": traceback.format_exc(),
                    }
                )
                # replace exception with a safe, user-friendly message
                reviewed_results[review_type] = (
                    f"{review_type.title()} review failed due to internal error."
                )

        # Assign finalized (non-exception) results back into structured critiques
        state["methodology_critique"] = {
            "agent_type": "methodology",
            "content": reviewed_results["methodology"],
            "score": self._extract_score(reviewed_results["methodology"]),
        }
        state["literature_critique"] = {
            "agent_type": "literature",
            "content": reviewed_results["literature"],
            "score": self._extract_score(reviewed_results["literature"]),
        }
        state["clarity_critique"] = {
            "agent_type": "clarity",
            "content": reviewed_results["clarity"],
            "score": self._extract_score(reviewed_results["clarity"]),
        }
        state["ethics_critique"] = {
            "agent_type": "ethics",
            "content": reviewed_results["ethics"],
            "score": self._extract_score(reviewed_results["ethics"]),
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
        try:
            initial_state = EnhancedReviewState(
                submission_id=str(submission_data.get("_id", "unknown")),
                content=submission_data.get("content", ""),
                title=submission_data.get("title", "Unknown Document"),
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

            config = {
                "configurable": {
                    "thread_id": str(submission_data.get("_id", "unknown"))
                }
            }
            final_state = await self.workflow.ainvoke(initial_state, config)
            return final_state.get("final_report", "Review completed with errors")
        except Exception as e:
            self.logger.error(
                e,
                additional_info={
                    "stage": "execute_review",
                    "submission_id": submission_data.get("_id"),
                },
            )
            return "Review failed due to system error. Please try again or contact support."


langgraph_workflow = EnhancedLangGraphWorkflow()
