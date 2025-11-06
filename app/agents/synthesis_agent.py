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
            from app.services.langchain_service import langchain_service
            from app.services.llm_service import llm_service

            submission = context["submission"]
            critiques = context["critiques"]

            # Advanced synthesis using multi-step LangChain workflow
            # Step 1: Initial synthesis with RAG
            initial_synthesis_prompt = f"""
Perform initial synthesis of academic manuscript review:

Title: {submission.get('title', 'Unknown')}
Full Content: {submission.get('content', '')}

Agent Reviews:
{self._format_critiques_for_synthesis(critiques)}

Create comprehensive analysis focusing on:
1. Overall manuscript quality assessment
2. Critical issues identification with evidence
3. Strengths and weaknesses analysis
4. Domain-specific evaluation criteria
"""

            initial_response = await langchain_service.invoke_with_rag(
                initial_synthesis_prompt, context=submission, use_memory=False
            )

            # Step 2: Enhanced synthesis with chain-of-thought
            enhanced_synthesis_prompt = f"""
Based on the initial analysis, create a detailed professional review report:

Initial Analysis:
{initial_response}

Original Manuscript:
Title: {submission.get('title', 'Unknown')}
Content: {submission.get('content', '')}

Agent Reviews:
{self._format_critiques_for_synthesis(critiques)}

Generate a structured academic review with:
1. Executive summary with scores and decision
2. Critical issues with exact quotes and solutions
3. Important improvements with detailed recommendations
4. Minor suggestions with section references
5. Manuscript strengths with specific examples
6. Section-specific action items
7. Domain-appropriate scoring breakdown

Ensure professional academic tone and comprehensive coverage.
"""

            # Use chain-of-thought for final synthesis
            final_response = await langchain_service.chain_of_thought_analysis(
                enhanced_synthesis_prompt, submission
            )

            # Apply guardrails to final review
            sanitized_response = apply_review_guardrails(final_response)
            return sanitized_response

        except Exception:
            # Fallback to basic synthesis if LangChain fails
            from app.services.llm_service import llm_service

            prompt = self.build_synthesis_prompt(context)
            response = await llm_service.generate_content(prompt, self.llm_provider)
            return apply_review_guardrails(response)

    async def generate_pdf_report(self, context: Dict[str, Any]) -> bytes:
        """Generate PDF version of the review report"""
        review_content = await self.generate_final_report(context)
        submission_info = context.get("submission", {})

        pdf_buffer = pdf_generator.generate_pdf_report(review_content, submission_info)
        return pdf_buffer.getvalue()

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

        critiques_text = self._format_critiques_with_deduplication(critiques, prioritized_issues)
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
            # safe access for dict-like critique
            agent_type = (
                critique.get("agent_type")
                if isinstance(critique, dict)
                else getattr(critique, "agent_type", "")
            )
            score = (
                critique.get("score")
                if isinstance(critique, dict)
                else getattr(critique, "score", "")
            )
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
        if score >= 6.5:
            return "Minor Revisions"
        if score >= 4.0:
            return "Major Revisions"
        return "Reject"

    def _build_prompt_template(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        submission,
        critiques_text,
        overall_score,
        decision,
        weights,  # pylint: disable=unused-argument
        prioritized_issues,
        domain_info,
        domain_criteria,  # pylint: disable=unused-argument
    ) -> str:
        # Issue counts available if needed for future enhancements
        _ = len(prioritized_issues.get("major", []))
        _ = len(prioritized_issues.get("moderate", []))
        _ = len(prioritized_issues.get("minor", []))

        domain = domain_info["primary_domain"]
        _ = domain_info["confidence"]

        content = submission.get("content", "")
        lines = content.split("\n")
        numbered_content = "\n".join([f"Line {i+1}: {line}" for i, line in enumerate(lines)])

        return f"""
Generate a COMPREHENSIVE LINE-BY-LINE academic review report.

MANUSCRIPT: {submission['title']}
DOMAIN: {domain.title()}
SCORE: {overall_score}/10 | DECISION: {decision}

NUMBERED MANUSCRIPT:
{numbered_content}

AGENT FINDINGS:
{critiques_text}

GENERATE REVIEW WITH THIS EXACT STRUCTURE:

# Detailed Professional Review Report

## Introduction
[2-3 paragraphs on manuscript context and review scope]

## Summary of Key Findings
- [Bullet point findings with specific numbers from manuscript]
- [Include exact data, percentages, sample sizes]

## Methodological Approach
[2-3 paragraphs analyzing methods, tools, and techniques used]

## Line-by-Line Review

### Abstract Section
**Line X**: "[exact quoted text]"
- Issue: [specific problem]
- Recommendation: [concrete fix]

**Line Y**: "[exact quoted text]"
- Issue: [specific problem]
- Recommendation: [concrete fix]

### Introduction Section
**Line X**: "[exact quoted text]"
- Issue: [specific problem]
- Recommendation: [concrete fix]

[Continue for ALL sections: Methods, Results, Discussion, Conclusion]

### Methods Section
**Line X**: "[exact quoted text]"
- Issue: [specific problem]
- Recommendation: [concrete fix]

### Results Section
**Line X**: "[exact quoted text]"
- Issue: [specific problem]
- Recommendation: [concrete fix]

### Discussion Section
**Line X**: "[exact quoted text]"
- Issue: [specific problem]
- Recommendation: [concrete fix]

### References Section
**Line X**: "[exact quoted text]"
- Issue: [specific problem]
- Recommendation: [concrete fix]

## Implications and Future Directions
[2-3 paragraphs]

## Strengths and Limitations

### Strengths
1. [Strength with line reference]: [explanation]
2. [Strength with line reference]: [explanation]

### Limitations
1. [Limitation with line reference]: [explanation and fix]
2. [Limitation with line reference]: [explanation and fix]

## Recommendations
1. **Line X-Y**: [specific change needed]
2. **Line X-Y**: [specific change needed]

## Conclusion
[2-3 paragraphs with final assessment]

CRITICAL REQUIREMENTS:
- Quote EXACT text with LINE NUMBERS for every issue
- Provide SPECIFIC recommendations for each quoted line
- Review EVERY section line-by-line
- Include at least 15-20 line-specific issues
- Format: **Line X**: "exact text" then Issue and Recommendation
"""

    def _format_domain_criteria(self, domain_criteria: Dict[str, List[str]]) -> str:
        lines = []
        for aspect, criteria in domain_criteria.items():
            criteria_text = ", ".join(criteria)
            lines.append(f"- {aspect.title()}: {criteria_text}")
        return "\n".join(lines)

    def _format_critiques_for_synthesis(self, critiques: List[Dict[str, Any]]) -> str:
        """Format critiques for LangChain synthesis"""
        formatted = []
        for critique in critiques:
            agent_type = critique.get("agent_type", "unknown")
            content = critique.get("content", "No content")
            score = critique.get("score", 0)
            formatted.append(f"{agent_type.title()} Agent (Score: {score}/10):\n{content}\n")
        return "\n".join(formatted)
