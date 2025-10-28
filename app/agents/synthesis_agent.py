from typing import Any, Dict

from app.services.issue_deduplicator import issue_deduplicator
from app.services.llm_service import llm_service


class SynthesisAgent:
    def __init__(self, llm_provider: str = None):
        self.llm_provider = llm_provider

    async def generate_final_report(self, context: Dict[str, Any]) -> str:
        # Use enhanced multi-pass analysis for detailed reviews
        from app.services.enhanced_llm_service import enhanced_llm_service

        try:
            # Try enhanced synthesis first
            response = await enhanced_llm_service.enhanced_synthesis(context)
            return response
        except Exception:
            # Fallback to standard synthesis
            prompt = self.build_synthesis_prompt(context)
            response = await llm_service.generate_content(prompt, self.llm_provider)
            return response

    def build_synthesis_prompt(self, context: Dict[str, Any]) -> str:
        submission = context["submission"]
        critiques = context["critiques"]

        # Deduplicate findings across agents
        all_findings = []
        for critique in critiques:
            all_findings.extend(critique.get("findings", []))

        unique_findings = issue_deduplicator.deduplicate_findings(all_findings)
        prioritized_issues = issue_deduplicator.prioritize_issues(unique_findings)

        critiques_text = self._format_critiques_with_deduplication(
            critiques, prioritized_issues
        )
        overall_score = self._calculate_weighted_score(critiques)
        decision = self._determine_decision(overall_score)
        weights = {
            "methodology": 0.3,
            "literature": 0.25,
            "clarity": 0.25,
            "ethics": 0.2,
        }

        return self._build_prompt_template(
            submission,
            critiques_text,
            overall_score,
            decision,
            weights,
            prioritized_issues,
        )

    def _format_critiques_with_deduplication(
        self, critiques, prioritized_issues
    ) -> str:
        critiques_text = "AGENT SCORES:\n"
        for critique in critiques:
            critiques_text += (
                f"- {critique['agent_type'].title()}: {critique['score']}/10\n"
            )

        critiques_text += "\nTOP ISSUES WITH QUOTED TEXT:\n"

        # Show major issues first with full detail
        major_issues = prioritized_issues.get("major", [])
        if major_issues:
            critiques_text += "\nMAJOR ISSUES (require immediate attention):\n"
            for issue in major_issues:
                text = issue.finding if hasattr(issue, "finding") else str(issue)
                section = (
                    getattr(issue, "section", "unknown")
                    if hasattr(issue, "section")
                    else "unknown"
                )
                line_ref = (
                    getattr(issue, "line_reference", "")
                    if hasattr(issue, "line_reference")
                    else ""
                )

                # Include quoted text if available
                quoted_text = ""
                if hasattr(issue, "highlights") and issue.highlights:
                    quoted_text = f' Quote: "{issue.highlights[0].text}"'

                critiques_text += (
                    f"- [{section.title()}, Line {line_ref}] {text}{quoted_text}\n"
                )

        # Show top 5 moderate issues with detail, summarize rest
        moderate_issues = prioritized_issues.get("moderate", [])
        if moderate_issues:
            critiques_text += f"\nMODERATE ISSUES (top 5 of {len(moderate_issues)}):\n"
            for issue in moderate_issues[:5]:
                text = issue.finding if hasattr(issue, "finding") else str(issue)
                section = (
                    getattr(issue, "section", "unknown")
                    if hasattr(issue, "section")
                    else "unknown"
                )
                line_ref = (
                    getattr(issue, "line_reference", "")
                    if hasattr(issue, "line_reference")
                    else ""
                )

                quoted_text = ""
                if hasattr(issue, "highlights") and issue.highlights:
                    quoted_text = f' Quote: "{issue.highlights[0].text[:50]}..."'

                critiques_text += (
                    f"- [{section.title()}, Line {line_ref}] {text}{quoted_text}\n"
                )

            if len(moderate_issues) > 5:
                critiques_text += f"- Plus {len(moderate_issues) - 5} additional moderate issues across sections\n"

        # Summarize minor issues
        minor_issues = prioritized_issues.get("minor", [])
        if minor_issues:
            critiques_text += f"\nMINOR SUGGESTIONS ({len(minor_issues)} items): Enhancement opportunities across sections\n"

        return critiques_text

    def _calculate_weighted_score(self, critiques) -> float:
        weights = {
            "methodology": 0.3,
            "literature": 0.25,
            "clarity": 0.25,
            "ethics": 0.2,
        }
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
    ) -> str:
        major_count = len(prioritized_issues.get("major", []))
        moderate_count = len(prioritized_issues.get("moderate", []))
        minor_count = len(prioritized_issues.get("minor", []))

        return f"""
Generate a professional, section-specific academic review report.

MANUSCRIPT: {submission['title']}
OVERALL SCORE: {overall_score}/10 | DECISION: {decision}
ISSUE SUMMARY: {major_count} major, {moderate_count} moderate, {minor_count} minor

DEDUPLICATED ANALYSIS:
{critiques_text}

CREATE STRUCTURED REPORT:

## Executive Summary
- Score: {overall_score}/10, Decision: {decision}
- Brief assessment highlighting main strengths and key improvement areas

## Critical Issues ({major_count} items)
- List each critical issue with exact quoted text
- Include line numbers and section references
- Provide immediate action required

## Important Improvements ({moderate_count} items)
- Show top 5 most important issues with specific examples:
  * Quote exact problematic text
  * Reference line numbers and sections
  * Suggest specific improvements
- Group remaining issues by section if more than 5

## Minor Suggestions ({minor_count} items)
- List optional improvements with section references
- Focus on enhancement opportunities

## Manuscript Strengths
- Highlight specific good practices with examples
- Quote well-written passages where applicable
- Acknowledge methodological strengths

## Section-Specific Action Items
1. **Abstract**: [Specific line-by-line changes needed]
2. **Methods**: [Exact additions/modifications required]
3. **Results**: [Specific improvements with line references]
4. **Discussion**: [Targeted enhancements needed]

## Score Breakdown
Methodology: {weights['methodology']*100}% | Literature: {weights['literature']*100}% | Clarity: {weights['clarity']*100}% | Ethics: {weights['ethics']*100}%

Prioritize showing exact quoted text for top issues. Limit moderate issues to 5 detailed examples plus grouped summary.
"""
