from abc import ABC, abstractmethod
from typing import Any, Dict

import google.generativeai as genai

from app.core.config import settings
from app.models.schemas import AgentCritique, DetailedFinding, TextHighlight
from app.services.manuscript_analyzer import manuscript_analyzer
from app.services.text_analysis import TextAnalyzer
from app.utils.logger import get_logger

genai.configure(api_key=settings.GEMINI_API_KEY)


class BaseAgent(ABC):
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        self.logger = get_logger()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Returns the system prompt for the agent.
        This is an abstract method that must be implemented by subclasses.

        Returns:
            str: The system prompt that provides instructions to the model
        """

    async def execute_task(self, context: Dict[str, Any]) -> AgentCritique:
        submission_id = context.get("submission_id", "unknown")
        manuscript_content = context.get("content", "")

        self._log_start(submission_id, manuscript_content)

        try:
            sections = manuscript_analyzer.analyze_structure(manuscript_content)
            context["sections"] = sections

            prompt = self.build_prompt(context)
            response_text = await self._get_response(prompt, manuscript_content)

            critique = self.parse_response(response_text)

            self._log_completion(submission_id, critique)
        except Exception as e:
            self.logger.error(
                e,
                additional_info={
                    "agent_type": self.agent_type,
                    "submission_id": submission_id,
                    "action": "task_execution",
                },
            )
            raise

        self._enhance_findings_with_positions(critique, manuscript_content, sections)
        return critique

    def _log_start(self, submission_id: str, manuscript_content: str) -> None:
        self.logger.log_agent_activity(
            agent_type=self.agent_type,
            action="task_started",
            submission_id=submission_id,
            additional_info={"content_length": len(manuscript_content)},
        )

    async def _get_response(self, prompt: str, manuscript_content: str) -> str:
        # Use enhanced analysis for longer manuscripts
        if len(manuscript_content.split()) > 3000:
            # Import only if needed for long manuscripts
            try:
                from app.services.enhanced_llm_service import (  # pylint: disable=import-outside-toplevel
                    enhanced_llm_service,
                )

                response = await enhanced_llm_service.multi_pass_analysis(prompt, "detailed")
                return (
                    response
                    if isinstance(response, str)
                    else getattr(response, "text", str(response))
                )
            except ImportError:
                # Fallback to standard model if enhanced service unavailable
                response = await self.model.generate_content_async(prompt)
                return getattr(response, "text", response)

        response = await self.model.generate_content_async(prompt)
        return getattr(response, "text", response)

    def _log_completion(self, submission_id: str, critique: AgentCritique) -> None:
        self.logger.log_agent_activity(
            agent_type=self.agent_type,
            action="task_completed",
            submission_id=submission_id,
            additional_info={
                "score": critique.score,
                "findings_count": len(critique.findings),
                "confidence": critique.confidence,
            },
        )

    def _enhance_findings_with_positions(
        self, critique: AgentCritique, manuscript_content: str, sections: Dict[str, Any]
    ) -> None:
        for finding in critique.findings:
            if not hasattr(finding, "highlights"):
                continue

            validated_highlights = []
            for highlight in finding.highlights:
                start, end = TextAnalyzer.find_text_position(manuscript_content, highlight.text)
                line_num = manuscript_analyzer.find_line_number(manuscript_content, highlight.text)
                section = (
                    manuscript_analyzer.get_section_for_line(sections, line_num)
                    if line_num
                    else "unknown"
                )

                if start != 0 or end != 0:
                    highlight.start_pos = start
                    highlight.end_pos = end
                    context_text = TextAnalyzer.extract_context(manuscript_content, start, end)
                    highlight.context = (
                        f"Line {line_num}, {section.title()} section: {context_text}"
                    )
                    validated_highlights.append(highlight)

            finding.highlights = validated_highlights

    def build_prompt(self, context: Dict[str, Any]) -> str:
        system_prompt = self.get_system_prompt()
        manuscript_content = context.get("content", "")
        context.get("sections", {})

        # Add line numbers to manuscript
        lines = manuscript_content.split("\n")
        numbered_content = "\n".join([f"Line {i+1}: {line}" for i, line in enumerate(lines)])

        return f"""
{system_prompt}

NUMBERED MANUSCRIPT:
{numbered_content}

JSON RESPONSE FORMAT:
{{
    "score": <float 0-10>,
    "findings": [
        {{
            "finding": "**Line X**: \"exact quoted text\" - Issue: [problem] - Fix: [sol]",
            "highlights": [
                {{
                    "text": "exact quoted text",
                    "start_pos": 0,
                    "end_pos": 0,
                    "context": "Line X context",
                    "issue_type": "specific problem"
                }}
            ],
            "severity": "major|moderate|minor",
            "category": "{self.agent_type}",
            "section": "section name",
            "line_reference": "X"
        }}
    ],
    "recommendations": ["**Line X-Y**: specific change needed"],
    "confidence": <float 0-1>,
    "bias_check": "objective analysis"
}}
"""

    def parse_response(  # pylint: disable=too-many-locals
        self, response_text: str
    ) -> AgentCritique:
        import json  # pylint: disable=import-outside-toplevel
        import random  # pylint: disable=import-outside-toplevel

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]
            data = json.loads(json_str)

            findings = self._parse_findings(data)
            raw_score = data.get("score", 5.0)
            score_variance = random.uniform(-0.3, 0.3)
            adjusted_score = max(0.0, min(10.0, raw_score + score_variance))

            return AgentCritique(
                agent_type=self.agent_type,
                score=round(adjusted_score, 1),
                findings=findings,
                recommendations=data.get("recommendations", []),
                confidence=data.get("confidence", 0.0),
                bias_check=data.get("bias_check", "Analysis completed objectively"),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return AgentCritique(
                agent_type=self.agent_type,
                score=0.0,
                findings=[
                    DetailedFinding(
                        finding=f"Error parsing response: {str(e)}",
                        highlights=[],
                        severity="major",
                        category="system",
                    )
                ],
                recommendations=["Manual review required"],
                confidence=0.0,
                bias_check="Error in analysis",
            )

    def _parse_findings(self, data: Dict[str, Any]) -> list:
        """Extract findings from response data."""
        findings = []
        for f in data.get("findings", []):
            highlights = [
                TextHighlight(
                    text=h.get("text", ""),
                    start_pos=h.get("start_pos", 0),
                    end_pos=h.get("end_pos", 0),
                    context=h.get("context", ""),
                    issue_type=h.get("issue_type", ""),
                )
                for h in f.get("highlights", [])
            ]
            findings.append(
                DetailedFinding(
                    finding=f.get("finding", ""),
                    highlights=highlights,
                    severity=f.get("severity", "minor"),
                    category=f.get("category", "general"),
                )
            )
        return findings
