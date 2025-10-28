from typing import Any, Dict

from app.services.llm_service import llm_service


class EnhancedLLMService:
    def __init__(self):
        self.primary_provider = "groq"  # Fast for initial analysis
        self.detailed_provider = "gemini"  # More thorough for synthesis

    async def multi_pass_analysis(
        self, prompt: str, analysis_type: str = "standard"
    ) -> str:
        """Perform multi-pass analysis for more detailed reviews."""

        if analysis_type == "detailed":
            # First pass: Quick analysis with Groq
            quick_prompt = (
                f"Provide a brief analysis focusing on key issues:\n{prompt[:3000]}"
            )
            quick_analysis = await llm_service.generate_content(
                quick_prompt, self.primary_provider
            )

            # Second pass: Detailed analysis with Gemini using quick analysis as context
            detailed_prompt = f"""
Based on this initial analysis: {quick_analysis}

Now provide a comprehensive, detailed review:
{prompt}

Focus on:
- Specific quoted text with exact line references
- Detailed methodological critique
- Comprehensive literature assessment
- Nuanced recommendations with rationale
"""
            return await llm_service.generate_content(
                detailed_prompt, self.detailed_provider
            )

        return await llm_service.generate_content(prompt, self.primary_provider)

    async def enhanced_synthesis(self, context: Dict[str, Any]) -> str:
        """Enhanced synthesis with multiple LLM perspectives."""

        # Get primary synthesis
        primary_synthesis = await self.multi_pass_analysis(
            self._build_synthesis_prompt(context), "detailed"
        )

        # Get secondary perspective for validation
        validation_prompt = f"""
Review this synthesis for completeness and accuracy:
{primary_synthesis}

Original critiques: {context.get('critiques', [])}

Provide an enhanced version that:
- Adds missing critical details
- Improves specificity of recommendations
- Ensures all major issues are addressed
- Enhances professional tone
"""

        enhanced_synthesis = await llm_service.generate_content(
            validation_prompt, self.detailed_provider
        )

        return enhanced_synthesis

    def _build_synthesis_prompt(self, context: Dict[str, Any]) -> str:
        submission = context["submission"]
        critiques = context["critiques"]

        critiques_summary = "\n".join(
            [
                f"{c['agent_type']}: {c['score']}/10 - {len(c.get('findings', []))} findings"
                for c in critiques
            ]
        )

        return f"""
Create a comprehensive academic review report for: {submission['title']}

Agent Analyses:
{critiques_summary}

Requirements:
- Executive summary with key insights
- Detailed issue analysis with quoted text
- Specific line-by-line recommendations
- Professional academic tone
- Constructive, actionable feedback
"""


enhanced_llm_service = EnhancedLLMService()
