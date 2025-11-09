from abc import ABC, abstractmethod
from typing import Any, Dict

import google.generativeai as genai

from app.core.config import settings
from app.models.schemas import AgentCritique, DetailedFinding, TextHighlight
from app.services.manuscript_analyzer import manuscript_analyzer
from app.services.text_analysis import TextAnalyzer
from app.utils.logger import get_logger

genai.configure(api_key=settings.GEMINI_API_KEY)

# Model configuration
DEFAULT_MODEL_NAME = "gemini-2.0-flash-exp"


class BaseAgent(ABC):
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.model = genai.GenerativeModel(DEFAULT_MODEL_NAME)
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

        try:
            self._enhance_findings_with_positions(critique, manuscript_content, sections)
        except Exception as e:
            # Log enhancement errors but do not fail the overall task; ensure we preserve the critique result.
            try:
                self.logger.error(
                    e,
                    additional_info={
                        "agent_type": self.agent_type,
                        "submission_id": submission_id,
                        "action": "enhance_findings",
                    },
                )
            except Exception:
                # Fallback logging if structured logger fails
                self.logger.warning(f"Failed enhancing findings: {e}")
        return critique

    def _log_start(self, submission_id: str, manuscript_content: str) -> None:
        try:
            content_length = len(manuscript_content) if manuscript_content else 0
            self.logger.log_agent_activity(
                agent_type=self.agent_type,
                action="task_started",
                submission_id=submission_id,
                additional_info={"content_length": content_length},
            )
        except Exception as e:
            self.logger.warning(f"Failed to log task start: {e}")

    async def _get_response(self, prompt: str, _manuscript_content: str) -> str:
        response = await self.model.generate_content_async(prompt)
        return str(response.text)

    def _log_completion(self, submission_id: str, critique: AgentCritique) -> None:
        self.logger.log_agent_activity(
            agent_type=self.agent_type,
            action="task_completed",
            submission_id=submission_id,
            additional_info={
                "score": critique.score,
                "findings_count": len(critique.findings),
            },
        )

    def _enhance_findings_with_positions(
        self, critique: AgentCritique, manuscript_content: str, sections: Dict[str, Any]
    ) -> None:
        for finding in critique.findings:
            if not finding.highlights:
                continue

            validated_highlights = []
            for highlight in finding.highlights:
                start, end = TextAnalyzer.find_text_position(manuscript_content, highlight.text)
                line_num = TextAnalyzer.find_line_number(manuscript_content, highlight.text)
                section = (
                    manuscript_analyzer.get_section_for_line(sections, line_num)
                    if line_num
                    else "unknown"
                )

                if start != 0 or end != 0:
                    context_text = TextAnalyzer.extract_context(manuscript_content, start, end)
                    validated_highlights.append(
                        TextHighlight(
                            text=highlight.text,
                            start=start,
                            end=end,
                            context=f"Line {line_num}, {section.title()} section: {context_text}",
                        )
                    )

            finding.highlights = validated_highlights

    def build_prompt(self, context: Dict[str, Any]) -> str:
        system_prompt = self.get_system_prompt()
        manuscript_content = context.get("content", "")
        _ = context.get("sections", {})

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
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(e, additional_info={"json_str": json_str[:100]})
                raise ValueError(f"Invalid JSON response: {str(e)}") from e

            if not isinstance(data, dict):
                raise ValueError("Response data must be a dictionary")

            findings = self._parse_findings(data)
            raw_score = data.get("score", 5.0)
            if not isinstance(raw_score, (int, float)):
                raw_score = 5.0
            score_variance = random.uniform(-0.3, 0.3)
            adjusted_score = max(0.0, min(10.0, raw_score + score_variance))

            return AgentCritique(
                agent_type=self.agent_type,
                score=round(adjusted_score, 1),
                summary=data.get("bias_check", "Analysis completed objectively"),
                findings=findings,
                strengths=data.get("recommendations", [])[:3],
                weaknesses=[f.get("finding", "") for f in data.get("findings", [])[:3]],
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return AgentCritique(
                agent_type=self.agent_type,
                score=0.0,
                summary=f"Error in analysis: {str(e)}",
                findings=[
                    DetailedFinding(
                        issue=f"Error parsing response: {str(e)}",
                        severity="major",
                        highlights=[],
                    )
                ],
                strengths=[],
                weaknesses=["Manual review required"],
            )

    def _parse_findings(self, data: Dict[str, Any]) -> list:
        """Extract findings from response data."""
        findings = []
        for f in data.get("findings", []):
            highlights = [
                TextHighlight(
                    text=h.get("text", ""),
                    start=h.get("start_pos", 0),
                    end=h.get("end_pos", 0),
                    context=h.get("context", ""),
                )
                for h in f.get("highlights", [])
            ]
            findings.append(
                DetailedFinding(
                    issue=f.get("finding", ""),
                    severity=f.get("severity", "minor"),
                    location=f.get("section", ""),
                    suggestion=f.get("finding", ""),
                    highlights=highlights,
                )
            )
        return findings
