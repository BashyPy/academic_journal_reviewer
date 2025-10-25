from typing import Any, Dict

from app.services.llm_service import llm_service


class SynthesisAgent:
    def __init__(self, llm_provider: str = None):
        self.llm_provider = llm_provider

    async def generate_final_report(self, context: Dict[str, Any]) -> str:
        prompt = self.build_synthesis_prompt(context)
        response = await llm_service.generate_content(prompt, self.llm_provider)
        return response

    def build_synthesis_prompt(self, context: Dict[str, Any]) -> str:
        submission = context["submission"]
        critiques = context["critiques"]

        critiques_text = ""
        for critique in critiques:
            critiques_text += f"""
## {critique['agent_type'].upper()} AGENT REVIEW
Score: {critique['score']}/10
Confidence: {critique['confidence']}

### Findings:
{chr(10).join(f"- {finding}" for finding in critique['findings'])}

### Recommendations:
{chr(10).join(f"- {rec}" for rec in critique['recommendations'])}

"""

        return f"""
You are a Synthesis Agent responsible for compiling a comprehensive final review report.

MANUSCRIPT TITLE: {submission['title']}

SPECIALIST AGENT REVIEWS:
{critiques_text}

Please generate a comprehensive final review report in markdown format that includes:

1. **Executive Summary** - Overall assessment and recommendation
2. **Detailed Analysis** - Synthesis of all agent findings
3. **Strengths** - What the manuscript does well
4. **Areas for Improvement** - Key issues to address
5. **Specific Recommendations** - Actionable steps for authors
6. **Overall Score** - Weighted average with justification
7. **Decision Recommendation** - Accept/Revise/Reject with rationale

The report should be professional, constructive, and actionable for journal editors and authors.
"""
