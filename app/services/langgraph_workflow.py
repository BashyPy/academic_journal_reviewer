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
    retry_count: int


class EnhancedLangGraphWorkflow:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.domain_detector = DomainDetector()
        self.issue_deduplicator = IssueDeduplicator()
        self.memory = MemorySaver()
        self.logger = get_logger()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
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

    def _initialize_review(self, state: EnhancedReviewState) -> EnhancedReviewState:
        try:
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
                self.logger.error(
                    "Domain detector returned invalid value, defaulting to 'general'",
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
            state.setdefault("errors", []).append({"stage": "initialize_review", "error": str(e)})
            return state

    async def _create_embeddings(self, state: EnhancedReviewState) -> EnhancedReviewState:
        try:
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

    async def _parallel_reviews(  # pylint: disable=too-many-locals
        self, state: EnhancedReviewState
    ) -> EnhancedReviewState:
        # Import native agents to leverage their rich prompts
        from app.agents.specialist_agents import (  # pylint: disable=import-outside-toplevel
            ClarityAgent,
            EthicsAgent,
            LiteratureAgent,
            MethodologyAgent,
        )
        from app.services.manuscript_analyzer import (  # pylint: disable=import-outside-toplevel
            manuscript_analyzer,
        )

        # Analyze manuscript structure for context
        sections = manuscript_analyzer.analyze_structure(state["content"])
        manuscript_length = len(state["content"].split())

        # Create section summary
        section_info = "\n".join(
            [
                f"- {name.title()}: {data['word_count']} words "
                f"(lines {min([l[0] for l in data['content']] or [0])}-"
                f"{max([l[0] for l in data['content']] or [0])})"
                for name, data in sections.items()
                if data["content"]
            ]
        )

        # Small method-specific runners using native agent prompts
        async def _domain_runner(
            kind: str, numbered_text: str, enhanced_context: Dict[str, Any]
        ) -> str:
            # Get native agent system prompt
            agent_map = {
                "methodology": MethodologyAgent(),
                "literature": LiteratureAgent(),
            }
            agent = agent_map.get(kind)
            if not agent:
                return await langchain_service.domain_aware_review(
                    numbered_text, state["domain"], kind, enhanced_context
                )

            # Build rich prompt using native agent's system prompt
            system_prompt = agent.get_system_prompt()
            rich_prompt = f"""
{system_prompt}

MANUSCRIPT STRUCTURE:
{section_info}
Total: {manuscript_length} words

REVIEW REQUIREMENTS:
- Reference specific sections and line numbers
- Quote exact text for each issue
- Prioritize by severity: major (critical flaws) > moderate (improvements) > minor (suggestions)
- Provide section-specific recommendations
- Focus on your expertise area

NUMBERED MANUSCRIPT:
Title: {state['title']}
Domain: {state['domain']}

{numbered_text}

Provide LINE-BY-LINE analysis with:
1. Score (0-10) with justification
2. Detailed findings with quoted text and line references
3. Severity classification (major/moderate/minor)
4. Section-specific recommendations
5. Confidence level (0-1)
6. Bias check confirmation
"""
            return await langchain_service.invoke_with_rag(rich_prompt, context=enhanced_context)

        async def _chain_runner(
            kind: str, numbered_text: str, enhanced_context: Dict[str, Any]
        ) -> str:
            if kind == "clarity":
                # Use native ClarityAgent prompt
                clarity_agent = ClarityAgent()
                system_prompt = clarity_agent.get_system_prompt()
                prompt = f"""
{system_prompt}

MANUSCRIPT STRUCTURE:
{section_info}
Total: {manuscript_length} words

REVIEW REQUIREMENTS:
- Reference specific sections and line numbers
- Quote exact unclear passages
- Prioritize by severity: major (critical clarity issues) > moderate (improvements) > minor (suggestions)
- Provide concrete improvement suggestions
- Focus on clarity, not stylistic preferences

NUMBERED MANUSCRIPT:
Title: {state['title']}
Domain: {state['domain']}

{numbered_text}

Provide LINE-BY-LINE clarity assessment with:
1. Score (0-10) based on communication effectiveness
2. Specific unclear passages with quotes and line numbers
3. Logical flow and organization issues
4. Technical accuracy concerns
5. Figure/table clarity assessment
6. Concrete recommendations for improvement
7. Confidence level and bias check
"""
                return await langchain_service.chain_of_thought_analysis(prompt, enhanced_context)
            return await langchain_service.chain_of_thought_analysis(
                numbered_text, enhanced_context
            )

        async def _multi_runner(
            kind: str, numbered_text: str, enhanced_context: Dict[str, Any]
        ) -> str:
            if kind == "ethics":
                # Use native EthicsAgent prompt
                ethics_agent = EthicsAgent()
                system_prompt = ethics_agent.get_system_prompt()
                prompt = f"""
{system_prompt}

MANUSCRIPT STRUCTURE:
{section_info}
Total: {manuscript_length} words

REVIEW REQUIREMENTS:
- Reference specific sections and line numbers
- Quote exact text showing ethical concerns
- Prioritize by severity: major (critical ethical issues) > moderate (concerns) > minor (suggestions)
- Provide practical guidance for compliance
- Consider cultural and institutional context

NUMBERED MANUSCRIPT:
Title: {state['title']}
Domain: {state['domain']}

{numbered_text}

Provide LINE-BY-LINE ethical evaluation with:
1. Score (0-10) based on ethical compliance
2. Specific ethical concerns with quoted evidence
3. Informed consent and privacy assessment
4. Conflict of interest evaluation
5. Research integrity indicators
6. Practical recommendations for improvement
7. Confidence level and bias check
"""
                return await langchain_service.multi_model_consensus(prompt, enhanced_context)
            return await langchain_service.multi_model_consensus(numbered_text, enhanced_context)

        async def _run(kind: str, max_len: int, method: str) -> str:
            try:
                content = (
                    state["content"][:max_len]
                    if len(state["content"]) > max_len
                    else state["content"]
                )
                # Add line numbers to content
                lines = content.split("\n")
                numbered_text = "\n".join([f"Line {i+1}: {line}" for i, line in enumerate(lines)])
                enhanced_context = {**state["context"], "content": numbered_text}

                runner_map = {
                    "domain": _domain_runner,
                    "chain": _chain_runner,
                    "multi": _multi_runner,
                }
                runner = runner_map.get(method)
                if not runner:
                    return f"{kind.title()} review failed due to internal error."

                return await runner(kind, numbered_text, enhanced_context)
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.error(e, additional_info={"review_type": kind})
                return f"{kind.title()} review failed due to internal error."

        # Create tasks for all reviews using the helper to reduce duplicated logic
        tasks = [
            _run("methodology", 8000, "domain"),
            _run("literature", 8000, "domain"),
            _run("clarity", 6000, "chain"),
            _run("ethics", 6000, "multi"),
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:  # pylint: disable=broad-exception-caught
            import traceback  # pylint: disable=import-outside-toplevel

            self.logger.error(e, additional_info={"stage": "parallel_reviews"})
            state.setdefault("errors", []).append(
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

        # Normalize results and record any exceptions
        import traceback  # pylint: disable=import-outside-toplevel

        keys = ["methodology", "literature", "clarity", "ethics"]
        reviewed_results = {}
        for k, res in zip(keys, results):
            if isinstance(res, Exception):
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

    async def _synthesize_report(self, state: EnhancedReviewState) -> EnhancedReviewState:
        try:
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
            self.logger.error(e, additional_info={"stage": "synthesize_report"})
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
            formatted.append(
                f"{critique['agent_type'].title()}: " f"{critique['content'][:500]}..."
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
                retry_count=0,
            )

            config = {
                "configurable": {"thread_id": str(submission_data.get("_id", "unknown"))},
                "recursion_limit": 50,
            }
            final_state = await self.workflow.ainvoke(initial_state, config)
            return {
                "final_report": final_state.get("final_report", "Review completed with errors"),
                "domain": final_state.get("domain", "general"),
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                e,
                additional_info={
                    "stage": "execute_review",
                    "submission_id": submission_data.get("_id"),
                },
            )
            return "Review failed due to system error. " "Please try again or contact support."

    def _should_retry_reviews(self, state: EnhancedReviewState) -> str:
        """Determine if reviews need retry based on quality checks."""
        # Check if any reviews failed or are too short
        critiques = [
            state.get("methodology_critique", {}),
            state.get("literature_critique", {}),
            state.get("clarity_critique", {}),
            state.get("ethics_critique", {}),
        ]

        for critique in critiques:
            content = critique.get("content", "")
            if "failed due to internal error" in content or len(content) < 100:
                # Only retry once to avoid infinite loops
                retry_count = state.get("retry_count", 0)
                if retry_count < 1:
                    state["retry_count"] = retry_count + 1
                    return "retry"

        return "synthesize"


langgraph_workflow = EnhancedLangGraphWorkflow()
