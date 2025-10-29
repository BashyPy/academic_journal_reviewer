from typing import Any, Dict, List, Optional

from app.services.issue_deduplicator import issue_deduplicator
from app.services.llm_service import llm_service
from app.services.domain_detector import domain_detector
from app.middleware.guardrail_middleware import apply_review_guardrails


class SynthesisAgent:
    def __init__(self, llm_provider: Optional[str] = None):
        self.llm_provider = llm_provider

    async def generate_final_report(self, context: Dict[str, Any]) -> str:
        # Use enhanced multi-pass analysis for detailed reviews
        from app.services.enhanced_llm_service import enhanced_llm_service

        try:
            # Try enhanced synthesis first
            response = await enhanced_llm_service.enhanced_synthesis(context)
        except Exception:
            # Fallback to standard synthesis
            prompt = self.build_synthesis_prompt(context)
            response = await llm_service.generate_content(prompt, self.llm_provider)
        
        # Apply guardrails to final review
        return apply_review_guardrails(response)

    def build_synthesis_prompt(self, context: Dict[str, Any]) -> str:
        submission = context["submission"]
        critiques = context["critiques"]

        # Detect domain and get domain-specific configuration
        domain_info = domain_detector.detect_domain(submission)
        domain = domain_info["primary_domain"]
        weights = domain_detector.get_domain_specific_weights(domain)
        domain_criteria = domain_detector.get_domain_specific_criteria(domain)

        # Deduplicate findings across agents
        all_findings = []
        for critique in critiques:
            all_findings.extend(critique.get("findings", []))

        unique_findings = issue_deduplicator.deduplicate_findings(all_findings)
        prioritized_issues = issue_deduplicator.prioritize_issues(unique_findings)

        critiques_text = self._format_critiques_with_deduplication(
            critiques, prioritized_issues
        )
        overall_score = self._calculate_weighted_score(critiques, weights)
        decision = self._determine_decision(overall_score)

        return self._build_prompt_template(
            submission,
            critiques_text,
            overall_score,
            decision,
            weights,
            prioritized_issues,
            domain_info,
            domain_criteria,
        )

    def _format_critiques_with_deduplication(
        self, critiques, prioritized_issues
    ) -> str:
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
            parts.append(f"\nMODERATE ISSUES (top 5 of {len(moderate_issues)}):\n")
            parts.append(self._format_issues_list(moderate_issues[:5], quote_mode="snippet"))
            if len(moderate_issues) > 5:
                parts.append(f"- Plus {len(moderate_issues) - 5} additional moderate issues across sections\n")

        minor_issues = prioritized_issues.get("minor", [])
        if minor_issues:
            parts.append(f"\nMINOR SUGGESTIONS ({len(minor_issues)} items): Enhancement opportunities across sections\n")

        return "".join(parts)

    def _format_agent_scores(self, critiques) -> str:
        lines = []
        for critique in critiques:
            # safe access for dict-like critique
            agent_type = critique.get("agent_type") if isinstance(critique, dict) else getattr(critique, "agent_type", "")
            score = critique.get("score") if isinstance(critique, dict) else getattr(critique, "score", "")
            lines.append(f"- {str(agent_type).title()}: {score}/10\n")
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
        if quote_mode == "full":
            return f' Quote: "{quote_text}"'
        if quote_mode == "snippet":
            snippet = quote_text[:50] + "..." if len(quote_text) > 50 else quote_text
            return f' Quote: "{snippet}"'
        return ""

    def _format_issues_list(self, issues, quote_mode: str = "none") -> str:
        """
        quote_mode: "full" -> include full quoted text if available
                    "snippet" -> include first ~50 chars of quote
                    "none" -> no quote
        """
        lines = []
        for issue in issues:
            text = self._get_field(issue, "finding")
            if text is None:
                text = str(issue)

            section = self._get_field(issue, "section", "unknown") or "unknown"
            line_ref = self._get_field(issue, "line_reference", "") or ""

            highlights = self._get_field(issue, "highlights", None)
            quoted_text = self._format_quote(highlights, quote_mode)

            lines.append(f"- [{str(section).title()}, Line {line_ref}] {text}{quoted_text}\n")
        return "".join(lines)

    def _calculate_weighted_score(self, critiques, weights: Dict[str, float]) -> float:
        total_score = total_weight = 0.0

        for critique in critiques:
            agent_type = (critique.get("agent_type") or "").lower()
            score = float(critique.get("score", 0) or 0)
            weight = weights.get(agent_type, sum(weights.values()) / len(weights))
            total_score += score * weight
            total_weight += weight

        return round((total_score / total_weight) if total_weight > 0 else 0.0, 1)

    def _determine_decision(self, score: float) -> str:
        if score >= 8.0:
            return "Accept"
        elif score >= 6.5:
            return "Minor Revisions"
        elif score >= 4.0:
            return "Major Revisions"
        return "Reject"

    def _build_prompt_template(
        self,
        submission,
        critiques_text,
        overall_score,
        decision,
        weights,
        prioritized_issues,
        domain_info,
        domain_criteria,
    ) -> str:
        major_count = len(prioritized_issues.get("major", []))
        moderate_count = len(prioritized_issues.get("moderate", []))
        minor_count = len(prioritized_issues.get("minor", []))

        domain = domain_info["primary_domain"]
        confidence = domain_info["confidence"]
        
        return f"""
Generate a professional, domain-specific academic review report with standardized issue explanations.

MANUSCRIPT: {submission['title']}
DOMAIN: {domain.title()} (confidence: {confidence:.2f})
OVERALL SCORE: {overall_score}/10 | DECISION: {decision}
ISSUE SUMMARY: {major_count} major, {moderate_count} moderate, {minor_count} minor

DEDUPLICATED ANALYSIS:
{critiques_text}

CREATE STRUCTURED REPORT WITH RIGOROUS STANDARDS:

## Executive Summary
- Score: {overall_score}/10, Decision: {decision}
- Brief assessment highlighting main strengths and key improvement areas (max 2 paragraphs)

## Critical Issues ({major_count} items)
For each critical issue, provide EXACTLY 2 paragraphs:
- Paragraph 1: Identify the specific problem with exact quoted text and line references
- Paragraph 2: Explain the impact and provide concrete solution/action required

## Important Improvements ({moderate_count} items)
For each improvement (top 5 detailed), provide AT MOST 2 paragraphs:
- Paragraph 1: Quote problematic text with section/line reference and explain the issue
- Paragraph 2: Suggest specific improvement with rationale (optional if issue is self-evident)
- Group remaining issues by section with 1 paragraph summaries

## Minor Suggestions ({minor_count} items)
- List with 1 paragraph explanations maximum
- Focus on enhancement opportunities with section references

## Manuscript Strengths
- Highlight specific practices with examples (1-2 paragraphs total)
- Quote well-written passages where applicable

## Section-Specific Action Items
1. **Abstract**: [Specific changes needed - 1 paragraph]
2. **Methods**: [Exact additions/modifications - 1 paragraph]
3. **Results**: [Specific improvements - 1 paragraph]
4. **Discussion**: [Targeted enhancements - 1 paragraph]

## Score Breakdown ({domain.title()} Domain Weighting)
Methodology: {weights['methodology']*100:.0f}% | Literature: {weights['literature']*100:.0f}% | Clarity: {weights['clarity']*100:.0f}% | Ethics: {weights['ethics']*100:.0f}%

## Domain-Specific Focus Areas
{self._format_domain_criteria(domain_criteria)}

STRICT FORMATTING RULES:
- Critical issues: EXACTLY 2 paragraphs each
- Important improvements: AT MOST 2 paragraphs each
- Minor suggestions: 1 paragraph maximum each
- Include exact quoted text and line references for all issues
- Apply {domain.title()} domain standards and expectations
- Ensure explanations are concise, rigorous, and actionable
"""

    def _format_domain_criteria(self, domain_criteria: Dict[str, List[str]]) -> str:
        lines = []
        for aspect, criteria in domain_criteria.items():
            criteria_text = ", ".join(criteria)
            lines.append(f"- {aspect.title()}: {criteria_text}")
        return "\n".join(lines)
