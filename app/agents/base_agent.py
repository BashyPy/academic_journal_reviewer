from abc import ABC, abstractmethod
from typing import Any, Dict

import google.generativeai as genai

from app.core.config import settings
from app.models.schemas import AgentCritique

genai.configure(api_key=settings.GEMINI_API_KEY)


class BaseAgent(ABC):
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Returns the system prompt for the agent.
        This is an abstract method that must be implemented by subclasses.

        Returns:
            str: The system prompt that provides instructions to the model
        """

    async def execute_task(self, context: Dict[str, Any]) -> AgentCritique:
        prompt = self.build_prompt(context)
        response = await self.model.generate_content_async(prompt)
        return self.parse_response(response.text)

    def build_prompt(self, context: Dict[str, Any]) -> str:
        system_prompt = self.get_system_prompt()
        manuscript_content = context.get("content", "")

        return f"""
{system_prompt}

MANUSCRIPT TO REVIEW:
{manuscript_content}

Please provide your analysis in the following JSON format:
{{
    "score": <float between 0-10>,
    "findings": ["finding1", "finding2", ...],
    "recommendations": ["rec1", "rec2", ...],
    "confidence": <float between 0-1>
}}
"""

    def parse_response(self, response_text: str) -> AgentCritique:
        import json

        try:
            # Extract JSON from response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]
            data = json.loads(json_str)

            return AgentCritique(
                agent_type=self.agent_type,
                score=data.get("score", 0.0),
                findings=data.get("findings", []),
                recommendations=data.get("recommendations", []),
                confidence=data.get("confidence", 0.0),
            )
        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            return AgentCritique(
                agent_type=self.agent_type,
                score=0.0,
                findings=[f"Error parsing agent response: {str(e)}"],
                recommendations=[f"Please review manually. Traceback: {tb}"],
                confidence=0.0,
            )
