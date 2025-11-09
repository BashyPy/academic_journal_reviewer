import html
import logging
from typing import Any, Dict, List, Optional

from app.middleware.guardrail_middleware import apply_review_guardrails
from app.services.domain_detector import domain_detector
from app.services.issue_deduplicator import issue_deduplicator
from app.services.pdf_generator import pdf_generator


class SynthesisAgent:
    def __init__(self, llm_provider: Optional[str] = None):
        self.llm_provider = llm_provider

    async def generate_final_report(self, context: Dict[str, Any]) -> str:
        try:
            from app.services.llm_service import llm_service

            # Validate context and required keys
            if not isinstance(context, dict):
                logging.error("Invalid context type: expected dict, got %s", type(context))
                raise TypeError("context must be a dict")
            submission = context.get("submission")
            critiques = context.get("critiques")
            if submission is None or critiques is None:
                logging.warning(
                    "Context missing required keys: submission=%s, critiques=%s",
                    bool(submission),
                    bool(critiques),
                )
                raise KeyError("context must include 'submission' and 'critiques'")

            # Extract and deduplicate findings
            all_findings = []
            for critique in critiques:
                findings = critique.get("findings", [])
                if findings:
                    all_findings.extend(findings)

            # Deduplicate if findings exist
            if all_findings:
                unique_findings = issue_deduplicator.deduplicate_findings(all_findings)
                prioritized = issue_deduplicator.prioritize_issues(unique_findings)

                dedup_summary = f"""

DEDUPLICATED FINDINGS:
- Major Issues: {len(prioritized.get('major', []))}
- Moderate Issues: {len(prioritized.get('moderate', []))}
- Minor Issues: {len(prioritized.get('minor', []))}
"""
            else:
                dedup_summary = ""

            # Direct synthesis preserving line-by-line format
            synthesis_prompt = f"""
You are a senior academic editor. Synthesize the agent reviews into a professional report.

MANUSCRIPT TITLE: {submission.get('title', 'Unknown')}{dedup_summary}

AGENT REVIEWS (CONTAIN LINE-BY-LINE ANALYSIS):
{self._format_critiques_for_synthesis(critiques)}

GENERATE REVIEW WITH THIS EXACT STRUCTURE:

# Comprehensive Review Report

## Executive Summary
[2-3 paragraphs: overall assessment, key findings, decision]

## Detailed Findings

### Methodology Review
[Copy ALL line-by-line findings from Methodology Agent]
[Keep format: **Line X**: "quoted text" - Issue: [problem] - Fix: [solution]]

### Literature Review
[Copy ALL line-by-line findings from Literature Agent]
[Keep format: **Line X**: "quoted text" - Issue: [problem] - Fix: [solution]]

### Clarity & Presentation Review
[Copy ALL line-by-line findings from Clarity Agent]
[Keep format: **Line X**: "quoted text" - Issue: [problem] - Fix: [solution]]

### Ethics & Integrity Review
[Copy ALL line-by-line findings from Ethics Agent]
[Keep format: **Line X**: "quoted text" - Issue: [problem] - Fix: [solution]]

## Recommendations
[Top 5-10 actionable items with line references]

## Conclusion
[Final assessment and decision]

CRITICAL INSTRUCTIONS:
- PRESERVE ALL line numbers and quoted text EXACTLY as provided by agents
- Do NOT paraphrase or rewrite the findings
- Do NOT create new findings
- MAINTAIN the format: **Line X**: "quoted text" - Issue - Fix
"""

            # Use basic LLM service to preserve formatting
            response = await llm_service.generate_content(
                synthesis_prompt, self.llm_provider or "groq"
            )

            # Apply guardrails to final review
            sanitized_response = apply_review_guardrails(response)
            return sanitized_response

        except Exception:
            # Fallback to basic synthesis
            from app.services.llm_service import llm_service

            prompt = self.build_synthesis_prompt(context)
            response = await llm_service.generate_content(prompt, self.llm_provider or "groq")
            return apply_review_guardrails(response)

    async def generate_pdf_report(self, context: Dict[str, Any]) -> bytes:
        """Generate PDF version of the review report"""
        # Generate the final review content, log and re-raise on failure so callers can decide handling
        try:
            review_content = await self.generate_final_report(context)
        except Exception as exc:
            logging.exception("Failed to generate final report for PDF: %s", exc)
            raise

        submission_info = context.get("submission", {})

        # Generate PDF and validate result; log detailed error and re-raise to avoid returning invalid data
        try:
            pdf_buffer = pdf_generator.generate_pdf_report(review_content, submission_info)
            if pdf_buffer is None:
                raise RuntimeError("pdf_generator returned None instead of a buffer")
            return pdf_buffer.getvalue()
        except Exception as exc:
            logging.exception("Failed to generate PDF report: %s", exc)
            raise
        return pdf_buffer.getvalue()

    def build_synthesis_prompt(self, context: Dict[str, Any]) -> str:
        # Validate context and required keys to avoid KeyError later on
        if not isinstance(context, dict):
            logging.error(
                "Invalid context type for build_synthesis_prompt: expected dict, got %s",
                type(context),
            )
            raise TypeError("context must be a dict")

        submission = context.get("submission")
        critiques = context.get("critiques")

        if submission is None or critiques is None:
            logging.error(
                "Context missing required keys in build_synthesis_prompt: submission=%s, critiques=%s",
                bool(submission),
                bool(critiques),
            )
            raise KeyError("context must include 'submission' and 'critiques'")

        # Detect domain and get domain-specific configuration
        domain_info = domain_detector.detect_domain(submission)
        domain = domain_info["primary_domain"]
        weights = domain_detector.get_domain_specific_weights(domain)
        _ = domain_detector.get_domain_specific_criteria(domain)
        # Deduplicate findings across agents
        all_findings = []
        for critique in critiques:
            all_findings.extend(critique.get("findings", []))

        unique_findings = issue_deduplicator.deduplicate_findings(all_findings)
        prioritized_issues = issue_deduplicator.prioritize_issues(unique_findings)

        critiques_text = self._format_critiques_with_deduplication(critiques, prioritized_issues)
        overall_score = self._calculate_weighted_score(critiques, weights)
        decision = self._determine_decision(overall_score)

        return self._build_prompt_template(
            submission,
            critiques_text,
            overall_score,
            decision,
            prioritized_issues,
            domain_info,
        )

    def _format_critiques_with_deduplication(self, critiques, prioritized_issues) -> str:
        parts = []
        parts.append("AGENT SCORES:\n")
        parts.append(self._format_agent_scores(critiques))
        parts.append("\nTOP ISSUES WITH QUOTED TEXT:\n")

        major_issues = prioritized_issues.get("major", [])
        if major_issues:
            parts.append("\nMAJOR ISSUES (require immediate attention):\n")
            parts.append(self._format_issues_list(major_issues, quote_mode="full"))

        moderate_issues = prioritized_issues.get("moderate", [])
        if moderate_issues:
            parts.append(f"\nMODERATE ISSUES (top 5 of {len(moderate_issues)}):")
            parts.append("\n")
            parts.append(self._format_issues_list(moderate_issues[:5], quote_mode="snippet"))
            if len(moderate_issues) > 5:
                extra_count = len(moderate_issues) - 5
                parts.append(f"- Plus {extra_count} additional moderate issues across sections\n")

        minor_issues = prioritized_issues.get("minor", [])
        if minor_issues:
            parts.append(f"\nMINOR SUGGESTIONS ({len(minor_issues)} items): ")
            parts.append("Enhancement opportunities across sections\n")

        return "".join(parts)

    def _format_agent_scores(self, critiques) -> str:
        lines = []
        for critique in critiques:
            # Use helper to safely extract fields from dict-like or object-like critiques
            agent_type = self._get_field(critique, "agent_type", "")
            score = self._get_field(critique, "score", "")

            # Normalize and format values for display
            agent_label = str(agent_type).title() if agent_type is not None else ""
            # Keep numeric scores as-is and coerce others to string for stable output
            if isinstance(score, (int, float)):
                score_value = score
            else:
                try:
                    # attempt to parse numeric-like strings
                    score_value = float(score)
                    # if integer-like, display without decimal .0
                    if score_value.is_integer():
                        score_value = int(score_value)
                except Exception:
                    score_value = str(score)

            lines.append(f"- {agent_label}: {score_value}/10\n")
        return "".join(lines)

    def _get_field(self, item, field, default=None):
        if isinstance(item, dict):
            return item.get(field, default)
        return getattr(item, field, default)

    def _format_quote(self, highlights, quote_mode: str) -> str:
        if not highlights:
            return ""
        first = highlights[0]
        quote_text = self._get_field(first, "text", "") or getattr(first, "text", "") or ""
        if not quote_text:
            return ""
        # Normalize and escape to prevent XSS and remove problematic control characters
        import html
        import re

        # Normalize to string and drop non-printable/control characters
        normalized = str(quote_text)
        normalized = re.sub(r"[\x00-\x1f\x7f]", " ", normalized)

        # Use html.escape with quote=True to escape quotes and angle brackets
        if quote_mode == "full":
            safe = html.escape(normalized, quote=True)
            return f' Quote: "{safe}"'
        if quote_mode == "snippet":
            snippet_raw = normalized[:50] + "..." if len(normalized) > 50 else normalized
            safe_snip = html.escape(snippet_raw, quote=True)
            return f' Quote: "{safe_snip}"'
        return ""

    def _format_issues_list(self, issues, quote_mode: str = "none") -> str:
        """
        quote_mode: "full" -> include full quoted text if available
                    "snippet" -> include first ~50 chars of quote
                    "none" -> no quote
        """
        import html

        lines = []
        for issue in issues:
            text = self._get_field(issue, "finding")
            if text is None:
                text = str(issue)

            section = self._get_field(issue, "section", "unknown") or "unknown"
            line_ref = self._get_field(issue, "line_reference", "") or ""

            highlights = self._get_field(issue, "highlights", None)
            quoted_text = self._format_quote(highlights, quote_mode)

            safe_section = html.escape(str(section).title())
            safe_line_ref = html.escape(str(line_ref))
            safe_text = html.escape(str(text))

            lines.append(f"- [{safe_section}, Line {safe_line_ref}] {safe_text}{quoted_text}\n")
        return "".join(lines)

    def _calculate_weighted_score(self, critiques, weights: Dict[str, float]) -> float:
        total_score = total_weight = 0.0

        for critique in critiques:
            agent_type = self._normalize_agent_type(critique)
            score = self._parse_score_value(critique, agent_type)
            weight = self._determine_weight(critique, agent_type, weights)

            total_score += score * weight
            total_weight += weight

        return round((total_score / total_weight) if total_weight > 0 else 0.0, 1)

    def _normalize_agent_type(self, critique) -> str:
        raw_agent = self._get_field(critique, "agent_type", "")
        try:
            return str(raw_agent).strip().lower() if raw_agent is not None else ""
        except Exception:
            logging.exception("Failed to normalize agent_type: %r", raw_agent)
            return ""

    def _parse_score_value(self, critique, agent_type) -> float:
        raw_score = self._get_field(critique, "score", 0)
        try:
            if isinstance(raw_score, (int, float)):
                return float(raw_score)
            return float(str(raw_score).strip())
        except Exception:
            logging.warning(
                "Invalid score value %r for agent %s; defaulting to 0", raw_score, agent_type
            )
            return 0.0

    def _determine_weight(self, critique, agent_type, weights) -> float:
        raw_weight = critique.get("weight", None)
        if raw_weight is None:
            return weights.get(agent_type, 0.25)
        try:
            return float(raw_weight)
        except Exception:
            logging.warning(
                "Invalid weight %r for agent %s; using default weight for agent or 0.25",
                raw_weight,
                agent_type,
            )
            return weights.get(agent_type, 0.25)

    def _determine_decision(self, score: float) -> str:
        if score >= 8.0:
            return "Accept"
        if score >= 6.5:
            return "Minor Revisions"
        if score >= 4.0:
            return "Major Revisions"
        return "Reject"

    def _format_prioritized_section(self, prioritized_issues) -> str:
        """Format prioritized issues for prompt"""
        sections = []
        if prioritized_issues.get("major"):
            sections.append(f"### Major Issues ({len(prioritized_issues['major'])} items)")
            sections.append("[List all major issues with line references]")
        if prioritized_issues.get("moderate"):
            sections.append(f"### Moderate Issues ({len(prioritized_issues['moderate'])} items)")
            sections.append("[List top moderate issues with line references]")
        if prioritized_issues.get("minor"):
            sections.append(f"### Minor Suggestions ({len(prioritized_issues['minor'])} items)")
            sections.append("[Summarize minor suggestions]")
        return "\n".join(sections)

    def _build_prompt_template(  # pylint: disable=too-many-arguments
        self,
        submission,
        critiques_text,
        overall_score,
        decision,
        prioritized_issues,
        domain_info,
    ) -> str:
        _ = len(prioritized_issues.get("major", []))
        _ = len(prioritized_issues.get("moderate", []))
        safe_title = html.escape(str(submission.get("title", "Untitled")))
        safe_domain = html.escape(str(domain_info.get("primary_domain", "unknown")).title())
        safe_critiques_text = html.escape(critiques_text)

        return f"""
You are a senior academic editor. Synthesize the agent reviews into a professional report.

MANUSCRIPT: {safe_title}
DOMAIN: {safe_domain}
SCORE: {overall_score}/10 | DECISION: {decision}

AGENT FINDINGS (ALREADY CONTAIN LINE-BY-LINE ANALYSIS):
{safe_critiques_text}

GENERATE REVIEW WITH THIS STRUCTURE:
SCORE: {overall_score}/10 | DECISION: {decision}

AGENT FINDINGS (ALREADY CONTAIN LINE-BY-LINE ANALYSIS):
{critiques_text}

GENERATE REVIEW WITH THIS STRUCTURE:

# Comprehensive Review Report

## Executive Summary
[2-3 paragraphs summarizing overall assessment, score, and decision]

## Detailed Findings by Section

### Methodology Review
[Preserve all line-by-line findings from methodology agent]
[Format: **Line X**: "[quoted text]" - Issue: [problem] - Fix: [solution]]

### Literature Review
[Preserve all line-by-line findings from literature agent]
[Format: **Line X**: "[quoted text]" - Issue: [problem] - Fix: [solution]]

### Clarity & Presentation Review
[Preserve all line-by-line findings from clarity agent]
[Format: **Line X**: "[quoted text]" - Issue: [problem] - Fix: [solution]]

### Ethics & Integrity Review
[Preserve all line-by-line findings from ethics agent]
[Format: **Line X**: "[quoted text]" - Issue: [problem] - Fix: [solution]]

## Prioritized Issues
{self._format_prioritized_section(prioritized_issues)}

## Recommendations
[Synthesize top 5-10 actionable recommendations with line references]

## Conclusion
[Final assessment with decision rationale]

CRITICAL: Preserve ALL line numbers and quoted text from agent reviews. Do NOT create new findings.
"""

    def _format_domain_criteria(self, domain_criteria: Dict[str, List[str]]) -> str:
        lines = []
        for aspect, criteria in domain_criteria.items():
            criteria_text = ", ".join(criteria)
            lines.append(f"- {aspect.title()}: {criteria_text}")
        return "\n".join(lines)

    def _format_critiques_for_synthesis(self, critiques: List[Dict[str, Any]]) -> str:
        """Format critiques preserving line-by-line analysis"""
        formatted = []
        for critique in critiques:
            agent_type = critique.get("agent_type", "unknown")
            score = critique.get("score", 0)

            # Get findings with line-by-line format
            findings = critique.get("findings", [])
            findings_text = []

            for finding in findings:
                if isinstance(finding, dict):
                    finding_text = finding.get("finding", "")
                else:
                    finding_text = getattr(finding, "finding", str(finding))

                if finding_text:
                    findings_text.append(finding_text)

            # Format agent section
            agent_section = f"\n{agent_type.title()} Agent (Score: {score}/10):\n"
            if findings_text:
                agent_section += "\n".join(findings_text)
            else:
                agent_section += "No specific findings"

            formatted.append(agent_section)

        return "\n\n".join(formatted)
