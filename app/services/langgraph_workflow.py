import asyncio
import html
from typing import Any, Dict, List, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.specialist_agents import (
    ClarityAgent,
    EthicsAgent,
    LiteratureAgent,
    MethodologyAgent,
)
from app.services.checkpoint_service import checkpoint_service
from app.services.domain_detector import DomainDetector
from app.services.issue_deduplicator import IssueDeduplicator
from app.services.langchain_service import langchain_service
from app.services.manuscript_analyzer import (
    manuscript_analyzer,
)
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
    retry_count: int
    errors: List[Dict[str, Any]]


class EnhancedLangGraphWorkflow:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.domain_detector = DomainDetector()
        self.issue_deduplicator = IssueDeduplicator()
        self.memory = MemorySaver()
        self.logger = get_logger()
        self.workflow = self._build_workflow()

    from langgraph.graph import CompiledStateGraph  # Add this import at the top if not present

    def _build_workflow(self) -> "CompiledStateGraph":
        """Construct the StateGraph."""
        workflow = StateGraph(EnhancedReviewState)

        # register nodes in one place to simplify future changes
        self._register_nodes(workflow)

        # connect edges and set entry point separately for clearer intent
        self._connect_edges(workflow)

        return workflow.compile(checkpointer=self.memory)

    def _register_nodes(self, workflow: StateGraph) -> None:
        """Register workflow nodes."""
        workflow.add_node("initialize", self._initialize_review)
        workflow.add_node("create_embeddings", self._create_embeddings)
        workflow.add_node("parallel_reviews", self._parallel_reviews)
        workflow.add_node("synthesize", self._synthesize_report)

    def _connect_edges(self, workflow: StateGraph) -> None:
        """Wire the workflow transitions with conditional routing."""
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "create_embeddings")
        workflow.add_edge("create_embeddings", "parallel_reviews")

        # Add conditional routing based on review quality
        workflow.add_conditional_edges(
            "parallel_reviews",
            self._should_retry_reviews,
            {"synthesize": "synthesize", "retry": "parallel_reviews"},
        )
        workflow.add_edge("synthesize", END)

    async def _initialize_review(self, state: EnhancedReviewState) -> EnhancedReviewState:
        try:
            # Save checkpoint
            await checkpoint_service.save_checkpoint(
                state["submission_id"], dict(state), "initialize"
            )
            content = state.get("content", "")
            title = state.get("title", "")
            # attempt to detect domain safely
            domain_result = self.domain_detector.detect_domain({"content": content, "title": title})
            domain = (
                domain_result.get("primary_domain", "general")
                if isinstance(domain_result, dict)
                else "general"
            )
            if not domain or domain == "general":
                # fallback and log a warning rather than failing
                e = ValueError("Domain detector returned invalid value")
                self.logger.error(
                    e,
                    additional_info={
                        "stage": "initialize_review",
                        "detected_domain": repr(domain_result),
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
        except Exception as e:  # pylint: disable=broad-exception-caught
            import traceback  # pylint: disable=import-outside-toplevel

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
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append({"stage": "initialize_review", "error": str(e)})
            return state

    async def _create_embeddings(self, state: EnhancedReviewState) -> EnhancedReviewState:
        try:
            # Save checkpoint
            await checkpoint_service.save_checkpoint(
                state["submission_id"], dict(state), "embeddings"
            )
            # Try to create embeddings, but don't fail if it doesn't work
            if hasattr(langchain_service, "embeddings") and langchain_service.embeddings:
                await langchain_service.create_document_embeddings(
                    state["content"], state["metadata"]
                )
                state["embeddings_created"] = True
            else:
                state["embeddings_created"] = False
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(e, additional_info={"stage": "create_embeddings"})
            state["embeddings_created"] = False
        return state

    async def _parallel_reviews(self, state: EnhancedReviewState) -> EnhancedReviewState:

        domain = state.get("domain", "general")
        weights = self.domain_detector.get_domain_specific_weights(domain)
        sections = manuscript_analyzer.analyze_structure(state["content"])
        manuscript_length = len(state["content"].split())
        section_info = self._get_section_info(sections)

        tasks = [
            self._run_review("methodology", 8000, "domain", state, section_info, manuscript_length),
            self._run_review("literature", 8000, "domain", state, section_info, manuscript_length),
            self._run_review("clarity", 6000, "chain", state, section_info, manuscript_length),
            self._run_review("ethics", 6000, "multi", state, section_info, manuscript_length),
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:  # pylint: disable=broad-exception-caught
            import traceback  # pylint: disable=import-outside-toplevel

            self.logger.error(e, additional_info={"stage": "parallel_reviews"})
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(
                {
                    "stage": "parallel_reviews",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            results = [
                "Error in methodology review",
                "Error in literature review",
                "Error in clarity review",
                "Error in ethics review",
            ]

        reviewed_results = self._handle_review_results(results, state)

        state["methodology_critique"] = {
            "agent_type": "methodology",
            "content": reviewed_results["methodology"],
            "score": self._extract_score(reviewed_results["methodology"]),
            "weight": weights.get("methodology", 0.25),
        }
        state["literature_critique"] = {
            "agent_type": "literature",
            "content": reviewed_results["literature"],
            "score": self._extract_score(reviewed_results["literature"]),
            "weight": weights.get("literature", 0.25),
        }
        state["clarity_critique"] = {
            "agent_type": "clarity",
            "content": reviewed_results["clarity"],
            "score": self._extract_score(reviewed_results["clarity"]),
            "weight": weights.get("clarity", 0.25),
        }
        state["ethics_critique"] = {
            "agent_type": "ethics",
            "content": reviewed_results["ethics"],
            "score": self._extract_score(reviewed_results["ethics"]),
            "weight": weights.get("ethics", 0.25),
        }

        return state

    def _get_section_info(self, sections: Dict[str, Any]) -> str:
        def _get_line_range(content_lines: List[Any]) -> str:
            if not content_lines:
                return "0-0"
            line_numbers = [
                line[0] for line in content_lines if isinstance(line, (list, tuple)) and line
            ]
            if not line_numbers:
                return "0-0"
            return f"{min(line_numbers)}-{max(line_numbers)}"

        return "\n".join(
            [
                f"- {name.title()}: {data['word_count']} words "
                f"(lines {_get_line_range(data.get('content', []))})"
                for name, data in sections.items()
                if data.get("content")
            ]
        )

    async def _run_review(
        self,
        kind: str,
        max_len: int,
        method: str,
        state: EnhancedReviewState,
        section_info: str,
        manuscript_length: int,
    ) -> str:
        try:
            content = (
                state["content"][:max_len] if len(state["content"]) > max_len else state["content"]
            )
            lines = content.split("\n")
            numbered_text = "\n".join([f"Line {i+1}: {line}" for i, line in enumerate(lines)])
            enhanced_context = {**state["context"], "content": numbered_text}

            if method == "domain":
                return await self._domain_runner(
                    kind, numbered_text, enhanced_context, state, section_info, manuscript_length
                )
            elif method == "chain":
                return await self._chain_runner(
                    kind, numbered_text, enhanced_context, section_info, manuscript_length, state
                )
            elif method == "multi":
                return await self._multi_runner(
                    kind, numbered_text, enhanced_context, section_info, manuscript_length, state
                )
            else:
                safe_kind = html.escape(str(kind).title())
                return f"{safe_kind} review failed due to internal error."
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(e, additional_info={"review_type": kind})
            safe_kind = html.escape(str(kind).title())
            return f"{safe_kind} review failed due to internal error."

    async def _domain_runner(
        self,
        kind: str,
        numbered_text: str,
        enhanced_context: Dict[str, Any],
        state: EnhancedReviewState,
        section_info: str,
        manuscript_length: int,
    ) -> str:

        agent_map = {
            "methodology": MethodologyAgent(),
            "literature": LiteratureAgent(),
        }
        agent = agent_map.get(kind)
        if not agent:
            return await langchain_service.domain_aware_review(
                numbered_text, state["domain"], kind, enhanced_context
            )

        system_prompt = agent.get_system_prompt()
        rich_prompt = f"""
{system_prompt}

MANUSCRIPT STRUCTURE:
{section_info}
Total: {manuscript_length} words

NUMBERED MANUSCRIPT:
Title: {state['title']}
Domain: {state['domain']}

{numbered_text}

You MUST follow the format specified in your system prompt above.
Provide 10-15 line-specific findings with exact quotes and line numbers.
"""
        return await langchain_service.invoke_with_rag(rich_prompt, context=enhanced_context)

    async def _chain_runner(
        self,
        kind: str,
        numbered_text: str,
        enhanced_context: Dict[str, Any],
        section_info: str,
        manuscript_length: int,
        state: EnhancedReviewState,
    ) -> str:

        if kind == "clarity":
            clarity_agent = ClarityAgent()
            system_prompt = clarity_agent.get_system_prompt()
            prompt = f"""
{system_prompt}

MANUSCRIPT STRUCTURE:
{section_info}
Total: {manuscript_length} words

NUMBERED MANUSCRIPT:
Title: {state['title']}
Domain: {state['domain']}

{numbered_text}

You MUST follow the format specified in your system prompt above.
Provide 10-15 line-specific findings with exact quotes and line numbers.
"""
            return await langchain_service.chain_of_thought_analysis(prompt, enhanced_context)
        return await langchain_service.chain_of_thought_analysis(numbered_text, enhanced_context)

    async def _multi_runner(
        self,
        kind: str,
        numbered_text: str,
        enhanced_context: Dict[str, Any],
        section_info: str,
        manuscript_length: int,
        state: EnhancedReviewState,
    ) -> str:

        if kind == "ethics":
            ethics_agent = EthicsAgent()
            system_prompt = ethics_agent.get_system_prompt()
            prompt = f"""
{system_prompt}

MANUSCRIPT STRUCTURE:
{section_info}
Total: {manuscript_length} words

NUMBERED MANUSCRIPT:
Title: {state['title']}
Domain: {state['domain']}

{numbered_text}

You MUST follow the format specified in your system prompt above.
Provide 10-15 line-specific findings with exact quotes and line numbers.
"""
            return await langchain_service.multi_model_consensus(prompt, enhanced_context)
        return await langchain_service.multi_model_consensus(numbered_text, enhanced_context)

    def _handle_review_results(
        self, results: List[Any], state: EnhancedReviewState
    ) -> Dict[str, str]:
        keys = ["methodology", "literature", "clarity", "ethics"]
        reviewed_results = {}
        for k, res in zip(keys, results):
            if isinstance(res, Exception):
                import traceback  # pylint: disable=import-outside-toplevel

                self.logger.error(res, additional_info={"review_type": k})
                state.setdefault("errors", []).append(
                    {
                        "stage": "parallel_reviews",
                        "review_type": k,
                        "error": str(res),
                        "traceback": traceback.format_exc(),
                    }
                )
                reviewed_results[k] = f"{k.title()} review failed due to internal error."
            else:
                reviewed_results[k] = res
        return reviewed_results

    async def _synthesize_report(self, state: EnhancedReviewState) -> EnhancedReviewState:
        try:
            # Save checkpoint
            await checkpoint_service.save_checkpoint(
                state["submission_id"], dict(state), "synthesize"
            )
            # Use the synthesis agent for final report generation
            from app.agents.synthesis_agent import (  # pylint: disable=import-outside-toplevel
                SynthesisAgent,
            )
            from app.services.domain_detector import (  # pylint: disable=import-outside-toplevel
                domain_detector,
            )

            synthesis_agent = SynthesisAgent()

            # Detect domain and get domain-specific configuration
            submission_data = {
                "title": state["title"],
                "content": state["content"],
            }
            domain_info = domain_detector.detect_domain(submission_data)

            # Prepare enriched context for synthesis agent
            context = {
                "submission": {
                    "title": state["title"],
                    "content": state["content"],
                    "_id": state["submission_id"],
                    "domain": domain_info.get("primary_domain", "general"),
                    "metadata": state.get("metadata", {}),
                },
                "critiques": [
                    state["methodology_critique"],
                    state["literature_critique"],
                    state["clarity_critique"],
                    state["ethics_critique"],
                ],
                "domain_info": domain_info,
            }

            # Generate final report using synthesis agent's rich formatting
            final_report = await synthesis_agent.generate_final_report(context)
            state["final_report"] = final_report

        except Exception as e:  # pylint: disable=broad-exception-caught
            import traceback  # pylint: disable=import-outside-toplevel

            self.logger.error(
                e,
                additional_info={
                    "stage": "synthesize_report",
                    "message": "Exception during synthesize_report",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            # preserve exception info in state for observability
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(
                {
                    "stage": "synthesize_report",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            # Provide a basic fallback report
            state["final_report"] = (
                f"Review synthesis failed: {str(e)}. "
                f"Individual agent reviews completed successfully."
            )

        return state

    def _extract_score(self, response: str) -> int:
        import re  # pylint: disable=import-outside-toplevel

        score_match = re.search(r"Score:\s*(\d+)", response)
        return int(score_match.group(1)) if score_match else 7

    def _format_critiques(self, critiques: List[Dict[str, Any]]) -> str:
        formatted = []
        for critique in critiques:
            formatted.append(f"{critique['agent_type'].title()}: {critique['content'][:500]}...")
        return "\n\n".join(formatted)

    async def execute_review(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            initial_state = {
                "submission_id": str(submission_data.get("_id", "unknown")),
                "content": submission_data.get("content", ""),
                "title": submission_data.get("title", ""),
                "metadata": submission_data.get("metadata", {}),
                "methodology_critique": {},
                "literature_critique": {},
                "clarity_critique": {},
                "ethics_critique": {},
                "final_report": "",
                "context": {},
                "embeddings_created": False,
                "retry_count": 0,
                "errors": [],
            }

            config = {
                "configurable": {"thread_id": str(submission_data.get("_id", "unknown"))},
                "recursion_limit": 50,
            }
            # Try to load checkpoint first
            checkpoint = await checkpoint_service.load_checkpoint(
                str(submission_data.get("_id", "unknown"))
            )

            if checkpoint:
                self.logger.info(f"Resuming from checkpoint: {submission_data.get('_id')}")
                initial_state.update(checkpoint)

            final_state = await self.workflow.ainvoke(initial_state, config)

            # Delete checkpoint on success
            await checkpoint_service.delete_checkpoint(str(submission_data.get("_id", "unknown")))

            return {
                "final_report": final_state.get("final_report", "Review completed with errors"),
                "domain": final_state.get("domain", "general"),
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            import traceback  # pylint: disable=import-outside-toplevel

            self.logger.error(
                e,
                additional_info={
                    "stage": "execute_review",
                    "message": "Exception during execute_review",
                    "submission_id": submission_data.get("_id"),
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            return {
                "final_report": "Review failed due to system error. Please try again or contact support.",
                "domain": "general",
            }

    def _should_retry_reviews(self, state: EnhancedReviewState) -> str:
        """Determine if reviews need retry based on quality checks."""

        def _trigger_retry(reason: str, agent_type: str) -> str:
            self.logger.warning(f"Retry needed: {agent_type} {reason}")
            state["retry_count"] = state.get("retry_count", 0) + 1
            return "retry"

        # Only retry once to avoid infinite loops
        if state.get("retry_count", 0) >= 1:
            return "synthesize"

        critiques = [
            state.get("methodology_critique", {}),
            state.get("literature_critique", {}),
            state.get("clarity_critique", {}),
            state.get("ethics_critique", {}),
        ]

        for critique in critiques:
            content = critique.get("content", "")
            agent_type = critique.get("agent_type", "unknown")
            score = critique.get("score", 7)

            if "failed due to internal error" in content:
                return _trigger_retry("failed", agent_type)
            if len(content) < 100:
                return _trigger_retry(f"too short ({len(content)} chars)", agent_type)
            if "Line" not in content and "line" not in content.lower():
                return _trigger_retry("missing line references", agent_type)
            if score == 7 and "Score: 7" not in content:
                return _trigger_retry("score not found in content", agent_type)

        return "synthesize"


langgraph_workflow = EnhancedLangGraphWorkflow()
